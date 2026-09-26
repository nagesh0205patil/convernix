import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class RetentionService:
    """Automated Privacy Retention Policy and Legal Hold Execution Engine."""

    @classmethod
    def is_under_legal_hold(cls, tenant, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Determines if a tenant or specific resource is protected by an active Legal/Investigation Hold."""
        from organization.models import LegalHold
        holds = LegalHold.objects.filter(tenant=tenant, is_active=True)
        if holds.filter(scope='TENANT_WIDE').exists():
            return True
        if resource_id and holds.filter(scope=resource_type, resource_id=str(resource_id)).exists():
            return True
        return False

    @classmethod
    def execute_retention_job(cls, tenant) -> Dict[str, Any]:
        """
        Executes retention policy sweeps for the tenant:
        1. Identifies expired records past policy threshold.
        2. Evaluates active legal holds.
        3. Executes deletion or anonymization.
        4. Removes associated disk media and search index hashes.
        5. Records tamper-evident audit evidence.
        """
        from organization.models import RetentionPolicy, AuditLog, DataExportRecord
        from whatsapp.models import Customer, Lead, WhatsAppMessage, Enquiry

        results: Dict[str, Any] = {
            'tenant_id': tenant.id,
            'policies_evaluated': 0,
            'records_deleted': 0,
            'records_anonymized': 0,
            'records_skipped_due_to_hold': 0,
            'media_purged': 0,
            'executed_at': timezone.now().isoformat(),
        }

        # Check tenant-wide hold first
        if cls.is_under_legal_hold(tenant, 'TENANT_WIDE'):
            results['status'] = 'SKIPPED_TENANT_WIDE_HOLD'
            logger.info('Retention sweep skipped for tenant=%s due to active tenant-wide legal hold', tenant.id)
            return results

        policies = RetentionPolicy.objects.filter(tenant=tenant, is_active=True)
        if not policies.exists():
            # Seed standard default policies if none configured
            default_defs = [
                ('LEADS', 365, 'ANONYMIZE'),
                ('CONVERSATIONS', 180, 'DELETE'),
                ('ATTACHMENTS', 90, 'DELETE'),
                ('EXPORTS', 7, 'DELETE'),
                ('AUDIT_LOGS', 730, 'DELETE'),
            ]
            for cat, days, act in default_defs:
                RetentionPolicy.objects.get_or_create(
                    tenant=tenant,
                    category=cat,
                    defaults={'retention_days': days, 'action': act, 'is_active': True}
                )
            policies = RetentionPolicy.objects.filter(tenant=tenant, is_active=True)

        now = timezone.now()

        for policy in policies:
            results['policies_evaluated'] += 1
            cutoff_date = now - timedelta(days=policy.retention_days)

            # --- 1. LEADS / CUSTOMERS ---
            if policy.category == 'LEADS':
                expired_enquiries = Enquiry.objects.filter(tenant=tenant, created_at__lt=cutoff_date)
                for enq in expired_enquiries:
                    if cls.is_under_legal_hold(tenant, 'ENQUIRY', str(enq.id)):
                        results['records_skipped_due_to_hold'] += 1
                        continue

                    if policy.action == 'ANONYMIZE':
                        # Anonymize Customer
                        cust = enq.customer
                        if cust and not cls.is_under_legal_hold(tenant, 'CUSTOMER', str(cust.id)):
                            cust.full_name = '[ANONYMIZED]'
                            cust.organization_name = '[ANONYMIZED]'
                            cust.email = ''
                            cust.email_hash = ''
                            # Clear phone hash to eliminate search index
                            cust.phone_hash = ''
                            cust.save()
                            results['records_anonymized'] += 1
                        enq.message = '[REDACTED_BY_RETENTION_POLICY]'
                        enq.save(update_fields=['message'])
                    else:
                        # Full delete
                        enq.delete()
                        results['records_deleted'] += 1

            # --- 2. CONVERSATIONS & MESSAGES ---
            elif policy.category == 'CONVERSATIONS':
                expired_enquiries = Enquiry.objects.filter(tenant=tenant, created_at__lt=cutoff_date)
                for enq in expired_enquiries:
                    if cls.is_under_legal_hold(tenant, 'ENQUIRY', str(enq.id)) or cls.is_under_legal_hold(tenant, 'CUSTOMER', str(enq.customer_id)):
                        results['records_skipped_due_to_hold'] += 1
                        continue
                    enq.delete()
                    results['records_deleted'] += 1

                expired_msgs = WhatsAppMessage.objects.filter(
                    customer__tenant=tenant,
                    timestamp__lt=cutoff_date
                )
                for msg in expired_msgs:
                    if cls.is_under_legal_hold(tenant, 'CUSTOMER', str(msg.customer_id)):
                        results['records_skipped_due_to_hold'] += 1
                        continue
                    if msg.attachment:
                        try:
                            if os.path.exists(msg.attachment.path):
                                os.remove(msg.attachment.path)
                                results['media_purged'] += 1
                        except Exception:
                            pass
                    msg.delete()
                    results['records_deleted'] += 1

            # --- 3. ATTACHMENTS ONLY ---
            elif policy.category == 'ATTACHMENTS':
                expired_attachments = WhatsAppMessage.objects.filter(
                    customer__tenant=tenant,
                    created_at__lt=cutoff_date
                ).exclude(attachment='')
                for msg in expired_attachments:
                    if cls.is_under_legal_hold(tenant, 'CUSTOMER', str(msg.customer_id)):
                        results['records_skipped_due_to_hold'] += 1
                        continue
                    try:
                        if msg.attachment and os.path.exists(msg.attachment.path):
                            os.remove(msg.attachment.path)
                            results['media_purged'] += 1
                    except Exception:
                        pass
                    msg.attachment = ''
                    msg.attachment_name = '[ATTACHMENT_PURGED_RETENTION]'
                    msg.save(update_fields=['attachment', 'attachment_name'])
                    results['records_deleted'] += 1

            # --- 4. TEMPORARY EXPORTS ---
            elif policy.category == 'EXPORTS':
                expired_exports = DataExportRecord.objects.filter(
                    tenant=tenant,
                    expires_at__lt=now
                )
                for exp in expired_exports:
                    if exp.file_path and os.path.exists(exp.file_path):
                        try:
                            os.remove(exp.file_path)
                            results['media_purged'] += 1
                        except Exception:
                            pass
                    exp.delete()
                    results['records_deleted'] += 1

        # Audit retention run
        AuditLog.objects.create(
            tenant=tenant,
            actor_name='RetentionEngine',
            actor_email='system@convernix.internal',
            action='RETENTION_JOB_EXECUTED',
            module='DataPrivacy',
            resource=f'Tenant #{tenant.id} Retention Sweep',
            status='Success',
            metadata=results,
        )

        return results
