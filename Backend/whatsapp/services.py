import logging
import re
import uuid
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    AutomationRule, BusinessNumber, Customer, Department, DepartmentMember, Enquiry, Lead,
    Notification, RoutingRule, WhatsAppConfiguration, WhatsAppMessage,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def normalize_phone(value):
    value = re.sub(r'[^0-9+]', '', value or '')
    if value and not value.startswith('+'):
        value = f'+{value}'
    return value


def normalize_meta_recipient(value):
    """Validate E.164 and return the digits-only form expected by Meta."""
    normalized = normalize_phone(value)
    if not re.fullmatch(r'\+[1-9]\d{7,14}', normalized):
        raise ValueError('Recipient phone number must be valid E.164 (8 to 15 digits)')
    return normalized[1:]


def _normalize_text(value):
    return re.sub(r'\s+', ' ', (value or '')).strip().lower()


def _find_matching_rule(business_number, message_text):
    automation = AutomationRule.objects.filter(
        business_number=business_number, rule_type='keyword_routing',
    ).first()
    if automation and not automation.is_active:
        return None

    normalized = _normalize_text(message_text)
    if automation and automation.config.get('routes'):
        for route in automation.config['routes']:
            kw = (route.get('keyword') or '').lower().strip()
            if kw and kw in normalized:
                automation.last_triggered_at = timezone.now()
                automation.save(update_fields=['last_triggered_at'])

                class MatchedRule:
                    pass

                m = MatchedRule()
                m.team_name = route.get('team') or business_number.default_team
                m.keyword = kw
                return m

    for rule in RoutingRule.objects.filter(business_number=business_number, is_active=True).order_by('-priority'):
        if rule.keyword.lower() in normalized:
            if automation:
                automation.last_triggered_at = timezone.now()
                automation.save(update_fields=['last_triggered_at'])
            return rule
    return None


def resolve_department(category, business_number, message_text=''):
    value = _normalize_text(category)
    dept_qs = Department.objects.filter(is_active=True, name__iexact=value)
    if business_number.tenant:
        dept_qs = dept_qs.filter(tenant=business_number.tenant)
    department = dept_qs.first()
    if department:
        return department, 'selected-category'

    rule = _find_matching_rule(business_number, message_text)
    name = rule.team_name if rule else business_number.default_team
    department, _ = Department.objects.get_or_create(
        tenant=business_number.tenant,
        name=name,
        defaults={'slug': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')},
    )
    return department, f'keyword:{rule.keyword}' if rule else 'default-team'


def sync_members_from_users(department):
    """Compatibility bridge while legacy User.team_name remains in use."""
    users = User.objects.filter(team_name__iexact=department.name, is_active=True).exclude(whatsapp_number__isnull=True)
    if department.tenant:
        users = users.filter(tenant=department.tenant)
    for user in users:
        if not user.whatsapp_number:
            continue
        DepartmentMember.objects.get_or_create(
            department=department,
            whatsapp_number=normalize_phone(user.whatsapp_number),
            defaults={'name': user.get_full_name() or user.username, 'user': user},
        )


@transaction.atomic
def create_enquiry(data, *, whatsapp_message_id=None, message_type='text', raw_payload=None, timestamp=None):
    requested_business_number = normalize_phone(data.get('business_number'))
    configuration = (
        WhatsAppConfiguration.for_webhook(requested_business_number, data.get('phone_number_id'))
        if requested_business_number else WhatsAppConfiguration.load()
    )
    business_number_raw = requested_business_number or (normalize_phone(configuration.business_number) if configuration else '')
    if not business_number_raw:
        raise ValueError('A WhatsApp business number is not configured')
    if not configuration:
        raise ValueError(f'WhatsApp configuration is missing for business number {business_number_raw}')
    phone = normalize_phone(data.get('phone_number') or data.get('from_number'))
    if not phone:
        raise ValueError('Customer phone number is required')

    if whatsapp_message_id and WhatsAppMessage.objects.filter(whatsapp_message_id=whatsapp_message_id).exists():
        return None, 'duplicate'

    business_number, _ = BusinessNumber.objects.update_or_create(
        number=business_number_raw,
        defaults={
            'tenant': configuration.tenant,
            'default_team': configuration.default_team,
            'phone_number_id': configuration.phone_number_id,
        },
    )
    department, route_reason = resolve_department(data.get('category'), business_number, data.get('message', ''))
    sync_members_from_users(department)

    customer, _ = Customer.objects.get_or_create(
        tenant=business_number.tenant,
        whatsapp_number=phone,
    )
    updates = {
        'full_name': data.get('customer_name') or data.get('full_name') or customer.full_name,
        'organization_name': data.get('organization_name') or data.get('organization') or customer.organization_name,
        'email': data.get('customer_email') or data.get('email') or customer.email,
    }
    for field, value in updates.items():
        if value:
            setattr(customer, field, value)
    customer.save()

    enquiry = Enquiry.objects.create(
        tenant=business_number.tenant,
        customer=customer, department=department,
        message=data.get('message') or 'WhatsApp enquiry', source=data.get('source', 'whatsapp'),
    )
    first_member = DepartmentMember.objects.filter(department=department, active=True).select_related('user').first()
    Lead.objects.create(
        business_number=business_number, enquiry=enquiry, customer_name=customer.full_name,
        phone_number=phone, customer_email=customer.email or None, message=enquiry.message,
        team_name=department.name, assigned_to=first_member.user if first_member else None,
        status='assigned' if first_member else 'new', source=enquiry.source,
    )

    if whatsapp_message_id:
        WhatsAppMessage.objects.create(
            whatsapp_message_id=whatsapp_message_id, customer=customer, enquiry=enquiry,
            direction='incoming', message_type=message_type, content=enquiry.message,
            status='received', raw_payload=raw_payload or {}, timestamp=timestamp or timezone.now(),
        )
    if business_number.forwarding_number:
        forwarding_number = normalize_phone(business_number.forwarding_number)
        forwarding_recipient, _ = DepartmentMember.objects.get_or_create(
            department=department,
            whatsapp_number=forwarding_number,
            defaults={'name': f'{business_number.number} forwarding recipient'},
        )
        recipients = [forwarding_recipient] if forwarding_recipient.active else []
    else:
        recipients = DepartmentMember.objects.filter(
            department=department, active=True, notification_enabled=True,
        )
    notifications = [
        Notification(enquiry=enquiry, recipient=member, recipient_number=member.whatsapp_number)
        for member in recipients if member.notification_enabled
    ]
    if not notifications:
        logger.warning('No active notification-enabled recipient for enquiry=%s department=%s', enquiry.pk, department.name)
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)
    enquiry.status = 'assigned' if notifications else 'new'
    enquiry.save(update_fields=['status', 'updated_at'])
    trigger_automations(enquiry, business_number, customer, is_first_contact=True)
    return enquiry, route_reason


def _send_automation_reply(business_number, customer, enquiry, message_text, msg_type='auto_reply'):
    from .meta import send_text_message
    try:
        send_text_message(customer.whatsapp_number, message_text, business_number=business_number.number)
    except Exception as exc:
        logger.warning('Auto-reply dispatch skipped or failed (%s): %s', msg_type, exc)
    WhatsAppMessage.objects.create(
        whatsapp_message_id=f'auto.{uuid.uuid4().hex}',
        customer=customer,
        enquiry=enquiry,
        direction='outgoing',
        message_type='text',
        content=message_text,
        status='sent',
        timestamp=timezone.now(),
    )


def trigger_automations(enquiry, business_number, customer, is_first_contact=True):
    """Execute active automation rules for this business number."""
    if not business_number:
        return

    # 1. Welcome Auto-responder (fires only on initial customer contact)
    if is_first_contact:
        welcome_rule = AutomationRule.objects.filter(
            business_number=business_number, rule_type='welcome', is_active=True,
        ).first()
        if welcome_rule:
            msg_text = welcome_rule.config.get(
                'message',
                'Hello! Thanks for reaching out to us on WhatsApp. How can our team assist you today?',
            )
            _send_automation_reply(business_number, customer, enquiry, msg_text, 'welcome_auto_reply')
            welcome_rule.last_triggered_at = timezone.now()
            welcome_rule.save(update_fields=['last_triggered_at'])

    # 2. Out-of-hours Auto-reply
    ooh_rule = AutomationRule.objects.filter(
        business_number=business_number, rule_type='out_of_hours', is_active=True,
    ).first()
    if ooh_rule:
        now = timezone.localtime(timezone.now())
        start_hour = ooh_rule.config.get('start_hour', 9)
        end_hour = ooh_rule.config.get('end_hour', 18)
        is_outside = now.hour < start_hour or now.hour >= end_hour or now.weekday() >= 5
        if is_outside:
            msg_text = ooh_rule.config.get(
                'message',
                'Thank you for your message! Our office hours are Monday to Friday, 9:00 AM – 6:00 PM. We have received your inquiry and our team will get back to you shortly.',
            )
            _send_automation_reply(business_number, customer, enquiry, msg_text, 'out_of_hours_auto_reply')
            ooh_rule.last_triggered_at = timezone.now()
            ooh_rule.save(update_fields=['last_triggered_at'])


@transaction.atomic
def record_incoming_message(data, *, whatsapp_message_id, message_type='text', raw_payload=None, timestamp=None):
    """Append a repeat message to the existing lead, creating an enquiry only on first contact."""
    if whatsapp_message_id and WhatsAppMessage.objects.filter(whatsapp_message_id=whatsapp_message_id).exists():
        return None, 'duplicate'

    phone = normalize_phone(data.get('phone_number') or data.get('from_number'))
    requested_number = normalize_phone(data.get('business_number'))
    configuration = (
        WhatsAppConfiguration.for_webhook(requested_number, data.get('phone_number_id'))
        if requested_number else None
    )
    tenant = configuration.tenant if configuration else None
    cust_qs = Customer.objects.filter(whatsapp_number=phone)
    if tenant:
        cust_qs = cust_qs.filter(tenant=tenant)
    customer = cust_qs.first()
    enquiry = None
    if customer:
        enquiries = Enquiry.objects.filter(customer=customer, legacy_lead__isnull=False)
        if tenant:
            enquiries = enquiries.filter(tenant=tenant)
        if requested_number:
            canonical_number = normalize_phone(configuration.business_number) if configuration else requested_number
            enquiries = enquiries.filter(legacy_lead__business_number__number=canonical_number)
        enquiry = enquiries.order_by('-created_at').first()

    if not enquiry:
        return create_enquiry(
            data, whatsapp_message_id=whatsapp_message_id, message_type=message_type,
            raw_payload=raw_payload, timestamp=timestamp,
        )

    WhatsAppMessage.objects.create(
        whatsapp_message_id=whatsapp_message_id, customer=customer, enquiry=enquiry,
        direction='incoming', message_type=message_type,
        content=data.get('message') or 'WhatsApp message', status='received',
        raw_payload=raw_payload or {}, timestamp=timestamp or timezone.now(),
    )
    enquiry.updated_at = timezone.now()
    enquiry.save(update_fields=['updated_at'])
    lead = getattr(enquiry, 'legacy_lead', None)
    if lead:
        trigger_automations(enquiry, lead.business_number, customer, is_first_contact=False)
    return enquiry, 'existing-conversation'


def route_incoming_message(data):
    enquiry, reason = create_enquiry(data)
    lead = enquiry.legacy_lead
    return {
        'lead_id': lead.id, 'enquiry_id': enquiry.id, 'reference': enquiry.reference,
        'business_number': lead.business_number.number, 'team_name': enquiry.department.name,
        'assigned_to': lead.assigned_to.email if lead.assigned_to else None,
        'assigned_to_name': lead.assigned_to.get_full_name() if lead.assigned_to else None,
        'customer_email': enquiry.customer.email, 'route_reason': reason, 'status': lead.status,
        'recipient_count': enquiry.notifications.count(),
    }


def parse_meta_timestamp(value):
    if not value:
        return timezone.now()
    if str(value).isdigit():
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    return parse_datetime(value) or timezone.now()


def extract_flow_data(message):
    interactive = message.get('interactive', {})
    response = interactive.get('nfm_reply', {}).get('response_json', {})
    if isinstance(response, str):
        import json
        response = json.loads(response)
    return response or {}


def parse_meta_events(payload):
    events = []
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            metadata = value.get('metadata', {})
            contacts = {c.get('wa_id'): c for c in value.get('contacts', [])}
            for message in value.get('messages', []):
                message_type = message.get('type', 'unknown')
                flow = extract_flow_data(message) if message_type == 'interactive' else {}
                text = message.get('text', {}).get('body', '')
                if not text and message_type == 'interactive':
                    text = flow.get('message') or message.get('interactive', {}).get('button_reply', {}).get('title', '')
                contact = contacts.get(message.get('from'), {})
                events.append({
                    'kind': 'message', 'message_id': message.get('id'), 'message_type': message_type,
                    'timestamp': parse_meta_timestamp(message.get('timestamp')), 'raw_payload': message,
                    'data': {
                        'business_number': metadata.get('display_phone_number'),
                        'phone_number_id': metadata.get('phone_number_id'),
                        'phone_number': message.get('from'),
                        'customer_name': flow.get('full_name') or flow.get('name') or contact.get('profile', {}).get('name', ''),
                        'organization_name': flow.get('organization_name') or flow.get('organization', ''),
                        'customer_email': flow.get('email', ''), 'category': flow.get('category', ''),
                        'message': text or 'WhatsApp Flow enquiry',
                    },
                })
            for status in value.get('statuses', []):
                events.append({'kind': 'status', 'message_id': status.get('id'), 'status': status.get('status'), 'raw_payload': status})
    return events


@transaction.atomic
def apply_delivery_status(message_id, status, raw_payload=None):
    allowed = {'sent', 'delivered', 'read', 'failed'}
    if status not in allowed:
        return False
    Notification.objects.filter(whatsapp_message_id=message_id).update(
        status=status,
        error_message=str((raw_payload or {}).get('errors', '')) if status == 'failed' else '',
        updated_at=timezone.now(),
    )
    WhatsAppMessage.objects.filter(whatsapp_message_id=message_id).update(status=status, raw_payload=raw_payload or {})
    return True
