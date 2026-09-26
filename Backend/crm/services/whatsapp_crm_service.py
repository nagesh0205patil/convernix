import logging
from typing import Any, Dict, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from crm.models import Customer, CustomerIdentity, Lead, Activity
from crm.services.customer_service import CustomerService
from crm.services.lead_service import LeadService
from crm.services.activity_service import ActivityService
from organization.services.crypto_service import normalize_search_term

logger = logging.getLogger(__name__)


class WhatsAppCrmService:
    @classmethod
    @transaction.atomic
    def handle_inbound_whatsapp_message(
        cls,
        tenant,
        sender_phone: str,
        sender_name: Optional[str] = None,
        message_content: str = '',
        meta_message_id: str = '',
        business_number=None,
        department=None,
        legacy_whatsapp_customer=None,
        timestamp=None,
    ) -> Tuple[Customer, Lead, bool]:
        """
        Integrates incoming WhatsApp interaction with Convernix CRM:
        1. Normalizes sender phone.
        2. Resolves or creates Customer & WhatsApp CustomerIdentity.
        3. Resolves existing active OPEN lead:
           - A new lead is NOT created for every incoming message.
           - If an active OPEN lead exists, we attach this interaction to that lead.
           - If NO active open lead exists (first contact, or previous leads are WON/LOST/CLOSED),
             we create a new Lead in the default pipeline and initial stage.
        4. Creates Activity record (MESSAGE_RECEIVED).
        5. Returns (customer, lead, is_new_lead).
        """
        canonical_phone = normalize_search_term(sender_phone, 'phone')
        effective_time = timestamp or timezone.now()

        # 1. Resolve or create Customer
        customer = CustomerService.resolve_or_create_customer(
            tenant=tenant,
            phone=canonical_phone,
            name=sender_name or 'WhatsApp Contact',
            source='WHATSAPP',
            legacy_whatsapp_customer=legacy_whatsapp_customer,
        )

        # 2. Check for active OPEN lead for this customer
        active_lead = Lead.objects.filter(
            tenant=tenant,
            customer=customer,
            status='OPEN',
            deleted_at__isnull=True,
        ).order_by('-created_at').first()

        is_new_lead = False
        if not active_lead:
            # Create fresh lead for customer
            is_new_lead = True
            lead_title = f"{customer.display_name or canonical_phone} - WhatsApp Inbound"
            active_lead = LeadService.create_lead(
                tenant=tenant,
                customer=customer,
                data={
                    'title': lead_title,
                    'source': 'WHATSAPP',
                    'department': department,
                    'priority': 'MEDIUM',
                },
            )
        else:
            # Update last contacted timestamp on active lead
            active_lead.last_contacted_at = effective_time
            active_lead.save(update_fields=['last_contacted_at', 'updated_at'])

        # 3. Log Activity for the message received
        preview_text = message_content[:150] if message_content else '[Media / Interaction]'
        ActivityService.log_activity(
            tenant=tenant,
            customer=customer,
            lead=active_lead,
            activity_type='MESSAGE_RECEIVED',
            title='Inbound WhatsApp Message',
            description=preview_text,
            metadata={
                'meta_message_id': meta_message_id,
                'business_number': business_number.number if business_number else '',
                'channel': 'whatsapp',
                'timestamp': effective_time.isoformat(),
            },
        )

        return customer, active_lead, is_new_lead
