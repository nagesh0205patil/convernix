import hashlib
import json
import time
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from users.models import Tenant, User
from whatsapp.models import Lead, Customer, Enquiry, Department, BusinessNumber
from organization.models import AuditLog
from integrations.models import (
    ServiceAccount,
    ApiKey,
    IdempotencyRecord,
    WebhookEndpoint,
    WebhookDelivery,
    ConnectorInstance,
    ConnectorFieldMapping,
    OutboxEvent,
)
from integrations.views.v1_api_keys import generate_secure_api_key
from integrations.webhooks import (
    compute_webhook_signature,
    verify_webhook_signature,
    replay_webhook_delivery,
)
from integrations.ssrf import validate_safe_url, SSRFValidationError
from integrations.sync_engine import apply_transformation, transform_convernix_to_external


class IntegrationsModuleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Tenant A
        self.tenant_a = Tenant.objects.create(
            name='Acme Corp',
            slug='acme-corp',
            status='ACTIVE',
        )
        self.b_num_a = BusinessNumber.objects.create(
            tenant=self.tenant_a,
            number='+919876543210',
            label='Acme Primary',
        )
        self.dept_a = Department.objects.create(
            tenant=self.tenant_a,
            name='Support',
            slug='support',
        )

        # Tenant B
        self.tenant_b = Tenant.objects.create(
            name='Globex Inc',
            slug='globex-inc',
            status='ACTIVE',
        )
        self.b_num_b = BusinessNumber.objects.create(
            tenant=self.tenant_b,
            number='+919876543299',
            label='Globex Primary',
        )
        self.dept_b = Department.objects.create(
            tenant=self.tenant_b,
            name='Support',
            slug='support-b',
        )

        # Service Account & API Key for Tenant A
        self.sa_a = ServiceAccount.objects.create(
            tenant=self.tenant_a,
            name='Acme Zapier Integration',
            status='active',
        )
        self.raw_key_a = generate_secure_api_key('cvx_live_')
        self.key_prefix_a = self.raw_key_a[:16]
        self.key_hash_a = hashlib.sha256(self.raw_key_a.encode('utf-8')).hexdigest()

        self.api_key_a = ApiKey.objects.create(
            tenant=self.tenant_a,
            service_account=self.sa_a,
            name='Acme Primary Key',
            key_prefix=self.key_prefix_a,
            secret_hash=self.key_hash_a,
            scopes=['*'],
            is_active=True,
            expires_at=timezone.now() + timedelta(days=90),
        )

        # Service Account & API Key for Tenant B
        self.sa_b = ServiceAccount.objects.create(
            tenant=self.tenant_b,
            name='Globex HubSpot Integration',
            status='active',
        )
        self.raw_key_b = generate_secure_api_key('cvx_live_')
        self.key_prefix_b = self.raw_key_b[:16]
        self.key_hash_b = hashlib.sha256(self.raw_key_b.encode('utf-8')).hexdigest()

        self.api_key_b = ApiKey.objects.create(
            tenant=self.tenant_b,
            service_account=self.sa_b,
            name='Globex Primary Key',
            key_prefix=self.key_prefix_b,
            secret_hash=self.key_hash_b,
            scopes=['*'],
            is_active=True,
            expires_at=timezone.now() + timedelta(days=90),
        )

    # =========================================================================
    # 1. Multi-Tenant Security & Horizontal Cross-Tenant Isolation
    # =========================================================================
    def test_cross_tenant_isolation_lead_retrieval(self):
        """Tenant B must never retrieve, inspect, or infer Tenant A's resources."""
        # Tenant A creates Lead A
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        resp_create = self.client.post('/api/v1/leads/', {
            'customer_name': 'Alice Smith',
            'phone_number': '+919999911111',
            'customer_email': 'alice@example.com',
            'message': 'Interested in enterprise plan',
        }, format='json')
        self.assertEqual(resp_create.status_code, status.HTTP_201_CREATED)
        lead_a_id = resp_create.data['id']

        # Tenant A can read Lead A
        resp_get_a = self.client.get(f'/api/v1/leads/{lead_a_id}/')
        self.assertEqual(resp_get_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get_a.data['customer_name'], 'Alice Smith')

        # Tenant B attempts to read Lead A
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_b}')
        resp_get_b = self.client.get(f'/api/v1/leads/{lead_a_id}/')
        self.assertEqual(resp_get_b.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_get_b.data['error']['code'], 'RESOURCE_NOT_FOUND')

        # Tenant B attempts to update Lead A
        resp_patch_b = self.client.patch(f'/api/v1/leads/{lead_a_id}/', {'status': 'resolved'}, format='json')
        self.assertEqual(resp_patch_b.status_code, status.HTTP_404_NOT_FOUND)

        # Lead A in Tenant A is unchanged
        lead_a = Lead.objects.get(pk=lead_a_id)
        self.assertEqual(lead_a.status, 'new')

    def test_cross_tenant_isolation_webhooks_and_deliveries(self):
        """Tenant B cannot see Tenant A's webhook endpoints or deliveries."""
        # Tenant A creates a webhook
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        resp_wh = self.client.post('/api/v1/webhooks/', {
            'name': 'Acme Webhook',
            'url': 'https://api.acme-corp-partner.example/hook',
            'event_filters': ['lead.*'],
        }, format='json')
        self.assertEqual(resp_wh.status_code, status.HTTP_201_CREATED)
        webhook_a_id = resp_wh.data['id']

        # Tenant B queries webhooks list
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_b}')
        resp_list_b = self.client.get('/api/v1/webhooks/')
        self.assertEqual(resp_list_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_list_b.data), 0)

        # Tenant B attempts to view or delete Tenant A webhook
        resp_detail_b = self.client.get(f'/api/v1/webhooks/{webhook_a_id}/')
        self.assertEqual(resp_detail_b.status_code, status.HTTP_404_NOT_FOUND)
        resp_delete_b = self.client.delete(f'/api/v1/webhooks/{webhook_a_id}/')
        self.assertEqual(resp_delete_b.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # 2. Cryptographic API Key Lifecycle & Security
    # =========================================================================
    def test_api_key_authentication_and_headers(self):
        # Authenticate via X-API-Key header
        self.client.credentials(HTTP_X_API_KEY=self.raw_key_a)
        resp = self.client.get('/api/v1/leads/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('X-Request-ID', resp.headers)
        self.assertIn('X-API-Version', resp.headers)

    def test_expired_api_key_rejected(self):
        expired_raw = generate_secure_api_key('cvx_live_')
        ApiKey.objects.create(
            tenant=self.tenant_a,
            name='Expired Key',
            key_prefix=expired_raw[:16],
            secret_hash=hashlib.sha256(expired_raw.encode('utf-8')).hexdigest(),
            scopes=['*'],
            is_active=True,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired_raw}')
        resp = self.client.get('/api/v1/leads/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_api_key_rejected(self):
        self.api_key_a.is_active = False
        self.api_key_a.revoked_at = timezone.now()
        self.api_key_a.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        resp = self.client.get('/api/v1/leads/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_disabled_service_account_rejects_key(self):
        self.sa_a.status = 'disabled'
        self.sa_a.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        resp = self.client.get('/api/v1/leads/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ip_restriction_enforcement(self):
        ip_restricted_raw = generate_secure_api_key('cvx_live_')
        ApiKey.objects.create(
            tenant=self.tenant_a,
            name='IP Restricted Key',
            key_prefix=ip_restricted_raw[:16],
            secret_hash=hashlib.sha256(ip_restricted_raw.encode('utf-8')).hexdigest(),
            scopes=['*'],
            ip_restrictions=['198.51.100.0/24', '203.0.113.50'],
            is_active=True,
        )
        # Disallowed IP
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {ip_restricted_raw}', REMOTE_ADDR='192.0.2.1')
        resp_blocked = self.client.get('/api/v1/leads/')
        self.assertEqual(resp_blocked.status_code, status.HTTP_403_FORBIDDEN)

        # Allowed IP
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {ip_restricted_raw}', REMOTE_ADDR='198.51.100.15')
        resp_allowed = self.client.get('/api/v1/leads/')
        self.assertEqual(resp_allowed.status_code, status.HTTP_200_OK)

    # =========================================================================
    # 3. Granular Scopes Enforcement
    # =========================================================================
    def test_scope_guard_read_vs_create(self):
        read_only_raw = generate_secure_api_key('cvx_live_')
        ApiKey.objects.create(
            tenant=self.tenant_a,
            name='Read Only Lead Key',
            key_prefix=read_only_raw[:16],
            secret_hash=hashlib.sha256(read_only_raw.encode('utf-8')).hexdigest(),
            scopes=['lead:read'],
            is_active=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {read_only_raw}')

        # Read succeeds
        resp_read = self.client.get('/api/v1/leads/')
        self.assertEqual(resp_read.status_code, status.HTTP_200_OK)

        # Create fails with 403
        resp_write = self.client.post('/api/v1/leads/', {
            'customer_name': 'Hacker',
            'phone_number': '+919999900000',
            'message': 'Attempting write without lead:create',
        }, format='json')
        self.assertEqual(resp_write.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 4. Idempotency Engine
    # =========================================================================
    def test_idempotency_caching_and_conflict_handling(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        idempotency_key = 'idem-req-lead-001'

        payload = {
            'customer_name': 'Bob Idempotent',
            'phone_number': '+918888877777',
            'message': 'First submission',
        }

        # 1. First execution
        resp1 = self.client.post(
            '/api/v1/leads/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        lead_id = resp1.data['id']

        # 2. Replay with identical payload and key: returns cached response
        resp2 = self.client.post(
            '/api/v1/leads/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data['id'], lead_id)
        self.assertEqual(resp2.headers.get('X-Cache-Lookup'), 'IDEMPOTENT_HIT')

        # Only 1 lead was created
        self.assertEqual(Lead.objects.filter(business_number__tenant=self.tenant_a).count(), 1)

        # 3. Reuse key with different payload: returns 409 conflict
        different_payload = {
            'customer_name': 'Eve Malicious',
            'phone_number': '+918888877777',
            'message': 'Tampered payload with old key',
        }
        resp3 = self.client.post(
            '/api/v1/leads/',
            different_payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(resp3.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp3.data['error']['code'], 'IDEMPOTENCY_CONFLICT')

    # =========================================================================
    # 5. Rate Limiting
    # =========================================================================
    def test_rate_limiting_enforcement(self):
        from integrations.rate_limiter import TokenBucketLimiter
        limiter = TokenBucketLimiter('test_bucket', capacity=3, fill_rate=0.1)

        # Consume 3 tokens
        allowed1, rem1, retry1, _ = limiter.consume(1)
        allowed2, rem2, retry2, _ = limiter.consume(1)
        allowed3, rem3, retry3, _ = limiter.consume(1)
        self.assertTrue(allowed1)
        self.assertTrue(allowed2)
        self.assertTrue(allowed3)

        # 4th request exceeds capacity
        allowed4, rem4, retry4, limit = limiter.consume(1)
        self.assertFalse(allowed4)
        self.assertEqual(rem4, 0)
        self.assertGreater(retry4, 0)

    # =========================================================================
    # 6. Webhook Signing & HMAC-SHA256 Verification
    # =========================================================================
    def test_webhook_hmac_sha256_signing_and_verification(self):
        secret = 'whsec_test_secret_key_1234567890'
        timestamp = str(int(time.time()))
        body = json.dumps({'event': 'lead.created', 'id': 'lead_123'}, separators=(',', ':'))

        signature = compute_webhook_signature(secret, timestamp, body)
        self.assertTrue(signature)
        self.assertEqual(len(signature), 64)  # Hex encoded SHA256

        # Verification passes with valid parameters
        self.assertTrue(verify_webhook_signature(secret, timestamp, body, signature))

        # Tampered payload fails
        tampered_body = json.dumps({'event': 'lead.created', 'id': 'lead_tampered'}, separators=(',', ':'))
        self.assertFalse(verify_webhook_signature(secret, timestamp, tampered_body, signature))

        # Tampered secret fails
        self.assertFalse(verify_webhook_signature('wrong_secret', timestamp, body, signature))

        # Expired timestamp outside tolerance window fails
        old_timestamp = str(int(time.time()) - 600)
        old_sig = compute_webhook_signature(secret, old_timestamp, body)
        self.assertFalse(verify_webhook_signature(secret, old_timestamp, body, old_sig, tolerance_seconds=300))

    # =========================================================================
    # 7. SSRF & Safe Egress Protection
    # =========================================================================
    def test_ssrf_prohibits_private_ips_and_metadata(self):
        blocked_urls = [
            'http://127.0.0.1:8000/webhook',
            'http://localhost/hook',
            'http://169.254.169.254/latest/meta-data/',
            'http://10.0.0.1/callback',
            'http://172.16.0.1:8080/internal',
            'http://192.168.1.1/hook',
            'http://metadata.google.internal/computeMetadata/v1/',
        ]

        for url in blocked_urls:
            with self.subTest(url=url):
                with self.assertRaises(SSRFValidationError):
                    validate_safe_url(url, allow_http=True)

    def test_ssrf_allows_legitimate_https_urls(self):
        parsed, ips = validate_safe_url('https://example.com/webhook/receive')
        self.assertEqual(parsed.hostname, 'example.com')
        self.assertTrue(len(ips) > 0)

    # =========================================================================
    # 8. Transactional Outbox Pattern
    # =========================================================================
    def test_transactional_outbox_event_persistence(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')
        resp = self.client.post('/api/v1/leads/', {
            'customer_name': 'Outbox Test Lead',
            'phone_number': '+917777788888',
            'message': 'Testing transactional outbox',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Verify OutboxEvent was created in the database
        outbox = OutboxEvent.objects.filter(tenant=self.tenant_a, event_type='lead.created').first()
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.status, 'pending')
        self.assertEqual(outbox.payload['data']['customer_name'], 'Outbox Test Lead')

    # =========================================================================
    # 9. Connector Marketplace & Field Mapping
    # =========================================================================
    def test_connector_field_transformation(self):
        # Direct
        self.assertEqual(apply_transformation('Acme', 'direct', {}), 'Acme')

        # Enum map
        cfg = {'mapping': {'new': 'OPEN', 'in_progress': 'WORKING', 'resolved': 'CLOSED'}}
        self.assertEqual(apply_transformation('new', 'enum_map', cfg), 'OPEN')
        self.assertEqual(apply_transformation('unknown', 'enum_map', cfg), 'unknown')

        # Boolean cast
        self.assertTrue(apply_transformation('yes', 'boolean_cast', {}))
        self.assertFalse(apply_transformation('0', 'boolean_cast', {}))

        # Default value
        self.assertEqual(apply_transformation(None, 'default_value', {'default': 'Unknown Org'}), 'Unknown Org')

    def test_connector_marketplace_and_instance_creation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')

        # View marketplace
        resp_mkt = self.client.get('/api/v1/integrations/marketplace/')
        self.assertEqual(resp_mkt.status_code, status.HTTP_200_OK)
        keys = [item['key'] for item in resp_mkt.data]
        self.assertIn('hubspot', keys)
        self.assertIn('salesforce', keys)
        self.assertIn('slack', keys)

        # Connect HubSpot instance
        resp_inst = self.client.post('/api/v1/integrations/instances/', {
            'connector_key': 'hubspot',
            'name': 'Marketing HubSpot',
            'config': {'portal_id': '12345678'},
            'credentials': {'access_token': 'test_token_hs'},
        }, format='json')
        self.assertEqual(resp_inst.status_code, status.HTTP_201_CREATED)
        inst_id = resp_inst.data['id']

        # Test connection
        resp_test = self.client.post(f'/api/v1/integrations/instances/{inst_id}/test/')
        self.assertEqual(resp_test.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_test.data['success'])

    # =========================================================================
    # 10. Audit Logging Non-Repudiation
    # =========================================================================
    def test_integration_audit_log_recorded(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.raw_key_a}')

        # Create API key
        resp_key = self.client.post('/api/v1/api-keys/', {
            'name': 'Audited API Key',
            'scopes': ['lead:read'],
        }, format='json')
        self.assertEqual(resp_key.status_code, status.HTTP_201_CREATED)

        # Verify audit log was recorded
        audit = AuditLog.objects.filter(tenant=self.tenant_a, action='API_KEY_CREATED').first()
        self.assertIsNotNone(audit)
        self.assertIn('Audited API Key', audit.resource)
        self.assertTrue(audit.tamper_hash)

