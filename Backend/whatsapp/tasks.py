import json
import logging

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .meta import MetaAPIError, MetaAPIPermanentError, send_template_message
from .models import (
    AutomationRule, BusinessNumber, Lead, Notification, WhatsAppConfiguration, WhatsAppMessage,
)
from .services import apply_delivery_status, parse_meta_events, record_incoming_message

logger = logging.getLogger(__name__)


def _redact_payload(payload):
    """Redact sensitive customer parameters and message text from stored payloads."""
    if not isinstance(payload, dict):
        return payload
    try:
        data = json.loads(json.dumps(payload))
        if 'template' in data and isinstance(data['template'], dict):
            components = data['template'].get('components', [])
            for comp in components:
                if comp.get('type') == 'body' and 'parameters' in comp:
                    comp['parameters'] = [{'type': 'text', 'text': '[REDACTED_FOR_PRIVACY]'}]
        if 'text' in data and isinstance(data['text'], dict):
            data['text']['body'] = '[REDACTED_FOR_PRIVACY]'
        return data
    except Exception:
        return payload


def _store_error(notification, exc, status):
    notification.status = status
    notification.request_payload = _redact_payload(exc.request_payload)
    notification.response_payload = _redact_payload(exc.response_payload)
    notification.http_status_code = exc.http_status
    notification.error_code = exc.code
    notification.error_subcode = exc.subcode
    notification.error_message = str(exc)
    notification.fbtrace_id = exc.fbtrace_id
    notification.save(update_fields=[
        'status', 'request_payload', 'response_payload', 'http_status_code', 'error_code',
        'error_subcode', 'error_message', 'fbtrace_id', 'retry_count', 'updated_at',
    ])


@shared_task(bind=True, max_retries=5)
def send_department_notification(self, notification_id):
    retry_error = None
    with transaction.atomic():
        notification = Notification.objects.select_for_update(of=('self',)).select_related(
            'enquiry__customer', 'enquiry__department', 'enquiry__legacy_lead__business_number', 'recipient',
        ).get(pk=notification_id)
        if notification.status in {'sent', 'delivered', 'read'}:
            return
        enquiry = notification.enquiry
        customer = enquiry.customer
        if not notification.recipient.active or not notification.recipient.notification_enabled:
            exc = MetaAPIPermanentError('Recipient is inactive or notifications are disabled')
            _store_error(notification, exc, 'permanently_failed')
            return
        notification.status = 'processing'
        notification.recipient_number = notification.recipient_number or notification.recipient.whatsapp_number
        business_number = notification.enquiry.legacy_lead.business_number.number
        account = WhatsAppConfiguration.for_business_number(business_number)
        notification.template_name = account.notification_template if account else settings.WHATSAPP_TEMPLATE_NAME
        notification.retry_count = self.request.retries
        notification.save(update_fields=['status', 'recipient_number', 'template_name', 'retry_count', 'updated_at'])
        received_at = timezone.localtime(enquiry.created_at).strftime('%d-%b-%Y %I:%M %p')

        # Decrypt fields safely if encrypted
        cust_name = getattr(customer, 'plain_name', None) or customer.full_name or 'Customer'
        cust_phone = getattr(customer, 'plain_phone', None) or customer.whatsapp_number
        msg_body = getattr(enquiry, 'plain_message', None) or enquiry.message

        # Support Zero-PII internal notifications when configured
        zero_pii_enabled = getattr(settings, 'ZERO_PII_NOTIFICATIONS', False)
        if zero_pii_enabled:
            masked_phone = f"******{cust_phone[-4:]}" if len(cust_phone) >= 4 else "****"
            sanitized_body = f"New lead received in {enquiry.department.name} Department. Login to Convernix to view and respond."
            parameters = [
                f"Lead #{enquiry.id}", masked_phone, enquiry.department.name,
                sanitized_body, received_at,
            ]
        else:
            parameters = [
                cust_name, cust_phone, enquiry.department.name,
                msg_body, received_at,
            ]

        masked_recipient = f'******{notification.recipient_number[-4:]}'
        logger.info(
            'Sending WhatsApp template notification_id=%s recipient=%s template=%s',
            notification.pk, masked_recipient, notification.template_name,
        )
        try:
            result, request_payload, http_status = send_template_message(
                notification.recipient_number, parameters,
                business_number=enquiry.legacy_lead.business_number.number,
            )
        except MetaAPIPermanentError as exc:
            _store_error(notification, exc, 'permanently_failed')
            logger.error(
                'Meta message permanently rejected notification_id=%s http_status=%s meta_error_code=%s',
                notification.pk, exc.http_status, exc.code,
            )
            return
        except MetaAPIError as exc:
            notification.retry_count = self.request.retries + 1
            final_attempt = notification.retry_count > self.max_retries
            _store_error(notification, exc, 'failed' if final_attempt else 'queued')
            if not final_attempt:
                retry_error = exc
        else:
            message_id = result.get('messages', [{}])[0].get('id', '')
            notification.whatsapp_message_id = message_id
            notification.status = 'sent'
            notification.request_payload = _redact_payload(request_payload)
            notification.response_payload = _redact_payload(result)
            notification.http_status_code = http_status
            notification.error_code = notification.error_subcode = notification.error_message = notification.fbtrace_id = ''
            notification.sent_at = timezone.now()
            notification.save(update_fields=[
                'whatsapp_message_id', 'status', 'request_payload', 'response_payload', 'http_status_code',
                'error_code', 'error_subcode', 'error_message', 'fbtrace_id', 'sent_at', 'updated_at',
            ])
            if message_id:
                WhatsAppMessage.objects.update_or_create(
                    whatsapp_message_id=message_id,
                    defaults={
                        'customer': customer, 'enquiry': enquiry, 'direction': 'outgoing',
                        'message_type': 'template', 'content': msg_body, 'status': 'sent',
                        'timestamp': timezone.now(),
                    },
                )
            logger.info('Meta message accepted notification_id=%s meta_message_id=%s', notification.pk, message_id)
    if retry_error:
        raise self.retry(exc=retry_error, countdown=60 * (2 ** self.request.retries))


@shared_task
def process_webhook_payload(payload):
    # Process through first-class Convernix Inbox pipeline
    try:
        from inbox.services.inbound_service import process_inbox_webhook_payload
        process_inbox_webhook_payload(payload)
    except Exception as exc:
        logger.error('Inbox webhook pipeline error: %s', exc, exc_info=True)

    # Maintain backward compatibility for legacy lead/enquiry workflows
    for event in parse_meta_events(payload):
        if event['kind'] == 'status':
            apply_delivery_status(event['message_id'], event['status'], event['raw_payload'])
            continue
        enquiry, state = record_incoming_message(
            event['data'], whatsapp_message_id=event['message_id'], message_type=event['message_type'],
            raw_payload=event['raw_payload'], timestamp=event['timestamp'],
        )
        if enquiry and state not in {'duplicate', 'existing-conversation'}:
            for notification_id in enquiry.notifications.values_list('id', flat=True):
                send_department_notification.delay(notification_id)


@shared_task
def check_lead_escalations(business_number_id=None):
    """Check unattended leads and mark priority according to the escalation rule."""
    rules = AutomationRule.objects.filter(rule_type='escalation', is_active=True)
    if business_number_id:
        if isinstance(business_number_id, BusinessNumber):
            rules = rules.filter(business_number=business_number_id)
        elif isinstance(business_number_id, (int, str)) and str(business_number_id).isdigit():
            rules = rules.filter(business_number_id=int(business_number_id))

    now = timezone.now()
    escalated_count = 0
    for rule in rules:
        try:
            timeout_minutes = int(rule.config.get('timeout_minutes', 15))
        except (ValueError, TypeError):
            timeout_minutes = 15
        cutoff = now - timedelta(minutes=timeout_minutes)
        unattended_leads = Lead.objects.filter(
            business_number=rule.business_number,
            created_at__lte=cutoff,
            status__in=['new', 'assigned'],
        ).exclude(customer_name__startswith='[PRIORITY]')

        for lead in unattended_leads:
            # Skip if an agent already replied with an outgoing message
            if lead.enquiry and lead.enquiry.messages.filter(direction='outgoing').exclude(whatsapp_message_id__startswith='auto.').exists():
                continue
            orig_name = lead.customer_name or lead.phone_number or 'Customer'
            lead.customer_name = f'[PRIORITY] {orig_name}'
            lead.save(update_fields=['customer_name', 'updated_at'])
            escalated_count += 1
            rule.last_triggered_at = now
            rule.save(update_fields=['last_triggered_at'])
    return escalated_count
