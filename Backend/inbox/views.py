import logging
import re
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.tenant_context import filter_by_tenant, get_request_tenant, require_request_tenant
from users.permissions import check_tenant_permission, has_tenant_permission
from organization.services.crypto_service import compute_blind_index
from organization.services.audit_service import log_admin_action
from organization.services.event_service import publish_domain_event
from organization.services.masking_service import MaskingService
from whatsapp.models import Department, Customer, BusinessNumber, WhatsAppConfiguration
from whatsapp.meta import MetaAPIError, MetaAPIPermanentError, send_text_message, send_media_message

from .models import (
    Conversation, ConversationStatus, ConversationPriority,
    Message, MessageDirection, MessageType, MessageStatus,
    MessageAttachment, MessageMention, ConversationRead,
    ConversationAssignment, AssignmentAction, Tag, ConversationTag
)
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, SendMessageInputSerializer, CreateNoteInputSerializer,
    AssignInputSerializer, TransferInputSerializer, ReadStateInputSerializer,
    MentionSerializer, DepartmentSummarySerializer, TagSerializer
)
from .permissions import HasInboxPermission, check_department_access
from .exceptions import (
    ConversationNotFoundException, ConversationAlreadyAssignedException,
    PermissionDeniedInboxException, DepartmentAccessDeniedException,
    InvalidConversationStateException, MessageSendFailedException,
    MetaAPIErrorException, MetaRateLimitedException, AttachmentTooLargeException,
    AttachmentTypeNotAllowedException, TenantAccessDeniedException,
    inbox_error_response
)

logger = logging.getLogger(__name__)
User = get_user_model()

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg',
    'video/mp4', 'video/3gpp',
    'application/pdf', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/csv',
}
MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class InboxPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationListCreateView(APIView):
    """
    GET /api/inbox/conversations
    List conversations filtered server-side by ownership, department, status, priority, tag, search.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'inbox.view'

    def get(self, request):
        tenant = require_request_tenant(request)
        queryset = Conversation.objects.filter(tenant=tenant).select_related(
            'contact', 'department', 'assigned_user', 'business_number'
        ).prefetch_related('tags__tag')

        # Ownership filter
        ownership = request.query_params.get('ownership', 'all').lower()
        if ownership == 'mine':
            queryset = queryset.filter(assigned_user=request.user)
        elif ownership == 'unassigned':
            queryset = queryset.filter(assigned_user__isnull=True)

        # Department filter
        dept_param = request.query_params.get('department')
        if dept_param:
            if dept_param.isdigit():
                queryset = queryset.filter(department_id=int(dept_param))
            else:
                queryset = queryset.filter(department__slug=dept_param)

        # Assigned agent filter
        agent_param = request.query_params.get('assigned_agent') or request.query_params.get('assigned_user')
        if agent_param:
            if agent_param.isdigit():
                queryset = queryset.filter(assigned_user_id=int(agent_param))
            else:
                queryset = queryset.filter(assigned_user__email=agent_param)

        # Status filter
        status_param = request.query_params.get('status')
        if status_param:
            statuses = [s.strip().upper() for s in status_param.split(',') if s.strip()]
            queryset = queryset.filter(status__in=statuses)

        # Priority filter
        priority_param = request.query_params.get('priority')
        if priority_param:
            priorities = [p.strip().upper() for p in priority_param.split(',') if p.strip()]
            queryset = queryset.filter(priority__in=priorities)

        # Tag filter
        tag_param = request.query_params.get('tag')
        if tag_param:
            if tag_param.isdigit():
                queryset = queryset.filter(tags__tag_id=int(tag_param))
            else:
                queryset = queryset.filter(tags__tag__name__iexact=tag_param)

        # Channel / Business number filter
        channel_param = request.query_params.get('channel') or request.query_params.get('business_number')
        if channel_param:
            if channel_param.isdigit():
                queryset = queryset.filter(business_number_id=int(channel_param))
            else:
                queryset = queryset.filter(business_number__number=channel_param)

        # Date range filter
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(last_message_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(last_message_at__lte=date_to)

        # Search filter
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            # 1. Exact match via blind index for phone and email
            phone_hash = compute_blind_index(tenant, search_query, 'phone')
            email_hash = compute_blind_index(tenant, search_query, 'email')
            search_filters = Q()
            if phone_hash:
                search_filters |= Q(contact__phone_hash=phone_hash)
            if email_hash:
                search_filters |= Q(contact__email_hash=email_hash)

            # 2. Text match on contact name or reference
            search_filters |= Q(contact__full_name__icontains=search_query)

            queryset = queryset.filter(search_filters)

        # Unread filter
        unread_param = request.query_params.get('unread')
        if unread_param is not None and unread_param.lower() in ('true', '1'):
            # Filter conversations where latest inbound message > user's last_read_at
            user_reads = ConversationRead.objects.filter(
                tenant=tenant, user=request.user
            ).values('conversation_id', 'last_read_at')
            read_map = {r['conversation_id']: r['last_read_at'] for r in user_reads}
            
            # Subquery or python filter for unread (paginated safely)
            unread_ids = []
            for conv_id, l_msg_at in queryset.values_list('id', 'last_message_at'):
                last_read = read_map.get(conv_id)
                if not last_read or l_msg_at > last_read:
                    unread_ids.append(conv_id)
            queryset = queryset.filter(id__in=unread_ids)

        # Ordering
        queryset = queryset.order_by('-last_message_at')

        paginator = InboxPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ConversationListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class ConversationDetailView(APIView):
    """
    GET /api/inbox/conversations/{id}
    Retrieve full conversation details with customer context.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.view'

    def get(self, request, id):
        tenant = require_request_tenant(request)
        conversation = Conversation.objects.filter(tenant=tenant, pk=id).select_related(
            'contact', 'department', 'assigned_user', 'business_number'
        ).prefetch_related('tags__tag').first()

        if not conversation:
            raise ConversationNotFoundException()

        if not check_department_access(request.user, tenant, conversation.department):
            raise DepartmentAccessDeniedException()

        # Audit view
        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='CONVERSATION_VIEWED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={'conversation_id': conversation.id, 'status': conversation.status},
        )

        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(serializer.data)


class ConversationClaimView(APIView):
    """
    POST /api/inbox/conversations/{id}/claim
    Atomic claim of an unassigned conversation.
    Uses select_for_update row locking to guarantee that two simultaneous claim attempts
    do not both succeed. Returns 409 CONVERSATION_ALREADY_ASSIGNED on conflict.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.claim'

    def post(self, request, id):
        tenant = require_request_tenant(request)

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            if conversation.assigned_user_id is not None:
                assigned_name = conversation.assigned_user.get_full_name() or conversation.assigned_user.email
                raise ConversationAlreadyAssignedException(
                    f'Conversation has already been claimed by {assigned_name}.'
                )

            conversation.assigned_user = request.user
            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['assigned_user', 'version', 'updated_at'])

            # Log assignment history
            ConversationAssignment.objects.create(
                tenant=tenant,
                conversation=conversation,
                assigned_by=request.user,
                to_user=request.user,
                action_type=AssignmentAction.CLAIM,
                reason='Claimed by agent from inbox queue',
            )

        # Audit and event
        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='CONVERSATION_CLAIMED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={'conversation_id': conversation.id, 'claimed_by': request.user.email},
        )
        publish_domain_event(
            event_type='conversation.assigned',
            tenant_id=tenant.id,
            data={
                'conversationId': conversation.id,
                'action': 'CLAIM',
                'assignedUserId': request.user.id,
                'assignedUserEmail': request.user.email,
            },
        )

        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConversationAssignView(APIView):
    """
    POST /api/inbox/conversations/{id}/assign
    Assign or reassign conversation to another agent.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.assign'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        serializer = AssignInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data['user_id']

        target_user = User.objects.filter(pk=target_user_id, is_active=True).first()
        if not target_user:
            return inbox_error_response('USER_NOT_FOUND', 'Target user was not found or is inactive.', status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            old_user = conversation.assigned_user
            action_type = AssignmentAction.REASSIGN if old_user else AssignmentAction.ASSIGN

            if action_type == AssignmentAction.REASSIGN:
                check_tenant_permission(request, 'conversation.reassign')

            conversation.assigned_user = target_user
            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['assigned_user', 'version', 'updated_at'])

            ConversationAssignment.objects.create(
                tenant=tenant,
                conversation=conversation,
                assigned_by=request.user,
                from_user=old_user,
                to_user=target_user,
                action_type=action_type,
            )

        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='CONVERSATION_ASSIGNED' if action_type == AssignmentAction.ASSIGN else 'CONVERSATION_REASSIGNED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={'conversation_id': conversation.id, 'assigned_to': target_user.email},
        )
        publish_domain_event(
            event_type='conversation.assigned',
            tenant_id=tenant.id,
            data={
                'conversationId': conversation.id,
                'action': action_type,
                'fromUserId': old_user.id if old_user else None,
                'assignedUserId': target_user.id,
            },
        )

        return Response(ConversationDetailSerializer(conversation, context={'request': request}).data)


class ConversationUnassignView(APIView):
    """
    POST /api/inbox/conversations/{id}/unassign
    Remove agent assignment from conversation.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.assign'

    def post(self, request, id):
        tenant = require_request_tenant(request)

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            old_user = conversation.assigned_user
            conversation.assigned_user = None
            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['assigned_user', 'version', 'updated_at'])

            ConversationAssignment.objects.create(
                tenant=tenant,
                conversation=conversation,
                assigned_by=request.user,
                from_user=old_user,
                to_user=None,
                action_type=AssignmentAction.UNASSIGN,
            )

        publish_domain_event(
            event_type='conversation.assigned',
            tenant_id=tenant.id,
            data={'conversationId': conversation.id, 'action': 'UNASSIGN'},
        )
        return Response(ConversationDetailSerializer(conversation, context={'request': request}).data)


class ConversationTransferView(APIView):
    """
    POST /api/inbox/conversations/{id}/transfer
    Transfer conversation to another department queue.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.transfer'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        serializer = TransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dept_id = serializer.validated_data['department_id']
        reason = serializer.validated_data.get('reason', '')
        user_id = serializer.validated_data.get('user_id')

        target_dept = Department.objects.filter(tenant=tenant, pk=dept_id, is_active=True).first()
        if not target_dept:
            return inbox_error_response('DEPARTMENT_NOT_FOUND', 'Target department was not found or is disabled.', status.HTTP_404_NOT_FOUND)

        target_user = None
        if user_id:
            target_user = User.objects.filter(pk=user_id, is_active=True).first()

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            old_dept = conversation.department
            old_user = conversation.assigned_user

            conversation.department = target_dept
            if target_user:
                conversation.assigned_user = target_user
            elif user_id is None:
                # If no user specified on department transfer, set unassigned so new dept team can claim
                conversation.assigned_user = None

            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['department', 'assigned_user', 'version', 'updated_at'])

            ConversationAssignment.objects.create(
                tenant=tenant,
                conversation=conversation,
                assigned_by=request.user,
                from_user=old_user,
                to_user=conversation.assigned_user,
                from_department=old_dept,
                to_department=target_dept,
                action_type=AssignmentAction.TRANSFER,
                reason=reason,
            )

        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='CONVERSATION_TRANSFERRED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={
                'conversation_id': conversation.id,
                'from_dept': old_dept.name if old_dept else '',
                'to_dept': target_dept.name,
                'reason': reason,
            },
        )
        publish_domain_event(
            event_type='conversation.transferred',
            tenant_id=tenant.id,
            data={
                'conversationId': conversation.id,
                'fromDepartmentId': old_dept.id if old_dept else None,
                'toDepartmentId': target_dept.id,
                'reason': reason,
            },
        )

        return Response(ConversationDetailSerializer(conversation, context={'request': request}).data)


class ConversationResolveView(APIView):
    """
    POST /api/inbox/conversations/{id}/resolve
    Mark conversation as resolved.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.resolve'

    def post(self, request, id):
        tenant = require_request_tenant(request)

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            if not conversation.can_transition_to(ConversationStatus.RESOLVED):
                raise InvalidConversationStateException(
                    f'Cannot transition conversation from {conversation.status} to RESOLVED.'
                )

            conversation.status = ConversationStatus.RESOLVED
            conversation.resolved_at = timezone.now()
            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['status', 'resolved_at', 'version', 'updated_at'])

        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='CONVERSATION_RESOLVED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={'conversation_id': conversation.id},
        )
        publish_domain_event(
            event_type='conversation.resolved',
            tenant_id=tenant.id,
            data={'conversationId': conversation.id, 'resolvedBy': request.user.email},
        )

        return Response(ConversationDetailSerializer(conversation, context={'request': request}).data)


class ConversationReopenView(APIView):
    """
    POST /api/inbox/conversations/{id}/reopen
    Reopen a resolved or closed conversation.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'conversation.reopen'

    def post(self, request, id):
        tenant = require_request_tenant(request)

        with transaction.atomic():
            conversation = Conversation.objects.select_for_update(of=('self',)).filter(
                tenant=tenant, pk=id
            ).first()

            if not conversation:
                raise ConversationNotFoundException()

            if not conversation.can_transition_to(ConversationStatus.OPEN):
                raise InvalidConversationStateException(
                    f'Cannot reopen conversation from status {conversation.status}.'
                )

            conversation.status = ConversationStatus.OPEN
            conversation.resolved_at = None
            conversation.version += 1
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['status', 'resolved_at', 'version', 'updated_at'])

        publish_domain_event(
            event_type='conversation.reopened',
            tenant_id=tenant.id,
            data={'conversationId': conversation.id, 'reopenedBy': request.user.email},
        )

        return Response(ConversationDetailSerializer(conversation, context={'request': request}).data)


class ConversationReadView(APIView):
    """
    POST /api/inbox/conversations/{id}/read
    Update per-user read tracking for the requesting agent.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'inbox.view'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        conversation = Conversation.objects.filter(tenant=tenant, pk=id).first()
        if not conversation:
            raise ConversationNotFoundException()

        serializer = ReadStateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_read = serializer.validated_data.get('is_read', True)
        last_msg_id = serializer.validated_data.get('last_read_message_id', '')

        if is_read:
            latest_msg = conversation.messages.filter(direction=MessageDirection.INBOUND).order_by('-timestamp').first()
            if not last_msg_id and latest_msg:
                last_msg_id = latest_msg.meta_message_id or str(latest_msg.id)

            ConversationRead.objects.update_or_create(
                tenant=tenant,
                conversation=conversation,
                user=request.user,
                defaults={
                    'last_read_message_id': last_msg_id,
                    'last_read_at': timezone.now(),
                },
            )
        else:
            # Mark unread: rewind last_read_at to beginning
            ConversationRead.objects.filter(
                tenant=tenant, conversation=conversation, user=request.user
            ).delete()

        publish_domain_event(
            event_type='conversation.read',
            tenant_id=tenant.id,
            data={
                'conversationId': conversation.id,
                'userId': request.user.id,
                'isRead': is_read,
            },
        )
        return Response({'status': 'ok', 'is_read': is_read})


class ConversationMessagesListView(APIView):
    """
    GET /api/inbox/conversations/{id}/messages
    Retrieve timeline messages for conversation.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'message.view'

    def get(self, request, id):
        tenant = require_request_tenant(request)
        conversation = Conversation.objects.filter(tenant=tenant, pk=id).first()
        if not conversation:
            raise ConversationNotFoundException()

        if not check_department_access(request.user, tenant, conversation.department):
            raise DepartmentAccessDeniedException()

        messages_qs = Message.objects.filter(
            tenant=tenant, conversation=conversation
        ).select_related('sender_user').prefetch_related('attachments').order_by('timestamp', 'id')

        # Internal notes visibility check
        can_view_notes = has_tenant_permission(request.user, tenant, 'note.view')
        if not can_view_notes:
            messages_qs = messages_qs.exclude(message_type=MessageType.INTERNAL_NOTE)

        paginator = InboxPagination()
        page = paginator.paginate_queryset(messages_qs, request)
        serializer = MessageSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        return ConversationSendMessageView.as_view()(request, id=id)


class ConversationSendMessageView(APIView):
    """
    POST /api/inbox/conversations/{id}/messages
    Send outbound WhatsApp message to customer via Meta Cloud API.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'message.send'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request, id):
        tenant = require_request_tenant(request)
        conversation = Conversation.objects.select_related(
            'contact', 'whatsapp_account', 'business_number'
        ).filter(tenant=tenant, pk=id).first()

        if not conversation:
            raise ConversationNotFoundException()

        if conversation.status == ConversationStatus.CLOSED:
            raise InvalidConversationStateException('Cannot send messages to a closed conversation. Please reopen it first.')

        serializer = SendMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data.get('message', '').strip()
        files = serializer.validated_data.get('files', [])

        # Validate business account credentials
        biz_num = conversation.business_number
        if not biz_num and conversation.whatsapp_account:
            biz_num = BusinessNumber.objects.filter(number=conversation.whatsapp_account.business_number).first()
        if not biz_num:
            biz_num = BusinessNumber.objects.filter(tenant=tenant, is_active=True).first()

        if not biz_num:
            return inbox_error_response('WHATSAPP_ACCOUNT_NOT_CONFIGURED', 'No active WhatsApp business number is configured for this conversation.', 409)

        cust_phone = conversation.contact.plain_phone or conversation.contact.whatsapp_number
        if not cust_phone:
            return inbox_error_response('CUSTOMER_PHONE_MISSING', 'Customer has no valid WhatsApp phone number.', 400)

        created_messages = []

        # Iterate attachments or send single text message
        items_to_send = files if files else [None]
        for idx, file_obj in enumerate(items_to_send):
            caption = text if idx == 0 else ''
            msg_type = MessageType.DOCUMENT if file_obj else MessageType.TEXT

            if file_obj:
                # Security validations on file
                if file_obj.size > MAX_ATTACHMENT_SIZE_BYTES:
                    raise AttachmentTooLargeException(f'File {file_obj.name} exceeds 25 MB limit.')
                if file_obj.content_type and file_obj.content_type.lower() not in ALLOWED_MIME_TYPES:
                    raise AttachmentTypeNotAllowedException(f'MIME type {file_obj.content_type} is not allowed.')

            # Persist message locally in SENDING status
            msg = Message.objects.create(
                tenant=tenant,
                conversation=conversation,
                sender_user=request.user,
                direction=MessageDirection.OUTBOUND,
                message_type=msg_type,
                content=caption or (file_obj.name if file_obj else text),
                status=MessageStatus.SENDING,
                timestamp=timezone.now(),
            )

            attachment_rec = None
            if file_obj:
                attachment_rec = MessageAttachment.objects.create(
                    tenant=tenant,
                    message=msg,
                    file=file_obj,
                    filename=file_obj.name,
                    content_type=file_obj.content_type or 'application/octet-stream',
                    file_size=file_obj.size,
                )
                file_obj.seek(0)

            # Dispatch via Meta Cloud API
            try:
                if file_obj:
                    result, req_payload, http_code, detected_type = send_media_message(
                        cust_phone, file_obj, caption, business_number=biz_num.number
                    )
                    type_mapping = {'image': MessageType.IMAGE, 'video': MessageType.VIDEO, 'audio': MessageType.AUDIO}
                    msg.message_type = type_mapping.get(detected_type, MessageType.DOCUMENT)
                else:
                    result, req_payload, http_code = send_text_message(
                        cust_phone, text, business_number=biz_num.number
                    )
                
                meta_id = result.get('messages', [{}])[0].get('id', '')
                if not meta_id:
                    raise MetaAPIError('Meta accepted no message identifier in response.')

                msg.meta_message_id = meta_id
                msg.status = MessageStatus.SENT
                msg.raw_payload = {'request': req_payload, 'response': result}
                msg.save(update_fields=['meta_message_id', 'message_type', 'status', 'raw_payload'])

                publish_domain_event(
                    event_type='message.sent',
                    tenant_id=tenant.id,
                    data={'messageId': msg.id, 'conversationId': conversation.id, 'metaMessageId': meta_id},
                )
                log_admin_action(
                    tenant=tenant,
                    actor_name=request.user.get_full_name() or request.user.username,
                    actor_email=request.user.email,
                    action='MESSAGE_SENT',
                    module='Inbox',
                    resource=f'Conversation #{conversation.id}',
                    request=request,
                    metadata={'conversation_id': conversation.id, 'message_id': msg.id},
                )
            except MetaAPIError as err:
                msg.status = MessageStatus.FAILED
                msg.error_message = str(err)
                msg.raw_payload = {'error': str(err), 'code': getattr(err, 'code', '')}
                msg.save(update_fields=['status', 'error_message', 'raw_payload'])

                publish_domain_event(
                    event_type='message.failed',
                    tenant_id=tenant.id,
                    data={'messageId': msg.id, 'conversationId': conversation.id, 'error': str(err)},
                )
                log_admin_action(
                    tenant=tenant,
                    actor_name=request.user.get_full_name() or request.user.username,
                    actor_email=request.user.email,
                    action='MESSAGE_FAILED',
                    module='Inbox',
                    resource=f'Conversation #{conversation.id}',
                    request=request,
                    metadata={'conversation_id': conversation.id, 'error': str(err)},
                    status='Failed',
                )
                logger.error('Meta message dispatch failed: %s', err)

                if getattr(err, 'code', '') in ('429', '131056') or getattr(err, 'http_status', None) == 429:
                    raise MetaRateLimitedException(str(err))
                raise MessageSendFailedException(str(err))

            created_messages.append(msg)

        # Update conversation latest message metadata
        conversation.last_message_id = created_messages[-1].meta_message_id
        conversation.last_message_preview = text[:200] if text else f'[{created_messages[-1].message_type}]'
        conversation.last_message_at = timezone.now()
        conversation.version += 1
        conversation.save(update_fields=['last_message_id', 'last_message_preview', 'last_message_at', 'version', 'updated_at'])

        # Auto-mark conversation as read for the sender
        ConversationRead.objects.update_or_create(
            tenant=tenant,
            conversation=conversation,
            user=request.user,
            defaults={'last_read_message_id': conversation.last_message_id, 'last_read_at': timezone.now()},
        )

        serializer = MessageSerializer(created_messages[0], context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationCreateNoteView(APIView):
    """
    POST /api/inbox/conversations/{id}/notes
    Add an internal note with @mentions support.
    Strictly isolated: internal notes are NEVER dispatched to Meta WhatsApp!
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'note.create'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        conversation = Conversation.objects.filter(tenant=tenant, pk=id).first()
        if not conversation:
            raise ConversationNotFoundException()

        serializer = CreateNoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['content']

        # Persist internal note
        note_msg = Message.objects.create(
            tenant=tenant,
            conversation=conversation,
            sender_user=request.user,
            direction=MessageDirection.INTERNAL,
            message_type=MessageType.INTERNAL_NOTE,
            content=content,
            status=MessageStatus.RECEIVED,
            timestamp=timezone.now(),
        )

        # Parse @mentions
        # Matches patterns like @john or @john.doe@company.com
        mention_patterns = re.findall(r'@([a-zA-Z0-9_.+-]+(?:@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)?)\b', content)
        mentioned_users = []
        for handle in set(mention_patterns):
            target_user = User.objects.filter(
                tenant=tenant, is_active=True
            ).filter(Q(username__iexact=handle) | Q(email__iexact=handle)).first()
            if target_user and target_user.id != request.user.id:
                mentioned_users.append(target_user)
                MessageMention.objects.create(
                    tenant=tenant,
                    message=note_msg,
                    mentioned_user=target_user,
                )
                publish_domain_event(
                    event_type='mention.created',
                    tenant_id=tenant.id,
                    data={
                        'mentionId': note_msg.id,
                        'conversationId': conversation.id,
                        'mentionedUserId': target_user.id,
                        'mentionedBy': request.user.email,
                    },
                )

        # Audit and domain event
        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='NOTE_CREATED',
            module='Inbox',
            resource=f'Conversation #{conversation.id}',
            request=request,
            metadata={'conversation_id': conversation.id, 'mention_count': len(mentioned_users)},
        )
        publish_domain_event(
            event_type='note.created',
            tenant_id=tenant.id,
            data={
                'messageId': note_msg.id,
                'conversationId': conversation.id,
                'senderEmail': request.user.email,
                'mentions': [u.email for u in mentioned_users],
            },
        )

        return Response(MessageSerializer(note_msg, context={'request': request}).data, status=status.HTTP_201_CREATED)


class MessageRetryView(APIView):
    """
    POST /api/inbox/messages/{id}/retry
    Retry sending a failed outbound message.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'message.send'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        message = Message.objects.select_related('conversation__contact', 'conversation__business_number').filter(
            tenant=tenant, pk=id, direction=MessageDirection.OUTBOUND
        ).first()

        if not message:
            return inbox_error_response('MESSAGE_NOT_FOUND', 'Failed message not found in tenant context.', 404)

        if message.status != MessageStatus.FAILED:
            return inbox_error_response('INVALID_STATUS', 'Only failed messages can be retried.', 400)

        conversation = message.conversation
        biz_num = conversation.business_number or BusinessNumber.objects.filter(tenant=tenant, is_active=True).first()
        cust_phone = conversation.contact.plain_phone or conversation.contact.whatsapp_number

        try:
            result, req_payload, http_code = send_text_message(
                cust_phone, message.plain_content, business_number=biz_num.number
            )
            meta_id = result.get('messages', [{}])[0].get('id', '')
            message.meta_message_id = meta_id
            message.status = MessageStatus.SENT
            message.error_message = ''
            message.save(update_fields=['meta_message_id', 'status', 'error_message'])

            publish_domain_event(
                event_type='message.sent',
                tenant_id=tenant.id,
                data={'messageId': message.id, 'conversationId': conversation.id, 'metaMessageId': meta_id},
            )
            return Response(MessageSerializer(message, context={'request': request}).data)
        except Exception as exc:
            message.error_message = str(exc)
            message.save(update_fields=['error_message'])
            raise MessageSendFailedException(str(exc))


class MentionListView(APIView):
    """
    GET /api/inbox/mentions
    List unread or all @mentions for requesting user.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'inbox.view'

    def get(self, request):
        tenant = require_request_tenant(request)
        mentions_qs = MessageMention.objects.filter(
            tenant=tenant, mentioned_user=request.user
        ).select_related('message__sender_user').order_by('-created_at')

        unread_only = request.query_params.get('unread')
        if unread_param := (unread_only and unread_only.lower() in ('true', '1')):
            mentions_qs = mentions_qs.filter(is_read=False)

        paginator = InboxPagination()
        page = paginator.paginate_queryset(mentions_qs, request)
        serializer = MentionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MentionMarkReadView(APIView):
    """
    POST /api/inbox/mentions/{id}/read
    Mark mention notification as read.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'inbox.view'

    def post(self, request, id):
        tenant = require_request_tenant(request)
        mention = MessageMention.objects.filter(
            tenant=tenant, pk=id, mentioned_user=request.user
        ).first()

        if not mention:
            return inbox_error_response('MENTION_NOT_FOUND', 'Mention not found.', 404)

        mention.is_read = True
        mention.read_at = timezone.now()
        mention.save(update_fields=['is_read', 'read_at'])

        return Response({'status': 'ok', 'is_read': True})


class AttachmentDownloadView(APIView):
    """
    GET /api/inbox/attachments/{id}/download/
    Authorized and audited streaming of attachments.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'attachment.download'

    def get(self, request, id):
        tenant = require_request_tenant(request)
        attachment = MessageAttachment.objects.select_related('message__conversation').filter(
            tenant=tenant, pk=id
        ).first()

        if not attachment:
            return inbox_error_response('ATTACHMENT_NOT_FOUND', 'Attachment not found.', 404)

        if not check_department_access(request.user, tenant, attachment.message.conversation.department):
            raise DepartmentAccessDeniedException()

        if not attachment.file:
            return inbox_error_response('ATTACHMENT_FILE_MISSING', 'Stored file object is missing.', 404)

        log_admin_action(
            tenant=tenant,
            actor_name=request.user.get_full_name() or request.user.username,
            actor_email=request.user.email,
            action='ATTACHMENT_DOWNLOADED',
            module='Inbox',
            resource=f'Attachment {attachment.filename}',
            request=request,
            metadata={'attachment_id': attachment.id, 'filename': attachment.filename},
        )

        return FileResponse(
            attachment.file.open('rb'),
            content_type=attachment.content_type,
            as_attachment=True,
            filename=attachment.filename,
        )


class DepartmentQueueListView(APIView):
    """
    GET /api/inbox/departments
    List department queues for the tenant with active counts.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'department.queue.view'

    def get(self, request):
        tenant = require_request_tenant(request)
        departments = Department.objects.filter(tenant=tenant, is_active=True).order_by('name')

        data = []
        for d in departments:
            conv_qs = Conversation.objects.filter(tenant=tenant, department=d)
            data.append({
                'id': d.id,
                'name': d.name,
                'slug': d.slug,
                'open_count': conv_qs.filter(status=ConversationStatus.OPEN).count(),
                'pending_count': conv_qs.filter(status=ConversationStatus.PENDING).count(),
                'resolved_count': conv_qs.filter(status=ConversationStatus.RESOLVED).count(),
                'unassigned_count': conv_qs.filter(status=ConversationStatus.OPEN, assigned_user__isnull=True).count(),
            })
        return Response(data)


class TagListView(APIView):
    """
    GET /api/inbox/tags
    List conversation tags for the tenant.
    """
    permission_classes = [HasInboxPermission]
    required_permission = 'inbox.view'

    def get(self, request):
        tenant = require_request_tenant(request)
        tags = Tag.objects.filter(tenant=tenant).order_by('name')
        return Response(TagSerializer(tags, many=True).data)


class InboxSSEView(APIView):
    """
    GET /api/inbox/events/
    Server-Sent Events stream for real-time inbox notifications.
    Requires no additional packages — uses Django's StreamingHttpResponse.
    The client (EventSource) auto-reconnects on disconnect.
    Stream closes after 60 s so the client reconnects fresh.

    Authentication: accepts ?token=<jwt> as EventSource cannot send headers.
    """
    permission_classes = []  # handled manually below for SSE compat

    def get(self, request):
        import time
        import json as _json
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        # Authenticate via Authorization header OR ?token= query param (EventSource compat)
        token_str = None
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_str = auth_header[7:].strip()
        if not token_str:
            token_str = request.GET.get('token', '').strip()

        user = None
        if token_str:
            try:
                UntypedToken(token_str)
                from rest_framework_simplejwt.authentication import JWTAuthentication
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token_str.encode())
                user = jwt_auth.get_user(validated)
            except (InvalidToken, TokenError, Exception):
                pass

        if not user or not user.is_authenticated:
            from django.http import HttpResponse
            return HttpResponse('Unauthorized', status=401)

        # Resolve tenant
        from users.tenant_context import get_request_tenant
        request.user = user  # needed for tenant resolution
        tenant = get_request_tenant(request)
        if not tenant:
            from django.http import HttpResponse
            return HttpResponse('No tenant context', status=403)

        # Permission check
        if not has_tenant_permission(user, tenant, 'inbox.view'):
            from django.http import HttpResponse
            return HttpResponse('Forbidden', status=403)

        def event_stream():
            """Generator that streams SSE events to the browser."""
            last_check = timezone.now()
            deadline = time.monotonic() + 60  # close after 60 s

            # Send initial connection confirmation
            yield 'event: connected\ndata: {"status":"ok"}\n\n'

            while time.monotonic() < deadline:
                time.sleep(2)

                # Fetch conversations updated since last check
                updated = Conversation.objects.filter(
                    tenant=tenant, updated_at__gt=last_check
                ).select_related('contact', 'department', 'assigned_user').order_by('-updated_at')[:20]

                for conv in updated:
                    payload = ConversationListSerializer(conv, context={'request': request}).data
                    yield f'event: conversation.updated\ndata: {_json.dumps(payload)}\n\n'

                # Fetch new messages since last check
                new_msgs = Message.objects.filter(
                    tenant=tenant,
                    created_at__gt=last_check,
                ).select_related('sender_user', 'conversation').order_by('created_at')[:50]

                for msg in new_msgs:
                    payload = {
                        'conversationId': msg.conversation_id,
                        'messageId': msg.id,
                        'direction': msg.direction,
                        'messageType': msg.message_type,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    }
                    yield f'event: message.received\ndata: {_json.dumps(payload)}\n\n'

                last_check = timezone.now()

                # Heartbeat to keep connection alive
                yield ': heartbeat\n\n'

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
