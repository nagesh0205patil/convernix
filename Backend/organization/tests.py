from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import Tenant
from .models import AuditLog, OrganizationProfile

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class OrganizationAdminTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Acme Corp', slug='acme-corp', tier='mid', status='active')
        self.tenant_b = Tenant.objects.create(name='Beta Ltd', slug='beta-ltd', tier='small', status='active')

        self.owner_a = User.objects.create_user(
            username='owner_a@acme.com', email='owner_a@acme.com', password='password123',
            role='owner', tenant=self.tenant_a, is_staff=True,
        )
        self.agent_a = User.objects.create_user(
            username='agent_a@acme.com', email='agent_a@acme.com', password='password123',
            role='agent', tenant=self.tenant_a,
        )
        self.owner_b = User.objects.create_user(
            username='owner_b@beta.com', email='owner_b@beta.com', password='password123',
            role='owner', tenant=self.tenant_b, is_staff=True,
        )

        self.client = APIClient()

    def test_owner_accesses_and_updates_organization_profile(self):
        self.client.force_authenticate(self.owner_a)
        response = self.client.get('/api/admin/organization/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['organization_name'], 'Acme Corp')
        self.assertTrue(response.data['org_id'].startswith('ORG-CLD-'))

        update_res = self.client.put('/api/admin/organization/', {
            'legal_business_name': 'Acme Global Technologies Pvt Ltd',
            'industry': 'Software & SaaS',
            'business_email': 'contact@acme.io',
        }, format='json')
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.data['legal_business_name'], 'Acme Global Technologies Pvt Ltd')

        # Verify audit log was recorded
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant_a, action='Updated organization profile').exists())

    def test_agent_is_denied_access_to_organization_settings(self):
        self.client.force_authenticate(self.agent_a)
        response = self.client.put('/api/admin/organization/', {'industry': 'Retail'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn("permission", response.data['detail'])

    def test_tenant_isolation_prevents_cross_tenant_leakage(self):
        # Create audit log for tenant A
        AuditLog.log(self.tenant_a, 'Owner A', 'Test action', 'Settings', 'Resource A')
        # Create audit log for tenant B
        AuditLog.log(self.tenant_b, 'Owner B', 'Secret action', 'IAM', 'Resource B')

        self.client.force_authenticate(self.owner_a)
        response = self.client.get('/api/admin/audit-logs/')
        self.assertEqual(response.status_code, 200)
        logs = response.data.get('audit_logs', [])
        # Tenant A must never see Tenant B's logs
        for entry in logs:
            self.assertNotEqual(entry['actor_name'], 'Owner B')
            self.assertNotEqual(entry['resource'], 'Resource B')

    def test_whatsapp_connection_and_diagnostics(self):
        self.client.force_authenticate(self.owner_a)
        # Run diagnostics test
        test_res = self.client.post('/api/admin/whatsapp/?action=test')
        self.assertEqual(test_res.status_code, 200)
        self.assertEqual(test_res.data['overall_status'], 'success')
        self.assertEqual(len(test_res.data['checks']), 5)

        # Connect WhatsApp number
        connect_res = self.client.post('/api/admin/whatsapp/', {
            'phone_number': '+91 98765 12345',
            'display_name': 'Acme WhatsApp Support',
            'phone_number_id': 'PNID_12345',
            'business_account_id': 'WABA_12345',
            'meta_app_id': 'APP_12345',
            'meta_access_token': 'EAABsecrettoken',
            'meta_app_secret': 'supersecretkey',
        }, format='json')
        self.assertEqual(connect_res.status_code, 200)
        self.assertEqual(connect_res.data['status'], 'connected')

    def test_audit_logs_are_immutable_and_exportable(self):
        self.client.force_authenticate(self.owner_a)
        export_res = self.client.get('/api/admin/audit-logs/?export=csv')
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res['Content-Type'], 'text/csv')
        content = export_res.content.decode('utf-8')
        self.assertIn('Timestamp,Actor,Action,Module,Resource,IP Address,Status', content)

