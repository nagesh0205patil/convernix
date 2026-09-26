import logging
from typing import Any, Dict, List, Optional
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.models import (
    Customer, CustomerIdentity, CustomerMergeHistory, CustomerTag,
    CustomFieldValue, Activity, Note, Lead
)
from crm.services.duplicate_detection_service import DuplicateDetectionService
from crm.services.activity_service import ActivityService
from organization.models import AuditLog
from organization.services.crypto_service import (
    compute_blind_index, encrypt_tenant_data, normalize_search_term
)
from organization.services.event_service import publish_domain_event
from integrations.outbox import emit_outbox_event

logger = logging.getLogger(__name__)


class CustomerService:
    @classmethod
    @transaction.atomic
    def create_customer(
        cls,
        tenant,
        data: Dict[str, Any],
        actor_user=None,
    ) -> Customer:
        """
        Creates a new Customer with encrypted PII, blind index lookups, and identity record.
        """
        raw_phone = data.get('phone', '')
        raw_email = data.get('email', '')
        display_name = data.get('display_name', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        source = data.get('source', 'MANUAL')
        status = data.get('status', 'ACTIVE')

        # Check exact duplicate customer before creation
        if raw_phone or raw_email:
            existing = DuplicateDetectionService.find_exact_customer(tenant, phone=raw_phone, email=raw_email)
            if existing:
                raise ValidationError({'detail': 'A customer with this phone or email already exists in your organization.', 'code': 'DUPLICATE_CUSTOMER'})

        customer = Customer(
            tenant=tenant,
            display_name=display_name or f'{first_name} {last_name}'.strip(),
            source=source,
            status=status,
        )
        if raw_phone:
            customer.set_plain_phone(raw_phone)
        if raw_email:
            customer.set_plain_email(raw_email)
        if first_name or last_name:
            customer.set_plain_names(first_name, last_name)

        try:
            customer.save()
        except IntegrityError as exc:
            # Handle concurrent race condition gracefully
            existing = DuplicateDetectionService.find_exact_customer(tenant, phone=raw_phone, email=raw_email)
            if existing:
                return existing
            raise ValidationError({'detail': 'Concurrent customer creation conflict.', 'code': 'CONCURRENT_MODIFICATION'}) from exc

        # Create identities
        if raw_phone:
            CustomerIdentity.objects.get_or_create(
                tenant=tenant,
                provider='PHONE',
                lookup_hash=customer.phone_lookup_hash,
                defaults={
                    'customer': customer,
                    'identifier_encrypted': customer.phone_encrypted,
                    'is_primary': True,
                    'verified': True,
                },
            )
            if source == 'WHATSAPP':
                CustomerIdentity.objects.get_or_create(
                    tenant=tenant,
                    provider='WHATSAPP',
                    lookup_hash=customer.phone_lookup_hash,
                    defaults={
                        'customer': customer,
                        'identifier_encrypted': customer.phone_encrypted,
                        'is_primary': True,
                        'verified': True,
                    },
                )

        if raw_email:
            CustomerIdentity.objects.get_or_create(
                tenant=tenant,
                provider='EMAIL',
                lookup_hash=customer.email_lookup_hash,
                defaults={
                    'customer': customer,
                    'identifier_encrypted': customer.email_encrypted,
                    'is_primary': not raw_phone,
                    'verified': True,
                },
            )

        # Log Activity
        ActivityService.log_activity(
            tenant=tenant,
            customer=customer,
            activity_type='CUSTOMER_CREATED',
            title='Customer Profile Created',
            description=f'Created via {source}',
            actor_user=actor_user,
        )

        # Publish domain event & outbox
        event_payload = {
            'customer_id': str(customer.customer_id),
            'display_name': customer.display_name,
            'source': customer.source,
            'status': customer.status,
        }
        try:
            publish_domain_event(
                event_type='crm.customer.created',
                tenant_id=tenant.id,
                data=event_payload,
            )
            emit_outbox_event(
                tenant=tenant,
                event_type='crm.customer.created',
                payload=event_payload,
            )
        except Exception as exc:
            logger.warning('Failed to emit customer created event: %s', exc)

        return customer

    @classmethod
    @transaction.atomic
    def update_customer(
        cls,
        customer: Customer,
        data: Dict[str, Any],
        actor_user=None,
    ) -> Customer:
        """
        Updates customer profile attributes, maintaining encryption and recalculating blind indexes.
        """
        tenant = customer.tenant
        update_fields = ['version', 'updated_at']

        if 'display_name' in data:
            customer.display_name = data['display_name']
            update_fields.append('display_name')

        if 'status' in data:
            customer.status = data['status']
            update_fields.append('status')

        if 'source' in data:
            customer.source = data['source']
            update_fields.append('source')

        if 'phone' in data:
            new_phone = data['phone']
            if new_phone:
                hashes = DuplicateDetectionService.compute_hashes(tenant, phone=new_phone)
                # Check uniqueness against other customers
                duplicate = Customer.objects.filter(
                    tenant=tenant,
                    phone_lookup_hash=hashes['phone_hash'],
                    deleted_at__isnull=True,
                ).exclude(customer_id=customer.customer_id).first()
                if duplicate:
                    raise ValidationError({'phone': 'Another customer already uses this phone number.', 'code': 'DUPLICATE_CUSTOMER'})
            customer.set_plain_phone(new_phone)
            update_fields.extend(['phone_encrypted', 'phone_lookup_hash'])

        if 'email' in data:
            new_email = data['email']
            if new_email:
                hashes = DuplicateDetectionService.compute_hashes(tenant, email=new_email)
                duplicate = Customer.objects.filter(
                    tenant=tenant,
                    email_lookup_hash=hashes['email_hash'],
                    deleted_at__isnull=True,
                ).exclude(customer_id=customer.customer_id).first()
                if duplicate:
                    raise ValidationError({'email': 'Another customer already uses this email address.', 'code': 'DUPLICATE_CUSTOMER'})
            customer.set_plain_email(new_email)
            update_fields.extend(['email_encrypted', 'email_lookup_hash'])

        if 'first_name' in data or 'last_name' in data:
            fn = data.get('first_name', customer.plain_first_name)
            ln = data.get('last_name', customer.plain_last_name)
            customer.set_plain_names(fn, ln)
            update_fields.extend(['first_name_encrypted', 'last_name_encrypted', 'display_name'])

        customer.version += 1
        customer.save(update_fields=list(set(update_fields)))

        # Log Activity
        ActivityService.log_activity(
            tenant=tenant,
            customer=customer,
            activity_type='CUSTOMER_UPDATED',
            title='Customer Profile Updated',
            description='Updated customer details',
            actor_user=actor_user,
        )

        # Audit Log
        AuditLog.log(
            tenant=tenant,
            actor_name=getattr(actor_user, 'get_full_name', lambda: '')() or getattr(actor_user, 'email', 'System'),
            actor_email=getattr(actor_user, 'email', ''),
            action='CUSTOMER_UPDATED',
            module='CRM',
            resource=f'Customer #{customer.customer_id}',
        )

        # Publish event
        try:
            publish_domain_event(
                event_type='crm.customer.updated',
                tenant_id=tenant.id,
                data={'customer_id': str(customer.customer_id)},
            )
        except Exception:
            pass

        return customer

    @classmethod
    @transaction.atomic
    def resolve_or_create_customer(
        cls,
        tenant,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        source: str = 'WHATSAPP',
        legacy_whatsapp_customer=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """
        Deterministic identity resolution with concurrency safety:
        1. Exact lookup hash match against Customer & CustomerIdentity.
        2. If matched, update missing attributes.
        3. If not found, atomically create new Customer and Identity records.
        """
        customer = DuplicateDetectionService.find_exact_customer(tenant, phone=phone, email=email)
        if customer:
            changed = False
            fields_to_update = []
            if not customer.display_name and name:
                customer.display_name = name
                fields_to_update.append('display_name')
                changed = True
            if not customer.legacy_whatsapp_customer and legacy_whatsapp_customer:
                customer.legacy_whatsapp_customer = legacy_whatsapp_customer
                fields_to_update.append('legacy_whatsapp_customer')
                changed = True
            if changed:
                customer.save(update_fields=fields_to_update)
            return customer

        # Create new customer
        return cls.create_customer(
            tenant=tenant,
            data={
                'phone': phone,
                'email': email,
                'display_name': name or 'WhatsApp User',
                'source': source,
            },
        )

    @classmethod
    @transaction.atomic
    def merge_customers(
        cls,
        tenant,
        primary_customer: Customer,
        secondary_customer: Customer,
        merged_by=None,
        reason: str = '',
    ) -> Customer:
        """
        Production-grade customer merge preserving all historical data and relationships:
        - Transfers all Leads to primary_customer
        - Transfers all Activities to primary_customer
        - Transfers all Notes to primary_customer
        - Re-parents all Identities to primary_customer
        - Re-parents Tags and CustomFieldValues
        - Re-parents Inbox Conversations
        - Preserves snapshot in CustomerMergeHistory
        - Soft-deletes secondary_customer
        - Logs tamper-evident AuditLog entry and emits domain event
        """
        if primary_customer.customer_id == secondary_customer.customer_id:
            raise ValidationError({'detail': 'Cannot merge a customer into itself.', 'code': 'CUSTOMER_MERGE_CONFLICT'})

        if primary_customer.tenant_id != tenant.id or secondary_customer.tenant_id != tenant.id:
            raise ValidationError({'detail': 'Cross-tenant merge is strictly prohibited.', 'code': 'TENANT_ACCESS_DENIED'})

        snapshot = {
            'secondary_customer_id': str(secondary_customer.customer_id),
            'display_name': secondary_customer.display_name,
            'source': secondary_customer.source,
            'status': secondary_customer.status,
            'created_at': secondary_customer.created_at.isoformat(),
        }

        # 1. Transfer Leads
        Lead.objects.filter(customer=secondary_customer).update(customer=primary_customer)

        # 2. Transfer Activities
        Activity.objects.filter(customer=secondary_customer).update(customer=primary_customer)

        # 3. Transfer Notes
        Note.objects.filter(customer=secondary_customer).update(customer=primary_customer)

        # 4. Transfer Identities (avoiding duplicate constraints)
        for identity in secondary_customer.identities.all():
            existing_ident = CustomerIdentity.objects.filter(
                tenant=tenant,
                provider=identity.provider,
                lookup_hash=identity.lookup_hash,
                customer=primary_customer,
            ).first()
            if not existing_ident:
                identity.customer = primary_customer
                identity.save(update_fields=['customer', 'updated_at'])
            else:
                identity.delete()

        # 5. Transfer Tags
        for ctag in secondary_customer.customer_tags.all():
            if not CustomerTag.objects.filter(customer=primary_customer, tag=ctag.tag).exists():
                ctag.customer = primary_customer
                ctag.save(update_fields=['customer'])
            else:
                ctag.delete()

        # 6. Transfer CustomFieldValues
        for cfv in secondary_customer.custom_field_values.all():
            if not CustomFieldValue.objects.filter(customer=primary_customer, definition=cfv.definition).exists():
                cfv.customer = primary_customer
                cfv.save(update_fields=['customer', 'updated_at'])
            else:
                cfv.delete()

        # 7. Re-link Inbox Conversations if present
        if secondary_customer.legacy_whatsapp_customer:
            from inbox.models import Conversation
            Conversation.objects.filter(contact=secondary_customer.legacy_whatsapp_customer).update(
                contact=primary_customer.legacy_whatsapp_customer or secondary_customer.legacy_whatsapp_customer
            )

        # 8. Record CustomerMergeHistory
        merge_record = CustomerMergeHistory.objects.create(
            tenant=tenant,
            primary_customer=primary_customer,
            secondary_customer_id=secondary_customer.customer_id,
            merged_by=merged_by,
            merged_data_snapshot=snapshot,
            reason=reason or 'Manual customer merge by authorized operator',
        )

        # 9. Soft-delete secondary customer
        secondary_customer.soft_delete()

        # 10. Record Activity on Primary
        ActivityService.log_activity(
            tenant=tenant,
            customer=primary_customer,
            activity_type='CUSTOMER_MERGED',
            title='Customer Merged',
            description=f'Merged customer {secondary_customer.display_name} (ID: {secondary_customer.customer_id}) into this profile.',
            actor_user=merged_by,
            metadata={'merge_id': str(merge_record.merge_id), 'reason': reason},
        )

        # 11. Tamper-evident AuditLog
        actor_name = getattr(merged_by, 'get_full_name', lambda: '')() or getattr(merged_by, 'email', 'System')
        AuditLog.log(
            tenant=tenant,
            actor_name=actor_name,
            actor_email=getattr(merged_by, 'email', ''),
            action='CUSTOMER_MERGED',
            module='CRM',
            resource=f'Customer #{primary_customer.customer_id}',
            metadata={'secondary_id': str(secondary_customer.customer_id), 'reason': reason},
        )

        # 12. Publish domain event & outbox
        event_payload = {
            'merge_id': str(merge_record.merge_id),
            'primary_customer_id': str(primary_customer.customer_id),
            'secondary_customer_id': str(secondary_customer.customer_id),
            'actor_name': actor_name,
        }
        try:
            publish_domain_event(
                event_type='crm.customer.merged',
                tenant_id=tenant.id,
                data=event_payload,
            )
            emit_outbox_event(
                tenant=tenant,
                event_type='crm.customer.merged',
                payload=event_payload,
            )
        except Exception as exc:
            logger.warning('Failed to emit customer merged event: %s', exc)

        return primary_customer
