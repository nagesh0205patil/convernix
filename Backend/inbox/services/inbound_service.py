import logging
from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from users.models import Tenant
from whatsapp.models import (
    BusinessNumber, Customer, Department, WhatsAppConfiguration, WhatsAppMessage, Enquiry, Lead, Notification
)
from whatsapp.services import parse_meta_events, resolve_department, normalize_phone
from organization.services.event_service import publish_domain_event
from inbox.models import (
    Conversation, ConversationStatus, ConversationPriority,
    Message, MessageDirection, MessageType, MessageStatus,
    MessageAttachment, WebhookEvent
)

logger = logging.getLogger(__name__)

STATUS_PRECEDENCE = {
    MessageStatus.QUEUED: 10,
    MessageStatus.SENDING: 20,
    MessageStatus.SENT: 30,
    MessageStatus.DELIVERED: 40,
    MessageStatus.READ: 50,
    MessageStatus.FAILED: 99,
}


def resolve_whatsapp_account_and_tenant(
    business_number_str: Optional[str], phone_number_id: Optional[str]
) -> Tuple[Optional[WhatsAppConfiguration], Optional[BusinessNumber], Optional[Tenant]]:
    """Resolves WhatsAppConfiguration, BusinessNumber, and trusted Tenant context."""
    config = None
    if phone_number_id:
        config = WhatsAppConfiguration.objects.filter(phone_number_id=phone_number_id).first()
    if not config and business_number_str:
        config = WhatsAppConfiguration.for_business_number(business_number_str)

    biz_num = None
    if business_number_str:
        normalized_biz = normalize_phone(business_number_str)
        biz_num = BusinessNumber.objects.filter(number=normalized_biz).first()
    if not biz_num and config:
        biz_num = BusinessNumber.objects.filter(number=config.business_number).first()

    tenant = getattr(config, 'tenant', None) or getattr(biz_num, 'tenant', None)
    return config, biz_num, tenant


@transaction.atomic
def process_single_inbound_message(event_data: Dict[str, Any]) -> Optional[Message]:
    """
    Executes the secure inbound pipeline for a single WhatsApp customer message:
    account resolution -> tenant resolution -> idempotency check ->
    contact resolution -> conversation resolution -> routing ->
    message persistence -> unread state -> domain event.
    """
    meta_message_id = event_data.get('message_id')
    if not meta_message_id:
        logger.warning('Inbound message ignored: Missing message_id')
        return None

    # Idempotency check 1: WebhookEvent
    if WebhookEvent.objects.filter(event_id=meta_message_id).exists():
        logger.info('Duplicate webhook event detected and discarded: %s', meta_message_id)
        return None

    data = event_data.get('data', {})
    business_number_str = data.get('business_number')
    phone_number_id = data.get('phone_number_id')

    config, biz_num, tenant = resolve_whatsapp_account_and_tenant(business_number_str, phone_number_id)
    if not tenant:
        logger.warning('Could not resolve tenant for incoming message on phone_number_id=%s', phone_number_id)
        WebhookEvent.objects.create(
            event_id=meta_message_id,
            event_type='message.received',
            status='IGNORED',
            payload=event_data.get('raw_payload', {}),
        )
        return None

    # Idempotency check 2: Message table
    existing_msg = Message.objects.filter(tenant=tenant, meta_message_id=meta_message_id).first()
    if existing_msg:
        logger.info('Message %s already exists in tenant %s', meta_message_id, tenant.id)
        return existing_msg

    # Contact lookup or creation with blind index
    sender_phone = normalize_phone(data.get('phone_number'))
    if not sender_phone:
        logger.warning('Inbound message missing sender phone number: %s', meta_message_id)
        return None

    customer = Customer.objects.find_by_phone(tenant, sender_phone)
    if not customer:
        customer = Customer.objects.create(
            tenant=tenant,
            whatsapp_number=sender_phone,
            full_name=data.get('customer_name') or 'WhatsApp User',
            organization_name=data.get('organization_name') or '',
            email=data.get('customer_email') or '',
        )
    else:
        # Update name or email if previously empty
        changed = False
        if not customer.full_name and data.get('customer_name'):
            customer.full_name = data.get('customer_name')
            changed = True
        if not customer.email and data.get('customer_email'):
            customer.email = data.get('customer_email')
            changed = True
        if changed:
            customer.save()

    # Determine message type and extract content
    meta_type = event_data.get('message_type', 'text').upper()
    type_map = {
        'TEXT': MessageType.TEXT,
        'IMAGE': MessageType.IMAGE,
        'VIDEO': MessageType.VIDEO,
        'AUDIO': MessageType.AUDIO,
        'DOCUMENT': MessageType.DOCUMENT,
        'LOCATION': MessageType.LOCATION,
        'CONTACT': MessageType.CONTACT,
        'INTERACTIVE': MessageType.INTERACTIVE,
        'BUTTON': MessageType.INTERACTIVE,
        'SYSTEM': MessageType.SYSTEM,
    }
    inbox_msg_type = type_map.get(meta_type, MessageType.TEXT)
    content_text = data.get('message') or ''

    # Conversation resolution
    conv_qs = Conversation.objects.filter(
        tenant=tenant,
        contact=customer,
    )
    if biz_num:
        conv_qs = conv_qs.filter(business_number=biz_num)

    # Active open/pending conversation takes priority
    active_conv = conv_qs.filter(status__in=[ConversationStatus.OPEN, ConversationStatus.PENDING]).order_by('-last_message_at').first()

    if not active_conv:
        # Check if there is a resolved conversation to reopen, or create fresh
        resolved_conv = conv_qs.filter(status=ConversationStatus.RESOLVED).order_by('-last_message_at').first()
        if resolved_conv:
            active_conv = resolved_conv
            active_conv.status = ConversationStatus.OPEN
            active_conv.resolved_at = None
            active_conv.version += 1
            active_conv.save(update_fields=['status', 'resolved_at', 'version', 'updated_at'])
            publish_domain_event(
                event_type='conversation.reopened',
                tenant_id=tenant.id,
                data={'conversationId': active_conv.id, 'reason': 'Customer inbound message'},
            )

    is_new_conversation = False
    if not active_conv:
        is_new_conversation = True
        # Resolve department based on keyword routing or business number default
        dept = None
        if biz_num:
            resolved_dept, _ = resolve_department(data.get('category'), biz_num, content_text)
            dept = resolved_dept

        active_conv = Conversation.objects.create(
            tenant=tenant,
            contact=customer,
            whatsapp_account=config,
            business_number=biz_num,
            department=dept,
            status=ConversationStatus.OPEN,
            priority=ConversationPriority.MEDIUM,
            last_message_preview=content_text[:200] if content_text else f'[{inbox_msg_type}]',
            last_message_at=event_data.get('timestamp') or timezone.now(),
        )
        publish_domain_event(
            event_type='conversation.created',
            tenant_id=tenant.id,
            data={
                'conversationId': active_conv.id,
                'contactId': customer.id,
                'departmentId': dept.id if dept else None,
                'status': active_conv.status,
            },
        )

    # Update conversation's latest message metadata
    active_conv.last_message_id = meta_message_id
    active_conv.last_message_preview = content_text[:200] if content_text else f'[{inbox_msg_type}]'
    active_conv.last_message_at = event_data.get('timestamp') or timezone.now()
    active_conv.version += 1
    active_conv.save(update_fields=['last_message_id', 'last_message_preview', 'last_message_at', 'version', 'updated_at'])

    # Persist Message
    message = Message.objects.create(
        tenant=tenant,
        conversation=active_conv,
        meta_message_id=meta_message_id,
        direction=MessageDirection.INBOUND,
        message_type=inbox_msg_type,
        content=content_text,
        status=MessageStatus.RECEIVED,
        raw_payload=event_data.get('raw_payload', {}),
        timestamp=event_data.get('timestamp') or timezone.now(),
    )

    # Handle Media Attachment metadata if attached
    raw_payload = event_data.get('raw_payload', {})
    if inbox_msg_type in (MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO, MessageType.DOCUMENT):
        media_obj = raw_payload.get(meta_type.lower(), {})
        media_id = media_obj.get('id', '')
        if media_id:
            MessageAttachment.objects.create(
                tenant=tenant,
                message=message,
                filename=media_obj.get('filename') or f'{inbox_msg_type.lower()}_{media_id[:8]}',
                content_type=media_obj.get('mime_type', 'application/octet-stream'),
                file_size=media_obj.get('file_size', 0),
                sha256_hash=media_obj.get('sha256', ''),
                meta_media_id=media_id,
            )

    # Record WebhookEvent for idempotency
    WebhookEvent.objects.create(
        event_id=meta_message_id,
        tenant=tenant,
        event_type='message.received',
        status='PROCESSED',
        payload=raw_payload,
    )

    # Emit domain event
    publish_domain_event(
        event_type='message.received',
        tenant_id=tenant.id,
        data={
            'messageId': message.id,
            'conversationId': active_conv.id,
            'direction': message.direction,
            'type': message.message_type,
            'status': message.status,
            'timestamp': message.timestamp.isoformat(),
        },
    )

    # Integrate with Convernix CRM Leads & Customer 360
    try:
        from crm.services.whatsapp_crm_service import WhatsAppCrmService
        WhatsAppCrmService.handle_inbound_whatsapp_message(
            tenant=tenant,
            sender_phone=sender_phone,
            sender_name=data.get('customer_name'),
            message_content=content_text,
            meta_message_id=meta_message_id,
            business_number=biz_num,
            department=active_conv.department,
            legacy_whatsapp_customer=customer,
            timestamp=event_data.get('timestamp'),
        )
    except Exception as crm_err:
        logger.warning('CRM inbound processing warning: %s', crm_err, exc_info=True)

    logger.info(
        'Processed inbound message id=%s for tenant=%s conv=%s',
        message.id, tenant.id, active_conv.id
    )
    return message


@transaction.atomic
def process_single_status_update(status_data: Dict[str, Any]) -> bool:
    """
    Processes delivery status updates (sent, delivered, read, failed) from Meta.
    Enforces safe state transition precedence to prevent out-of-order webhook degradation.
    """
    meta_message_id = status_data.get('message_id')
    raw_status = (status_data.get('status') or '').upper()

    status_mapping = {
        'SENT': MessageStatus.SENT,
        'DELIVERED': MessageStatus.DELIVERED,
        'READ': MessageStatus.READ,
        'FAILED': MessageStatus.FAILED,
    }
    target_status = status_mapping.get(raw_status)
    if not target_status or not meta_message_id:
        return False

    message = Message.objects.select_for_update().filter(meta_message_id=meta_message_id).first()
    if not message:
        # Message may belong to legacy notification or template
        return False

    current_rank = STATUS_PRECEDENCE.get(message.status, 0)
    target_rank = STATUS_PRECEDENCE.get(target_status, 0)

    # If already at higher or equal rank and target is not FAILED, ignore out-of-order event
    if target_rank <= current_rank and target_status != MessageStatus.FAILED:
        logger.info(
            'Out-of-order status update ignored for message %s: current=%s target=%s',
            meta_message_id, message.status, target_status
        )
        return False

    message.status = target_status
    raw_payload = status_data.get('raw_payload', {})
    if target_status == MessageStatus.FAILED:
        errors = raw_payload.get('errors', [])
        err_msg = errors[0].get('message', 'Delivery failed') if errors else 'Meta delivery failed'
        message.error_message = err_msg

    message.raw_payload = {**message.raw_payload, 'last_status_event': raw_payload}
    message.save(update_fields=['status', 'error_message', 'raw_payload'])

    # Emit domain event
    event_type_name = f'message.{target_status.lower()}'
    publish_domain_event(
        event_type=event_type_name,
        tenant_id=message.tenant_id,
        data={
            'messageId': message.id,
            'conversationId': message.conversation_id,
            'status': message.status,
            'metaMessageId': meta_message_id,
        },
    )

    logger.info('Updated message %s status to %s', meta_message_id, target_status)
    return True


def process_inbox_webhook_payload(payload: Dict[str, Any]) -> Dict[str, int]:
    """Top-level webhook payload orchestrator for Convernix Inbox."""
    results = {'messages_processed': 0, 'statuses_processed': 0}
    for event in parse_meta_events(payload):
        if event['kind'] == 'status':
            if process_single_status_update(event):
                results['statuses_processed'] += 1
        elif event['kind'] == 'message':
            if process_single_inbound_message(event):
                results['messages_processed'] += 1
    return results

