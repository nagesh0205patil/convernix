import json
import os
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from organization.models import (
    AuditLog,
    ComplianceControl,
    DataExportRecord,
    LegalHold,
    PrivacyEvent,
    PrivacyNotice,
    PrivacyRequest,
    RetentionPolicy,
    SecurityIncident,
    TenantKeyMetadata,
    TenantKeyVersionHistory,
)
from organization.services.compliance_service import ComplianceService
from organization.services.crypto_service import (
    compute_blind_index,
    decrypt_tenant_data,
    encrypt_tenant_data,
    get_or_create_tenant_key_metadata,
)
from organization.services.data_classification import DataClassificationService
from organization.services.dsr_service import DsrService
from organization.services.kms_service import LocalKmsProvider, get_kms_provider
from organization.services.masking_service import MaskingService
from organization.services.mfa_service import MfaService
from organization.services.retention_service import RetentionService
from organization.services.tenant_key_service import rotate_tenant_key
from users.models import Tenant, TenantMembership
from whatsapp.models import (
    BusinessNumber,
    Customer,
    Department,
    DepartmentMember,
    Enquiry,
    Notification,
    WhatsAppMessage,
)

User = get_user_model()


class EnterpriseSecurityAndPrivacyTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Acme Corp', slug='acme-corp')
        self.tenant_b = Tenant.objects.create(name='Globex Corp', slug='globex-corp')

        self.owner_a = User.objects.create_user(
            username='owner_a', email='owner@acme.test', password='Password123!', role='owner', tenant=self.tenant_a
        )
        TenantMembership.objects.create(tenant=self.tenant_a, user=self.owner_a, role='owner', status='active')

        self.agent_a = User.objects.create_user(
            username='agent_a', email='agent@acme.test', password='Password123!', role='agent', tenant=self.tenant_a
        )
        TenantMembership.objects.create(tenant=self.tenant_a, user=self.agent_a, role='agent', status='active')

        self.client_owner = APIClient()
        self.client_owner.force_authenticate(user=self.owner_a)

        self.client_agent = APIClient()
        self.client_agent.force_authenticate(user=self.agent_a)

    def test_01_aes_256_gcm_authenticated_encryption_and_tamper_detection(self):
        """AES-256-GCM authenticated ciphertext format and tamper authentication tag verification."""
        plaintext = 'Sensitive Customer Information'
        ciphertext = encrypt_tenant_data(self.tenant_a, plaintext)

        self.assertTrue(ciphertext.startswith('cvx:v1:'))
        parts = ciphertext.split(':')
        self.assertEqual(len(parts), 4)  # cvx, v1, nonce_b64, ct_tag_b64

        # Decrypt succeeds with valid key and unaltered ciphertext
        decrypted = decrypt_tenant_data(self.tenant_a, ciphertext)
        self.assertEqual(decrypted, plaintext)

        # Tampering with single byte in ciphertext must fail authenticated tag check
        import base64
        nonce = parts[2]
        raw_ct_tag = base64.b64decode(parts[3])
        tampered_raw = bytearray(raw_ct_tag)
        tampered_raw[0] ^= 0xFF  # Flip bits
        tampered_ct = f"cvx:v1:{nonce}:{base64.b64encode(tampered_raw).decode('ascii')}"

        with self.assertRaises(Exception):
            decrypt_tenant_data(self.tenant_a, tampered_ct)

    def test_02_per_tenant_dek_isolation(self):
        """Cross-tenant encryption key isolation: Tenant B cannot decrypt Tenant A's ciphertext."""
        plaintext = 'Confidential Lead Data for Acme'
        ciphertext_a = encrypt_tenant_data(self.tenant_a, plaintext)

        with self.assertRaises(Exception):
            decrypt_tenant_data(self.tenant_b, ciphertext_a)

    def test_03_key_rotation_and_versioned_decryption(self):
        """Envelope encryption key rotation: increments key version and preserves backward decryptability."""
        # 1. Encrypt with v1
        ct_v1 = encrypt_tenant_data(self.tenant_a, 'Message in Version 1')
        self.assertTrue(ct_v1.startswith('cvx:v1:'))

        # 2. Rotate Tenant DEK
        new_meta = rotate_tenant_key(self.tenant_a, rotated_by=self.owner_a)
        self.assertEqual(new_meta['new_version'], 2)

        # 3. New encrypt uses v2
        ct_v2 = encrypt_tenant_data(self.tenant_a, 'Message in Version 2')
        self.assertTrue(ct_v2.startswith('cvx:v2:'))

        # 4. Old v1 ciphertext remains decryptable
        self.assertEqual(decrypt_tenant_data(self.tenant_a, ct_v1), 'Message in Version 1')
        self.assertEqual(decrypt_tenant_data(self.tenant_a, ct_v2), 'Message in Version 2')

        # 5. Audit trail recorded for rotation
        self.assertTrue(
            AuditLog.objects.filter(tenant=self.tenant_a, action='KEY_ROTATED').exists()
        )

    def test_04_hmac_sha256_blind_index_search(self):
        """Exact-match search via HMAC-SHA256 blind index without decrypting records."""
        raw_phone = '+919876543210'
        raw_email = 'customer@example.com'

        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Rahul Patil',
            whatsapp_number=raw_phone,
            email=raw_email,
        )

        # Stored phone & email must be encrypted
        self.assertTrue(customer.whatsapp_number.startswith('cvx:v'))
        self.assertTrue(customer.email.startswith('cvx:v'))
        self.assertTrue(bool(customer.phone_hash))
        self.assertTrue(bool(customer.email_hash))

        # Lookup by phone blind index
        found = Customer.objects.find_by_phone(self.tenant_a, raw_phone)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, customer.id)
        self.assertEqual(found.plain_phone, raw_phone)

        # Blind index isolation: Tenant B computing hash for same number gets different hash
        hash_a = compute_blind_index(self.tenant_a, raw_phone, 'phone')
        hash_b = compute_blind_index(self.tenant_b, raw_phone, 'phone')
        self.assertNotEqual(hash_a, hash_b)

    def test_05_field_masking_and_audited_reveal_api(self):
        """Field masking for unauthorized users and audited reveal endpoint for authorized users."""
        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Anita Desai',
            whatsapp_number='+919876543210',
            email='anita.desai@example.com',
        )
        dept = Department.objects.create(name='Sales', slug='sales-sec')
        enquiry = Enquiry.objects.create(
            tenant=self.tenant_a,
            customer=customer,
            department=dept,
            message='I want enterprise pricing',
        )

        # 1. Agent without lead.phone.view gets masked phone
        res_agent = self.client_agent.get('/api/whatsapp/enquiries/')
        self.assertEqual(res_agent.status_code, 200)
        items = res_agent.data.get('results', res_agent.data)
        self.assertTrue(len(items) > 0)
        target = next(item for item in items if item['id'] == enquiry.id)
        self.assertIn('******', target['phone_number'])
        self.assertEqual(target['phone_number'], '+91 ******3210')

        # 2. Owner (privileged) calls reveal endpoint
        res_reveal = self.client_owner.post(f'/api/whatsapp/customers/{customer.id}/reveal-phone/')
        self.assertEqual(res_reveal.status_code, 200)
        self.assertEqual(res_reveal.data['phone_number'], '+919876543210')
        self.assertTrue(res_reveal.data['is_unmasked'])

        # 3. Audit log PHONE_REVEALED must be logged
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant_a,
                action='PHONE_REVEALED',
                resource__contains=str(customer.id),
            ).exists()
        )

    def test_06_tamper_evident_audit_log_hash_chain(self):
        """Audit log HMAC-SHA256 signature chain verification and tamper detection."""
        log1 = AuditLog.objects.create(
            tenant=self.tenant_a,
            actor_name='Admin 1',
            actor_email='admin1@acme.test',
            action='USER_CREATED',
            module='IAM',
            resource='User #1',
            status='Success',
        )
        log2 = AuditLog.objects.create(
            tenant=self.tenant_a,
            actor_name='Admin 1',
            actor_email='admin1@acme.test',
            action='ROLE_UPDATED',
            module='IAM',
            resource='Role #1',
            status='Success',
        )

        self.assertEqual(log2.previous_hash, log1.tamper_hash)

        # Verification passes on unaltered log chain
        verify_result = AuditLog.verify_integrity(self.tenant_a)
        self.assertTrue(verify_result['valid'])

        # Tampering with an audit record detects alteration
        AuditLog.objects.filter(pk=log1.pk).update(action='MALICIOUS_ALTERATION')
        tamper_result = AuditLog.verify_integrity(self.tenant_a)
        self.assertFalse(tamper_result['valid'])
        self.assertEqual(tamper_result['tampered_log_id'], log1.pk)

    def test_07_dsr_privacy_access_and_export_lifecycle(self):
        """Data Principal Request (DSR) ACCESS workflow: discovery, JSON export, and download."""
        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Vikram Seth',
            whatsapp_number='+919123456789',
            email='vikram@acme.test',
        )
        dept = Department.objects.create(name='Support', slug='support-dsr')
        Enquiry.objects.create(
            tenant=self.tenant_a, customer=customer, department=dept, message='Test enquiry for DSR'
        )

        req = PrivacyRequest.objects.create(
            tenant=self.tenant_a,
            request_id='DSR-TEST-001',
            data_principal_reference=str(customer.id),
            request_type='ACCESS',
            status='RECEIVED',
        )

        result = DsrService.execute_request(req, actor=self.owner_a)
        self.assertIn('export_token', result)
        req.refresh_from_db()
        self.assertEqual(req.status, 'COMPLETED')

        # Download temporary export file
        token = result['export_token']
        res_dl = self.client_owner.get(f'/api/privacy/exports/{token}/download/')
        self.assertEqual(res_dl.status_code, 200)

    def test_08_dsr_privacy_correction_and_erasure(self):
        """DSR CORRECTION (in-place re-encryption) and ERASURE (anonymization)."""
        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Original Name',
            whatsapp_number='+919988776655',
            email='original@acme.test',
        )

        # 1. Correction
        req_corr = PrivacyRequest.objects.create(
            tenant=self.tenant_a,
            request_id='DSR-CORR-01',
            data_principal_reference=str(customer.id),
            request_type='CORRECTION',
            details=json.dumps({'full_name': 'Corrected Name', 'email': 'corrected@acme.test'}),
            status='RECEIVED',
        )
        DsrService.execute_request(req_corr, actor=self.owner_a)
        customer.refresh_from_db()
        self.assertEqual(customer.plain_name, 'Corrected Name')
        self.assertEqual(customer.plain_email, 'corrected@acme.test')

        # 2. Erasure
        req_erase = PrivacyRequest.objects.create(
            tenant=self.tenant_a,
            request_id='DSR-ERASE-01',
            data_principal_reference=str(customer.id),
            request_type='ERASURE',
            status='RECEIVED',
        )
        DsrService.execute_request(req_erase, actor=self.owner_a)
        customer.refresh_from_db()
        self.assertIn('ANONYMIZED', customer.plain_name.upper())
        self.assertIn('ANONYMIZED', customer.plain_phone.upper())

    def test_09_automated_retention_sweep_and_legal_hold(self):
        """Automated retention policy sweep deletes expired records unless protected by LegalHold."""
        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Old Customer',
            whatsapp_number='+919111122222',
        )
        dept = Department.objects.create(name='Legal', slug='legal-ret')
        enq = Enquiry.objects.create(
            tenant=self.tenant_a, customer=customer, department=dept, message='Old enquiry'
        )

        # Backdate enquiry beyond retention threshold
        past_date = timezone.now() - timedelta(days=200)
        Enquiry.objects.filter(pk=enq.pk).update(created_at=past_date)

        RetentionPolicy.objects.create(
            tenant=self.tenant_a, category='CONVERSATIONS', retention_days=180, action='DELETE'
        )

        # 1. With active LegalHold, record must NOT be deleted
        hold = LegalHold.objects.create(
            tenant=self.tenant_a,
            hold_id='HOLD-001',
            name='Litigation Hold',
            reason='Pending regulatory inquiry',
            scope='ENQUIRY',
            resource_id=str(enq.id),
            is_active=True,
        )

        sweep1 = RetentionService.execute_retention_job(self.tenant_a)
        self.assertTrue(Enquiry.objects.filter(pk=enq.pk).exists())
        self.assertEqual(sweep1['records_skipped_due_to_hold'], 1)

        # 2. Release hold -> sweep deletes expired record
        hold.is_active = False
        hold.save()

        sweep2 = RetentionService.execute_retention_job(self.tenant_a)
        self.assertFalse(Enquiry.objects.filter(pk=enq.pk).exists())
        self.assertEqual(sweep2['records_deleted'], 1)

    def test_10_mfa_totp_and_single_use_recovery_codes(self):
        """RFC 6238 TOTP verification and emergency single-use recovery code consumption."""
        secret = MfaService.generate_totp_secret()
        uri = MfaService.get_provisioning_uri(secret, self.owner_a.email)
        self.assertTrue(uri.startswith('otpauth://totp/'))

        # Compute valid TOTP code
        current_interval = int(timezone.now().timestamp()) // 30
        valid_code = MfaService._compute_totp(secret, current_interval)
        self.assertTrue(MfaService.verify_totp(secret, valid_code))
        self.assertFalse(MfaService.verify_totp(secret, '000000'))

        # Single-use recovery codes
        plain_codes, hashed_codes = MfaService.generate_recovery_codes(count=4)
        self.owner_a.mfa_recovery_codes = hashed_codes
        self.owner_a.save()

        # First use succeeds
        first_code = plain_codes[0]
        self.assertTrue(MfaService.verify_and_consume_recovery_code(self.owner_a, first_code))
        self.owner_a.refresh_from_db()
        self.assertEqual(len(self.owner_a.mfa_recovery_codes), 3)

        # Replay attempt fails
        self.assertFalse(MfaService.verify_and_consume_recovery_code(self.owner_a, first_code))

    def test_11_compliance_telemetry_endpoint_and_strict_disclaimer(self):
        """Compliance telemetry reports factual technical controls with clear non-certification disclaimer."""
        res = self.client_owner.get('/api/admin/compliance/telemetry/')
        self.assertEqual(res.status_code, 200)

        data = res.data
        self.assertIn('disclaimer', data)
        self.assertIn('support compliance readiness', data['disclaimer'])
        self.assertEqual(data['encryption']['status'], 'ACTIVE')
        self.assertIn('AES-256-GCM', data['encryption']['algorithm'])
        self.assertIn(data['kms']['status'], ('healthy', 'ONLINE'))
        self.assertEqual(data['audit_logging']['status'], 'ACTIVE')

    @override_settings(ZERO_PII_NOTIFICATIONS=True)
    def test_12_zero_pii_notifications_and_payload_redaction(self):
        """Zero-PII notification mode sanitizes notification parameters and redacts stored payloads."""
        customer = Customer.objects.create(
            tenant=self.tenant_a,
            full_name='Secret Customer',
            whatsapp_number='+919876543210',
        )
        dept = Department.objects.create(name='Confidential', slug='confidential-team')
        member = DepartmentMember.objects.create(
            department=dept, name='Internal Staff', whatsapp_number='+919800000000'
        )
        biz = BusinessNumber.objects.create(
            number='+15550001111', phone_number_id='pid1', label='Main', is_active=True
        )
        enquiry = Enquiry.objects.create(
            tenant=self.tenant_a,
            customer=customer,
            department=dept,
            message='Highly confidential enquiry text',
        )
        from whatsapp.models import Lead
        Lead.objects.create(
            business_number=biz,
            customer_name='Secret Customer',
            phone_number='+919876543210',
            message='Highly confidential enquiry text',
            enquiry=enquiry,
        )

        notification = Notification.objects.create(
            enquiry=enquiry, recipient=member, recipient_number=member.whatsapp_number
        )

        with patch('whatsapp.tasks.send_template_message') as mock_send:
            mock_send.return_value = (
                {'messages': [{'id': 'wamid.sec'}]},
                {'template': {'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': '+919876543210'}]}]}},
                200,
            )
            from whatsapp.tasks import send_department_notification
            send_department_notification(notification.pk)

            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            params = args[1]

            # In ZERO-PII mode, params must NOT contain raw customer phone or full message text
            self.assertNotIn('+919876543210', params)
            self.assertNotIn('Highly confidential enquiry text', params)
            self.assertIn('Login to Convernix to view and respond.', params[3])

            notification.refresh_from_db()
            self.assertEqual(notification.status, 'sent')
            # Stored payload must be redacted
            payload_str = json.dumps(notification.request_payload)
            self.assertNotIn('+919876543210', payload_str)
            self.assertIn('[REDACTED_FOR_PRIVACY]', payload_str)
