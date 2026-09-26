import json
import logging
import os
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .crypto_service import (
    compute_blind_index,
    decrypt_tenant_data,
    encrypt_tenant_data,
)
from .retention_service import RetentionService

logger = logging.getLogger(__name__)


class DsrService:
    """
    Data Subject / Data Principal Request (DSR) Management Service.
    Implements ACCESS, CORRECTION, ERASURE, and WITHDRAW_CONSENT workflows for DPDP Act & ISO 27701.
    """

    @classmethod
    def locate_customer(cls, tenant, identifier: str) -> Optional[Any]:
        """Locate customer by ID, exact phone blind index, or exact email blind index."""
        from whatsapp.models import Customer
        if not identifier or not tenant:
            return None
        
        # 1. By primary key
        if identifier.isdigit():
            c = Customer.objects.filter(tenant=tenant, pk=int(identifier)).first()
            if c:
                return c

        # 2. By phone blind index
        phone_hash = compute_blind_index(tenant, identifier, 'phone')
        if phone_hash:
            c = Customer.objects.filter(tenant=tenant, phone_hash=phone_hash).first()
            if c:
                return c

        # 3. By email blind index
        email_hash = compute_blind_index(tenant, identifier, 'email')
        if email_hash:
            c = Customer.objects.filter(tenant=tenant, email_hash=email_hash).first()
            if c:
                return c

        return None

    @classmethod
    def process_access_request(cls, tenant, identifier: str, requested_by=None) -> Dict[str, Any]:
        """
        Gathers complete data principal processing profile across all models and generates a
        temporary secure export file.
        """
        from organization.models import AuditLog, DataExportRecord, PrivacyEvent
        from whatsapp.models import Customer, Enquiry, WhatsAppMessage

        customer = cls.locate_customer(tenant, identifier)
        if not customer:
            raise ValueError('Data principal record not found within this organization.')

        # 1. Customer profile
        decrypted_phone = decrypt_tenant_data(tenant, customer.whatsapp_number)
        decrypted_name = decrypt_tenant_data(tenant, customer.full_name)
        decrypted_email = decrypt_tenant_data(tenant, customer.email)
        decrypted_org = decrypt_tenant_data(tenant, customer.organization_name)

        payload: Dict[str, Any] = {
            'data_principal': {
                'customer_id': customer.id,
                'full_name': decrypted_name,
                'phone_number': decrypted_phone,
                'email': decrypted_email,
                'organization': decrypted_org,
                'created_at': customer.created_at.isoformat(),
            },
            'enquiries': [],
            'messages': [],
            'privacy_events': [],
            'exported_at': timezone.now().isoformat(),
        }

        # 2. Enquiries
        for enq in Enquiry.objects.filter(customer=customer):
            payload['enquiries'].append({
                'reference': enq.reference,
                'department': enq.department.name if enq.department else None,
                'message': decrypt_tenant_data(tenant, enq.message),
                'status': enq.status,
                'created_at': enq.created_at.isoformat(),
            })

        # 3. Messages
        for msg in WhatsAppMessage.objects.filter(customer=customer):
            payload['messages'].append({
                'id': msg.id,
                'direction': msg.direction,
                'type': msg.message_type,
                'content': decrypt_tenant_data(tenant, msg.content),
                'attachment_name': msg.attachment_name,
                'timestamp': msg.timestamp.isoformat(),
            })

        # 4. Privacy Events / Consent History
        for ev in PrivacyEvent.objects.filter(tenant=tenant, data_principal_reference=str(customer.id)):
            payload['privacy_events'].append({
                'event_type': ev.event_type,
                'purpose': ev.purpose,
                'occurred_at': ev.occurred_at.isoformat(),
                'metadata': ev.metadata,
            })

        # Store temporary protected export file
        export_token = f'dsr_{uuid.uuid4().hex}'
        export_dir = os.path.join(settings.BASE_DIR, 'media', 'exports', f'tenant_{tenant.id}')
        os.makedirs(export_dir, exist_ok=True)
        file_path = os.path.join(export_dir, f'{export_token}.json')

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

        export_rec = DataExportRecord.objects.create(
            tenant=tenant,
            export_token=export_token,
            requested_by=requested_by if getattr(requested_by, 'is_authenticated', False) else None,
            export_type='PRIVACY_DSR',
            file_path=file_path,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(requested_by, 'username', 'system'),
            actor_email=getattr(requested_by, 'email', 'system@convernix.internal'),
            action='DATA_EXPORTED',
            module='DataPrivacy',
            resource=f'Customer #{customer.id} Data Discovery Export',
            status='Success',
            metadata={'export_token': export_token, 'customer_id': customer.id},
        )

        return {
            'export_token': export_token,
            'download_url': f'/api/privacy/exports/{export_token}/download/',
            'expires_at': export_rec.expires_at.isoformat(),
            'records_summary': {
                'enquiries_count': len(payload['enquiries']),
                'messages_count': len(payload['messages']),
            },
        }

    @classmethod
    @transaction.atomic
    def process_correction_request(cls, tenant, identifier: str, corrections: Dict[str, str], actor=None) -> Dict[str, Any]:
        """
        Corrects inaccurate data principal personal information with audited evidence.
        Re-encrypts data with active tenant key and updates HMAC search blind indexes.
        """
        from organization.models import AuditLog
        from whatsapp.models import Customer, Lead

        customer = cls.locate_customer(tenant, identifier)
        if not customer:
            raise ValueError('Data principal record not found within this organization.')

        fields_corrected = []
        if 'full_name' in corrections and corrections['full_name']:
            customer.full_name = encrypt_tenant_data(tenant, corrections['full_name'])
            fields_corrected.append('full_name')

        if 'organization_name' in corrections and corrections['organization_name']:
            customer.organization_name = encrypt_tenant_data(tenant, corrections['organization_name'])
            fields_corrected.append('organization_name')

        if 'email' in corrections and corrections['email']:
            raw_email = corrections['email'].strip().lower()
            customer.email = encrypt_tenant_data(tenant, raw_email)
            customer.email_hash = compute_blind_index(tenant, raw_email, 'email')
            fields_corrected.append('email')

        if 'phone_number' in corrections and corrections['phone_number']:
            raw_phone = corrections['phone_number'].strip()
            customer.whatsapp_number = encrypt_tenant_data(tenant, raw_phone)
            customer.phone_hash = compute_blind_index(tenant, raw_phone, 'phone')
            fields_corrected.append('phone_number')

        customer.save()

        # Update matching leads projection
        leads = Lead.objects.filter(business_number__tenant=tenant, enquiry__customer=customer)
        for lead in leads:
            if 'full_name' in corrections:
                lead.customer_name = customer.full_name
            if 'phone_number' in corrections:
                lead.phone_number = customer.whatsapp_number
                lead.phone_hash = customer.phone_hash
            if 'email' in corrections:
                lead.customer_email = customer.email
                lead.email_hash = customer.email_hash
            lead.save()

        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', 'privacy@convernix.internal'),
            action='DATA_CORRECTED',
            module='DataPrivacy',
            resource=f'Customer #{customer.id}',
            status='Success',
            metadata={'customer_id': customer.id, 'fields_corrected': fields_corrected},
        )

        return {'status': 'CORRECTED', 'customer_id': customer.id, 'fields_corrected': fields_corrected}

    @classmethod
    @transaction.atomic
    def process_erasure_request(cls, tenant, identifier: str, mode: str = 'ANONYMIZE', actor=None) -> Dict[str, Any]:
        """
        Executes privacy-aware deletion or anonymization.
        Pre-checks active legal holds; if held, rejects erasure and records legal hold exception.
        """
        from organization.models import AuditLog
        from whatsapp.models import Customer, Enquiry, WhatsAppMessage, Lead

        customer = cls.locate_customer(tenant, identifier)
        if not customer:
            raise ValueError('Data principal record not found within this organization.')

        # 1. Legal Hold check
        if RetentionService.is_under_legal_hold(tenant, 'CUSTOMER', str(customer.id)) or RetentionService.is_under_legal_hold(tenant, 'TENANT_WIDE'):
            AuditLog.objects.create(
                tenant=tenant,
                actor_name=getattr(actor, 'username', 'system'),
                actor_email=getattr(actor, 'email', 'privacy@convernix.internal'),
                action='ERASURE_BLOCKED_LEGAL_HOLD',
                module='DataPrivacy',
                resource=f'Customer #{customer.id}',
                status='Failed',
                metadata={'customer_id': customer.id, 'reason': 'Active legal hold prohibits deletion.'}
            )
            return {
                'status': 'RETAINED_UNDER_HOLD',
                'customer_id': customer.id,
                'message': 'Erasure cannot be executed because this record is subject to an active legal/investigation hold.',
            }

        # 2. Anonymize or Delete
        if mode == 'ANONYMIZE':
            customer.full_name = '[ANONYMIZED]'
            customer.organization_name = '[ANONYMIZED]'
            customer.whatsapp_number = '[ANONYMIZED]'
            customer.email = ''
            customer.phone_hash = ''
            customer.email_hash = ''
            customer.save()

            Lead.objects.filter(business_number__tenant=tenant, enquiry__customer=customer).update(
                customer_name='[ANONYMIZED]',
                phone_number='[ANONYMIZED]',
                phone_hash='',
                customer_email=None,
                email_hash='',
                message='[REDACTED_BY_DATA_PRINCIPAL_REQUEST]',
            )
            Enquiry.objects.filter(customer=customer).update(
                message='[REDACTED_BY_DATA_PRINCIPAL_REQUEST]'
            )
            WhatsAppMessage.objects.filter(customer=customer).update(
                content='[REDACTED_BY_DATA_PRINCIPAL_REQUEST]'
            )
            action_name = 'DATA_ANONYMIZED'
        else:
            # Full deletion
            # Purge attachment files
            for msg in WhatsAppMessage.objects.filter(customer=customer).exclude(attachment=''):
                if msg.attachment and os.path.exists(msg.attachment.path):
                    try:
                        os.remove(msg.attachment.path)
                    except Exception:
                        pass
            customer.delete()
            action_name = 'DATA_DELETED'

        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', 'privacy@convernix.internal'),
            action=action_name,
            module='DataPrivacy',
            resource=f'Customer #{identifier}',
            status='Success',
            metadata={'identifier': identifier, 'mode': mode},
        )

        return {'status': 'COMPLETED', 'action': action_name, 'identifier': identifier}

    @classmethod
    def process_consent_withdrawal(cls, tenant, identifier: str, purpose: str = 'MARKETING', actor=None) -> Dict[str, Any]:
        """Records an auditable consent withdrawal event in the privacy event ledger."""
        from organization.models import AuditLog, PrivacyEvent

        customer = cls.locate_customer(tenant, identifier)
        ref_id = str(customer.id) if customer else identifier

        event = PrivacyEvent.objects.create(
            tenant=tenant,
            data_principal_reference=ref_id,
            event_type='CONSENT_WITHDRAWN',
            purpose=purpose,
            source='Customer Request / DSR Workflow',
            metadata={'withdrawn_by': getattr(actor, 'email', 'user')},
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', 'system@convernix.internal'),
            action='CONSENT_WITHDRAWN',
            module='DataPrivacy',
            resource=f'Data Principal #{ref_id}',
            status='Success',
            metadata={'event_id': event.id, 'purpose': purpose},
        )

        return {'status': 'WITHDRAWN', 'event_id': event.id, 'purpose': purpose}

    @classmethod
    def execute_request(cls, req_obj, actor=None) -> Dict[str, Any]:
        """Orchestrates end-to-end execution of a PrivacyRequest model instance."""
        req_type = req_obj.request_type.upper()
        ident = str(getattr(req_obj, 'data_principal_reference', None) or getattr(req_obj, 'customer_id', ''))
        if req_type == 'ACCESS':
            res = cls.process_access_request(req_obj.tenant, ident, requested_by=actor)
            req_obj.status = 'COMPLETED'
            req_obj.resolution_notes = f"Export generated: token {res.get('export_token')}"
            req_obj.completion_date = timezone.now()
            req_obj.save()
            return res
        elif req_type == 'CORRECTION':
            raw_details = getattr(req_obj, 'details', '')
            if raw_details and raw_details.startswith('{'):
                try:
                    updates = json.loads(raw_details)
                except Exception:
                    updates = {}
            else:
                updates = getattr(req_obj, 'requested_changes', None) or {}
            res = cls.process_correction_request(req_obj.tenant, ident, updates, actor=actor)
            req_obj.status = 'COMPLETED'
            req_obj.resolution_notes = "Customer data re-encrypted and search indexes refreshed."
            req_obj.completion_date = timezone.now()
            req_obj.save()
            return res
        elif req_type == 'ERASURE':
            res = cls.process_erasure_request(req_obj.tenant, ident, actor=actor)
            req_obj.status = 'COMPLETED'
            req_obj.resolution_notes = "Customer data anonymized/erased in compliance with DPDP & retention policy."
            req_obj.completion_date = timezone.now()
            req_obj.save()
            return res
        elif req_type in ('WITHDRAW_CONSENT', 'CONSENT_WITHDRAWAL'):
            res = cls.process_consent_withdrawal(req_obj.tenant, ident, actor=actor)
            req_obj.status = 'COMPLETED'
            req_obj.resolution_notes = "Consent withdrawn and recorded in consent ledger."
            req_obj.completion_date = timezone.now()
            req_obj.save()
            return res
        else:
            raise ValueError(f"Unsupported request type: {req_type}")
