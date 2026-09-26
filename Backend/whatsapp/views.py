import hashlib
import hmac
import csv
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .meta import MetaAPIError, send_media_message, send_text_message
from .models import AutomationRule, BusinessNumber, Enquiry, WhatsAppConfiguration, WhatsAppMessage
from .serializers import (AutomationRuleSerializer, BusinessNumberSerializer, ConversationListSerializer,
                          ConversationReadSerializer, ConversationSerializer,
                          EnquirySerializer, SendMessageSerializer)
from .tasks import process_webhook_payload
from .workspace import accessible_business_numbers, selected_business_number, sync_business_numbers, workspace_is_explicit
from users.permissions import PlatformAdminPermission, PlatformReadWritePermission
from users.tenant_context import filter_by_tenant, get_request_tenant, require_request_tenant


logger = logging.getLogger(__name__)


class EnquiryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
    allowed_page_sizes = {20, 50, 100, 150, 200}

    def get_page_size(self, request):
        try:
            requested = int(request.query_params.get(self.page_size_query_param, self.page_size))
        except (TypeError, ValueError):
            requested = self.page_size
        return requested if requested in self.allowed_page_sizes else self.page_size


def valid_signature(body, signature):
    webhook_secrets = WhatsAppConfiguration.objects.exclude(webhook_secret='').values_list('webhook_secret', flat=True)
    if not webhook_secrets:
        return settings.DEBUG and settings.WHATSAPP_ALLOW_UNSIGNED_WEBHOOKS
    return any(
        hmac.compare_digest('sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), signature or '')
        for secret in webhook_secrets
    )


class WhatsAppHealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        business_numbers = list(WhatsAppConfiguration.objects.values_list('business_number', flat=True))
        return Response({'status': 'ok', 'service': 'whatsapp', 'business_numbers': business_numbers})


class WhatsAppWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        supplied_token = request.query_params.get('hub.verify_token', '')
        token_matches = any(
            hmac.compare_digest(supplied_token, token)
            for token in WhatsAppConfiguration.objects.exclude(verify_token='').values_list('verify_token', flat=True)
        )
        if token_matches and request.query_params.get('hub.mode') == 'subscribe':
            # Meta requires the challenge as raw text. DRF's Response would JSON-encode
            # the string and add quotation marks, causing webhook verification to fail.
            return HttpResponse(request.query_params.get('hub.challenge', ''), content_type='text/plain')
        return Response({'detail': 'Webhook verification failed'}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        if not valid_signature(request.body, request.headers.get('X-Hub-Signature-256')):
            logger.warning('WhatsApp webhook rejected: invalid signature; no messages queued. Check META_APP_SECRET in WhatsApp configuration.')
            return Response({'detail': 'Invalid webhook signature'}, status=status.HTTP_403_FORBIDDEN)
        payload = request.data or {}
        if payload.get('object') != 'whatsapp_business_account':
            return Response({'detail': 'Unsupported webhook object'}, status=status.HTTP_400_BAD_REQUEST)
        process_webhook_payload.delay(payload)
        logger.info('WhatsApp webhook signature verified and payload queued')
        return Response({'status': 'accepted'}, status=status.HTTP_200_OK)


class EnquiryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EnquirySerializer
    pagination_class = EnquiryPagination
    filter_backends = [SearchFilter]
    search_fields = ['reference', 'customer__full_name', 'customer__whatsapp_number',
                     'customer__email', 'department__name', 'message', 'status']

    def get_queryset(self):
        business_number = selected_business_number(self.request)
        queryset = filter_by_tenant(Enquiry.objects.all(), self.request)
        if workspace_is_explicit(self.request):
            queryset = queryset.filter(legacy_lead__business_number=business_number)
        return queryset.select_related(
            'customer', 'department',
        ).prefetch_related('notifications__recipient')


class ConversationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer

    def get_queryset(self):
        business_number = selected_business_number(self.request)
        queryset = filter_by_tenant(Enquiry.objects.all(), self.request)
        if workspace_is_explicit(self.request):
            queryset = queryset.filter(legacy_lead__business_number=business_number)
        return queryset.select_related(
            'customer', 'department', 'legacy_lead__business_number',
        ).prefetch_related('messages').order_by('-updated_at')


class ConversationDetailView(APIView):
    permission_classes = [PlatformReadWritePermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, enquiry_id):
        business_number = selected_business_number(self.request)
        queryset = filter_by_tenant(Enquiry.objects.all(), self.request)
        if workspace_is_explicit(self.request):
            queryset = queryset.filter(legacy_lead__business_number=business_number)
        return generics.get_object_or_404(
            queryset.select_related(
                'customer', 'department', 'legacy_lead__business_number',
            ).prefetch_related('messages'), pk=enquiry_id,
        )

    def get(self, request, enquiry_id):
        return Response(ConversationSerializer(self.get_object(enquiry_id)).data)

    def post(self, request, enquiry_id):
        enquiry = self.get_object(enquiry_id)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data.get('message', '').strip()
        attachments = serializer.validated_data.get('files', [])
        business_number = getattr(getattr(enquiry, 'legacy_lead', None), 'business_number', None)
        if not business_number:
            return Response({'detail': 'This enquiry is not linked to a WhatsApp business number.'}, status=409)
        for index, attachment in enumerate(attachments or [None]):
            caption = text if index == 0 else ''
            message = WhatsAppMessage.objects.create(
                whatsapp_message_id=f'local.{uuid.uuid4().hex}', customer=enquiry.customer, enquiry=enquiry,
                direction='outgoing', message_type='document' if attachment else 'text',
                content=caption or (attachment.name if attachment else text), status='queued',
                timestamp=timezone.now(),
            )
            # get_object() prefetches history; discard that snapshot so the response includes new messages.
            enquiry._prefetched_objects_cache.pop('messages', None)
            if attachment:
                message.attachment.save(attachment.name, attachment, save=False)
                message.attachment_name = attachment.name
                message.attachment_content_type = attachment.content_type or 'application/octet-stream'
                message.save(update_fields=['attachment', 'attachment_name', 'attachment_content_type'])
                attachment.seek(0)
            try:
                if attachment:
                    result, payload, _, media_type = send_media_message(
                        enquiry.customer.whatsapp_number, attachment, caption,
                        business_number=business_number.number,
                    )
                    message.message_type = media_type
                else:
                    result, payload, _ = send_text_message(
                        enquiry.customer.whatsapp_number, text, business_number=business_number.number,
                    )
            except MetaAPIError as error:
                message.status = 'failed'
                message.raw_payload = {'error': str(error), 'response': error.response_payload}
                message.save(update_fields=['status', 'raw_payload'])
                return Response({'detail': str(error), 'message': ConversationSerializer(enquiry).data}, status=502)
            meta_id = result.get('messages', [{}])[0].get('id')
            if not meta_id:
                message.status = 'failed'
                message.raw_payload = {'request': payload, 'response': result}
                message.save(update_fields=['status', 'raw_payload'])
                return Response({'detail': 'Meta accepted no message identifier.'}, status=502)
            message.whatsapp_message_id = meta_id
            message.status = 'sent'
            message.raw_payload = {'request': payload, 'response': result}
            message.save(update_fields=['whatsapp_message_id', 'message_type', 'status', 'raw_payload'])
        enquiry.updated_at = timezone.now()
        enquiry.save(update_fields=['updated_at'])
        return Response(ConversationSerializer(enquiry).data, status=status.HTTP_201_CREATED)


class ConversationAttachmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, enquiry_id, message_id):
        business_number = selected_business_number(request)
        enquiry_qs = filter_by_tenant(Enquiry.objects.all(), request)
        enquiry = generics.get_object_or_404(enquiry_qs, pk=enquiry_id)
        filters = {'pk': message_id, 'enquiry': enquiry}
        if workspace_is_explicit(request):
            filters['enquiry__legacy_lead__business_number'] = business_number
        message = generics.get_object_or_404(
            WhatsAppMessage.objects.only(
                'id', 'enquiry_id', 'attachment', 'attachment_name', 'attachment_content_type',
            ),
            **filters,
        )
        if not message.attachment:
            return Response({'detail': 'This message has no stored attachment.'}, status=404)

        tenant = get_request_tenant(request)
        if tenant:
            from organization.models import AuditLog
            AuditLog.objects.create(
                tenant=tenant,
                actor_name=getattr(request.user, 'get_full_name', lambda: '')() or getattr(request.user, 'username', 'user'),
                actor_email=getattr(request.user, 'email', ''),
                action='ATTACHMENT_ACCESSED',
                module='MediaSecurity',
                resource=f'Attachment {message.attachment_name or message.id} for Enquiry #{enquiry.id}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                status='Success',
                metadata={'message_id': message.id, 'enquiry_id': enquiry.id, 'filename': message.attachment_name}
            )

        return FileResponse(
            message.attachment.open('rb'), content_type=message.attachment_content_type or 'application/octet-stream',
            as_attachment=False, filename=message.attachment_name,
        )


class ConversationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, enquiry_id):
        business_number = selected_business_number(request)
        enquiry_qs = filter_by_tenant(Enquiry.objects.all(), request)
        filters = {'pk': enquiry_id}
        if workspace_is_explicit(request):
            filters['legacy_lead__business_number'] = business_number
        enquiry = generics.get_object_or_404(enquiry_qs, **filters)
        serializer = ConversationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incoming = WhatsAppMessage.objects.filter(enquiry=enquiry, direction='incoming')
        if serializer.validated_data['is_read']:
            incoming.filter(seen_at__isnull=True).update(seen_at=timezone.now())
        else:
            latest = incoming.order_by('-timestamp').first()
            if latest:
                latest.seen_at = None
                latest.save(update_fields=['seen_at'])
        enquiry = Enquiry.objects.select_related(
            'customer', 'department', 'legacy_lead__business_number',
        ).prefetch_related('messages').get(pk=enquiry.pk)
        return Response(ConversationSerializer(enquiry).data)


class EnquiryExportView(APIView):
    """Export enquiries as CSV for a supported rolling or custom date range with privacy controls."""

    permission_classes = [IsAuthenticated]
    RANGE_DAYS = {'week': 7, 'month': 30, 'three_months': 90}

    @staticmethod
    def safe_csv_value(value):
        text = str(value or '')
        return f"'{text}" if text.startswith(('=', '+', '-', '@')) else text

    def get_date_range(self, request):
        range_name = request.query_params.get('range', 'week')
        today = timezone.localdate()
        if range_name in self.RANGE_DAYS:
            return today - timedelta(days=self.RANGE_DAYS[range_name] - 1), today
        if range_name != 'custom':
            raise ValueError('Range must be week, month, three_months, or custom.')

        start_date = parse_date(request.query_params.get('start_date', ''))
        end_date = parse_date(request.query_params.get('end_date', ''))
        if not start_date or not end_date:
            raise ValueError('A valid start_date and end_date are required for a custom range.')
        if start_date > end_date:
            raise ValueError('start_date cannot be after end_date.')
        if end_date > today:
            raise ValueError('end_date cannot be in the future.')
        return start_date, end_date

    def get(self, request):
        tenant = get_request_tenant(request)
        from users.permissions import has_tenant_permission
        if tenant and not has_tenant_permission(request.user, tenant, 'lead.export') and not request.user.is_superuser:
            return Response({'detail': "You do not have permission to export leads (requires 'lead.export')."}, status=status.HTTP_403_FORBIDDEN)

        try:
            start_date, end_date = self.get_date_range(request)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        enquiries = filter_by_tenant(
            Enquiry.objects.filter(created_at__date__range=(start_date, end_date)),
            request,
        )
        if workspace_is_explicit(request):
            enquiries = enquiries.filter(legacy_lead__business_number=selected_business_number(request))
        enquiries = (
            enquiries
            .select_related('customer', 'department')
            .prefetch_related('notifications__recipient')
            .order_by('-created_at')
        )

        can_view_phone = False
        can_view_email = False
        from organization.services.masking_service import MaskingService
        if tenant:
            can_view_phone = MaskingService.can_view_unmasked_phone(request.user, tenant)
            can_view_email = MaskingService.can_view_unmasked_email(request.user, tenant)
        elif request.user.is_superuser:
            can_view_phone = True
            can_view_email = True

        filename = f'enquiries_{start_date.isoformat()}_{end_date.isoformat()}.csv'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')  # Excel-friendly UTF-8 BOM.
        writer = csv.writer(response)
        writer.writerow([
            'Reference', 'Customer Name', 'Phone Number', 'Email', 'Organization',
            'Team', 'Message', 'Status', 'Received At', 'Notification Recipients',
            'Notification Statuses',
        ])
        count = 0
        for enquiry in enquiries:
            count += 1
            notifications = list(enquiry.notifications.all())
            cust = enquiry.customer
            phone_val = getattr(cust, 'plain_phone', None) or cust.whatsapp_number
            if not can_view_phone:
                phone_val = MaskingService.mask_phone(phone_val)
            email_val = getattr(cust, 'plain_email', None) or cust.email
            if not can_view_email:
                email_val = MaskingService.mask_email(email_val)
            writer.writerow([
                self.safe_csv_value(enquiry.reference),
                self.safe_csv_value(getattr(cust, 'plain_name', None) or cust.full_name),
                self.safe_csv_value(phone_val),
                self.safe_csv_value(email_val),
                self.safe_csv_value(getattr(cust, 'plain_organization', None) or cust.organization_name),
                self.safe_csv_value(enquiry.department.name),
                self.safe_csv_value(getattr(enquiry, 'plain_message', None) or enquiry.message),
                enquiry.get_status_display(),
                timezone.localtime(enquiry.created_at).isoformat(),
                self.safe_csv_value(', '.join(item.recipient.name for item in notifications)),
                self.safe_csv_value(', '.join(item.get_status_display() for item in notifications)),
            ])

        # Audit EXPORT_CREATED and record export record
        if tenant:
            from organization.models import AuditLog, DataExportRecord
            token = f'exp_{uuid.uuid4().hex}'
            AuditLog.objects.create(
                tenant=tenant,
                actor_name=getattr(request.user, 'get_full_name', lambda: '')() or getattr(request.user, 'username', 'user'),
                actor_email=getattr(request.user, 'email', ''),
                action='EXPORT_CREATED',
                module='DataPrivacy',
                resource=f'Lead Export ({count} records)',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                status='Success',
                metadata={'record_count': count, 'range': f'{start_date} to {end_date}', 'masked': not can_view_phone}
            )
            DataExportRecord.objects.create(
                tenant=tenant,
                export_token=token,
                requested_by=request.user if request.user.is_authenticated else None,
                export_type='LEAD_CSV_EXPORT',
                file_path=filename,
                expires_at=timezone.now() + timedelta(days=7),
                download_count=1,
                downloaded_at=timezone.now(),
            )
        return response


class CustomerRevealView(APIView):
    """Authorized endpoint for revealing masked customer PII with mandatory audit logging."""
    permission_classes = [IsAuthenticated]

    def post(self, request, customer_id):
        from .models import Customer, Enquiry
        from organization.services.masking_service import MaskingService
        tenant = get_request_tenant(request)
        customer = Customer.objects.filter(pk=customer_id).first()
        if not customer:
            enquiry = Enquiry.objects.filter(pk=customer_id).first()
            if enquiry:
                customer = enquiry.customer
        if not customer:
            return Response({'detail': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        if tenant and customer.tenant_id != tenant.id:
            return Response({'detail': 'Customer not found in tenant context.'}, status=status.HTTP_404_NOT_FOUND)

        if not MaskingService.can_view_unmasked_phone(request.user, tenant):
            return Response({'detail': "Permission denied: 'lead.phone.view' or 'customer.phone.reveal' required."}, status=status.HTTP_403_FORBIDDEN)

        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        MaskingService.audit_phone_reveal(request.user, tenant, str(customer.pk), ip_address=ip)
        MaskingService.audit_email_reveal(request.user, tenant, str(customer.pk), ip_address=ip)

        return Response({
            'id': customer.id,
            'customer_name': getattr(customer, 'plain_name', None) or customer.full_name,
            'phone_number': getattr(customer, 'plain_phone', None) or customer.whatsapp_number,
            'customer_email': getattr(customer, 'plain_email', None) or customer.email,
            'organization_name': getattr(customer, 'plain_organization', None) or customer.organization_name,
            'is_unmasked': True,
        })


class BusinessNumberView(APIView):
    permission_classes = [PlatformAdminPermission]

    def get(self, request):
        requested_number = request.query_params.get('business_number')
        selected = selected_business_number(request)
        if requested_number and not accessible_business_numbers(request.user).filter(number=requested_number).exists():
            return Response({'detail': 'This WhatsApp business number is unavailable.'}, status=status.HTTP_404_NOT_FOUND)
        configuration = WhatsAppConfiguration.for_business_number(requested_number or (selected.number if selected else ''))
        if not configuration:
            return Response({'detail': 'WhatsApp configuration not found'}, status=status.HTTP_404_NOT_FOUND)
        number, _ = BusinessNumber.objects.update_or_create(
            number=configuration.business_number,
            defaults={
                'tenant': configuration.tenant,
                'default_team': configuration.default_team,
                'phone_number_id': configuration.phone_number_id,
            },
        )
        return Response(BusinessNumberSerializer(number).data)

    def patch(self, request):
        requested_number = request.data.get('business_number') or request.query_params.get('business_number')
        selected = selected_business_number(request)
        if requested_number and not accessible_business_numbers(request.user, request=request).filter(number=requested_number).exists():
            return Response({'detail': 'This WhatsApp business number is unavailable.'}, status=status.HTTP_404_NOT_FOUND)
        configuration = WhatsAppConfiguration.for_business_number(requested_number or (selected.number if selected else ''))
        if not configuration:
            return Response({'detail': 'WhatsApp configuration not found'}, status=status.HTTP_404_NOT_FOUND)
        number, _ = BusinessNumber.objects.get_or_create(
            number=configuration.business_number,
            defaults={'tenant': configuration.tenant},
        )
        serializer = BusinessNumberSerializer(number, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_number = serializer.validated_data.get('number', number.number)
        access = request.user.number_access
        if (access == 'india' and not new_number.startswith('+91')) or (access == 'us' and not new_number.startswith('+1')):
            return Response({'detail': 'The number is outside your regional access.'}, status=status.HTTP_403_FORBIDDEN)
        number = serializer.save()
        configuration.business_number = number.number
        configuration.default_team = number.default_team
        configuration.phone_number_id = number.phone_number_id
        configuration.save()
        return Response(serializer.data)


class BusinessNumberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        sync_business_numbers(tenant=tenant)
        numbers = accessible_business_numbers(request.user, request=request).order_by('label', 'number')
        return Response(BusinessNumberSerializer(numbers, many=True).data)


class AutomationRuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business_number = selected_business_number(request)
        if not business_number:
            return Response({'detail': 'Select a WhatsApp business number.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .tasks import check_lead_escalations
            check_lead_escalations(business_number)
        except Exception as exc:
            logger.warning('check_lead_escalations failed: %s', exc)
        rules = AutomationRule.get_or_create_defaults(business_number)
        return Response(AutomationRuleSerializer(rules, many=True).data)


class AutomationRuleDetailView(APIView):
    permission_classes = [PlatformReadWritePermission]

    def patch(self, request, pk):
        business_number = selected_business_number(request)
        rule = generics.get_object_or_404(AutomationRule, pk=pk, business_number=business_number)
        serializer = AutomationRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(AutomationRuleSerializer(updated).data)

