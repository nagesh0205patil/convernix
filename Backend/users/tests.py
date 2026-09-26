from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='http://frontend.test',
)
class IAMTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='password123',
            role='owner', is_staff=True, is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_owner_invites_and_recipient_activates_account(self):
        response = self.client.post('/api/iam/invitations/', {
            'email': 'viewer@example.com', 'role': 'viewer', 'team_name': 'Support',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        invited = User.objects.get(email='viewer@example.com')
        self.assertFalse(invited.is_active)
        self.assertFalse(invited.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        token = mail.outbox[0].body.split('?invite=', 1)[1]

        self.client.force_authenticate(user=None)
        accepted = self.client.post('/api/auth/invitations/accept/', {
            'token': token, 'first_name': 'View', 'last_name': 'Only', 'password': 'newpassword123',
        }, format='json')
        self.assertEqual(accepted.status_code, 200)
        invited.refresh_from_db()
        self.assertTrue(invited.is_active)
        self.assertTrue(invited.check_password('newpassword123'))

    def test_admin_cannot_grant_owner_access(self):
        admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='password123', role='admin', is_staff=True,
        )
        self.client.force_authenticate(admin)
        response = self.client.post('/api/iam/invitations/', {'email': 'new@example.com', 'role': 'owner'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_viewer_cannot_create_campaign_but_can_read(self):
        viewer = User.objects.create_user(
            username='viewer', email='read@example.com', password='password123', role='viewer',
        )
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get('/api/campaigns/').status_code, 200)
        self.assertEqual(self.client.post('/api/campaigns/', {'name': 'Denied', 'message': 'No'}, format='json').status_code, 403)

    def test_invalid_invitation_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/auth/invitations/accept/', {
            'token': signing.dumps({'user_id': 999}, salt='wrong'),
            'first_name': 'Invalid', 'password': 'password123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_role_downgrade_removes_staff_write_access(self):
        member = User.objects.create_user(username='staff', email='staff@example.com', role='admin', is_staff=True)
        response = self.client.patch(f'/api/team-members/{member.pk}/', {'role': 'viewer'}, format='json')
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertFalse(member.is_staff)
        self.client.force_authenticate(member)
        self.assertEqual(self.client.post('/api/campaigns/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/whatsapp/conversations/999/', {}, format='json').status_code, 403)

    def test_admin_cannot_modify_owner_or_self(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', role='admin')
        owner = User.objects.create_user(username='other-owner', email='other@example.com', role='owner')
        self.client.force_authenticate(admin)
        for member in (owner, admin):
            url = f'/api/team-members/{member.pk}/'
            self.assertEqual(self.client.patch(url, {'role': 'viewer'}, format='json').status_code, 403)
            self.assertEqual(self.client.delete(url).status_code, 403)

    def test_pending_user_role_can_be_updated_without_activation(self):
        member = User.objects.create_user(username='pending', email='pending@example.com', is_active=False)
        response = self.client.patch(f'/api/team-members/{member.pk}/', {'role': 'editor', 'is_active': True}, format='json')
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.role, 'editor')
        self.assertFalse(member.is_active)

    def test_viewer_cannot_manage_users(self):
        viewer = User.objects.create_user(username='viewer', email='viewer@example.com')
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get('/api/team-members/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/team-members/{self.owner.pk}/', {'role': 'viewer'}, format='json').status_code, 403)

    def test_delete_user_preserves_campaign_and_metrics_and_invalidates_login(self):
        from campaigns.models import Campaign
        from analytics.models import CampaignMetric
        from rest_framework_simplejwt.tokens import RefreshToken
        member = User.objects.create_user(username='delete', email='delete@example.com', password='password123')
        token = str(RefreshToken.for_user(member).access_token)
        campaign = Campaign.objects.create(name='Keep history', message='Hello', created_by=member)
        metric = CampaignMetric.objects.create(campaign=campaign, date='2026-09-08', created_by=member)
        self.assertEqual(self.client.delete(f'/api/team-members/{member.pk}/').status_code, 204)
        self.assertFalse(User.objects.filter(pk=member.pk).exists())
        campaign.refresh_from_db()
        metric.refresh_from_db()
        self.assertIsNone(campaign.created_by_id)
        self.assertIsNone(metric.created_by_id)
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_regional_access_filters_numbers_and_headerless_campaigns(self):
        from whatsapp.models import WhatsAppConfiguration
        from whatsapp.workspace import sync_business_numbers, accessible_business_numbers
        from campaigns.models import Campaign
        for number in ('+918035260741', '+12522501805'):
            WhatsAppConfiguration.objects.create(business_number=number)
        sync_business_numbers()
        numbers = list(accessible_business_numbers(self.owner).order_by('number'))
        for number in numbers:
            Campaign.objects.create(name=number.number, message='Hello', created_by=self.owner, business_number=number)
        for access, prefix in [('india', '+91'), ('us', '+1'), ('both', '+')]:
            self.owner.number_access = access
            self.owner.save()
            response = self.client.get('/api/whatsapp/business-numbers/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), 2 if access == 'both' else 1)
            self.assertTrue(all(item['number'].startswith(prefix) for item in response.data))
            campaigns = self.client.get('/api/campaigns/')
            if access == 'both':
                self.assertEqual(campaigns.status_code, 400)
                continue
            self.assertEqual(campaigns.status_code, 200)
            self.assertEqual(len(campaigns.data['results']), 1)
            self.assertTrue(campaigns.data['results'][0]['name'].startswith(prefix))
            denied = next(n for n in numbers if not n.number.startswith(prefix))
            self.assertEqual(self.client.get('/api/campaigns/', HTTP_X_BUSINESS_NUMBER_ID=str(denied.pk)).status_code, 404)
            self.assertEqual(self.client.get('/api/whatsapp/settings/', {'business_number': denied.number}).status_code, 404)

    def test_restricted_user_without_numbers_cannot_read_legacy_data(self):
        self.owner.number_access = 'india'
        self.owner.save()
        self.assertEqual(self.client.get('/api/campaigns/').status_code, 403)

    def test_number_permission_is_saved_and_returned_at_login(self):
        member = User.objects.create_user(username='regional', email='regional@example.com', password='password123')
        url = f'/api/team-members/{member.pk}/'
        self.assertEqual(self.client.patch(url, {'number_access': 'india'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'number_access': 'invalid'}, format='json').status_code, 400)
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/auth/login/', {'email': member.email, 'password': 'password123'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['number_access'], 'india')

    def test_pending_invitation_can_be_deleted(self):
        member = User.objects.create_user(username='pending-delete', email='pending-delete@example.com', is_active=False)
        self.assertEqual(self.client.delete(f'/api/team-members/{member.pk}/').status_code, 204)
        self.assertFalse(User.objects.filter(pk=member.pk).exists())

    def test_regional_access_applies_to_metric_reads_and_writes(self):
        from whatsapp.models import WhatsAppConfiguration
        from whatsapp.workspace import sync_business_numbers, accessible_business_numbers
        from campaigns.models import Campaign
        from analytics.models import CampaignMetric
        for number in ('+918035260741', '+12522501805'):
            WhatsAppConfiguration.objects.create(business_number=number)
        sync_business_numbers()
        campaigns = {}
        for number in accessible_business_numbers(self.owner):
            campaign = Campaign.objects.create(name=number.number, message='Hello', created_by=self.owner, business_number=number)
            campaigns[number.number[:3]] = campaign
            CampaignMetric.objects.create(campaign=campaign, date='2026-09-08', created_by=self.owner)
        self.owner.number_access = 'india'
        self.owner.save()
        response = self.client.get('/api/analytics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['campaign'] for item in response.data['results']], [campaigns['+91'].pk])
        denied = self.client.post('/api/analytics/create/', {'campaign': campaigns['+12'].pk, 'date': '2026-09-08'}, format='json')
        self.assertEqual(denied.status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False)
class TenantIsolationTests(TestCase):
    def setUp(self):
        from .models import Tenant
        self.tenant_a = Tenant.objects.create(name='Tenant Alpha', slug='tenant-alpha', max_users=2, max_campaigns_monthly=5)
        self.tenant_b = Tenant.objects.create(name='Tenant Beta', slug='tenant-beta', status='suspended')

        self.user_a = User.objects.create_user(
            username='alpha_user', email='alpha@alpha.com', password='password123',
            tenant=self.tenant_a, role='owner', is_staff=True,
        )
        self.user_b = User.objects.create_user(
            username='beta_user', email='beta@beta.com', password='password123',
            tenant=self.tenant_b, role='owner',
        )
        self.superuser = User.objects.create_user(
            username='superadmin', email='super@convernix.com', password='password123',
            is_staff=True, is_superuser=True,
        )
        self.client = APIClient()

    def test_suspended_tenant_cannot_login(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'beta@beta.com', 'password': 'password123',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('suspended', str(response.data))

    def test_suspended_tenant_requests_are_forbidden(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get('/api/tenant/me/')
        self.assertEqual(response.status_code, 403)
        response = self.client.get('/api/team-members/')
        self.assertEqual(response.status_code, 403)

    def test_superuser_with_tenant_override_header(self):
        self.client.force_authenticate(user=self.superuser)
        # Without header, superuser gets platform overview
        resp_all = self.client.get('/api/tenant/me/')
        self.assertEqual(resp_all.status_code, 200)
        self.assertTrue(resp_all.data['is_platform_admin'])
        self.assertIsNone(resp_all.data['tenant'])

        # With X-Tenant-ID header, superuser inspects Tenant Alpha
        resp_scoped = self.client.get('/api/tenant/me/', HTTP_X_TENANT_ID=str(self.tenant_a.pk))
        self.assertEqual(resp_scoped.status_code, 200)
        self.assertFalse(resp_scoped.data['is_platform_admin'])
        self.assertEqual(resp_scoped.data['tenant']['name'], 'Tenant Alpha')

    def test_tenant_user_isolation(self):
        self.client.force_authenticate(user=self.user_a)
        # user_a only sees members of tenant_a
        resp = self.client.get('/api/team-members/')
        self.assertEqual(resp.status_code, 200)
        usernames = [u['username'] for u in resp.data['results']]
        self.assertIn('alpha_user', usernames)
        self.assertNotIn('beta_user', usernames)

    def test_invitation_quota_enforced(self):
        self.client.force_authenticate(user=self.user_a)
        # Create a second user in tenant_a to reach max_users (2)
        User.objects.create_user(
            username='alpha_user_2', email='alpha2@alpha.com', password='password123',
            tenant=self.tenant_a, role='viewer',
        )
        response = self.client.post('/api/iam/invitations/', {
            'email': 'alpha3@alpha.com', 'role': 'viewer', 'team_name': 'Support',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('seat limit', str(response.data))

