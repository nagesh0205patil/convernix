import hashlib
import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.test import APIClient

from users.models import Tenant, TenantMembership, TenantLifecycleHistory
from users.permissions import has_tenant_permission, access_role
from users.tenant_context import resolve_tenant_context
from organization.models import (
    AuditLog,
    CustomRole,
    Feature,
    NotificationTemplate,
    NotificationTemplateVersion,
    OrganizationProfile,
    Permission,
    Plan,
    PlanEntitlement,
    PlanLimit,
    RolePermission,
    SecurityPolicy,
    Subscription,
    SupportAccessRequest,
    SupportAccessSession,
    TenantApiKey,
    TenantIntegration,
    TenantKeyMetadata,
    UsageCounter,
)
from organization.services.api_key_service import ApiKeyService
from organization.services.audit_service import log_admin_action, redact_sensitive_data
from organization.services.crypto_service import (
    derive_tenant_cipher,
    encrypt_tenant_secret,
    decrypt_tenant_secret,
    get_or_create_tenant_key_metadata,
)
from organization.services.entitlement_service import EntitlementService
from organization.services.support_access_service import SupportAccessService
from organization.services.template_engine import SafeTemplateEngine, ALLOWED_VARIABLES
from organization.services.tenant_service import (
    TenantService,
    ensure_canonical_permissions,
    ensure_default_plans_and_features,
    ensure_default_roles_for_tenant,
)
from whatsapp.models import BusinessNumber, Department, WhatsAppConfiguration

User = get_user_model()


class SaaSAdminControlPlaneTests(TestCase):
    """Production-grade test suite verifying the Convernix SaaS & Tenant Administration control plane."""

    def setUp(self):
        # Ensure base plans and canonical permissions are populated
        ensure_canonical_permissions()
        ensure_default_plans_and_features()

        # Provision Tenant A (Primary)
        self.tenant_a, self.owner_a = TenantService.provision_tenant(
            company_name='Alpha Enterprises',
            tier='mid',
            owner_email='owner.a@alpha.test',
            owner_password='AlphaPassword123!',
            owner_first_name='Amit',
            owner_last_name='Sharma',
        )

        # Provision Tenant B (Secondary for cross-tenant tests)
        self.tenant_b, self.owner_b = TenantService.provision_tenant(
            company_name='Beta Corp',
            tier='small',
            owner_email='owner.b@beta.test',
            owner_password='BetaPassword123!',
            owner_first_name='Bhavna',
            owner_last_name='Patel',
        )

        # Platform Superuser (No universal bypass to tenant conversations without elevation)
        self.superuser = User.objects.create_superuser(
            username='platform.admin@cloudtronix.io',
            email='platform.admin@cloudtronix.io',
            password='PlatformMasterPassword123!',
        )

        # Create Client instances
        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.owner_a)

        self.client_b = APIClient()
        self.client_b.force_authenticate(user=self.owner_b)

        self.client_super = APIClient()
        self.client_super.force_authenticate(user=self.superuser)

    # =========================================================================
    # 1. Idempotent Provisioning Saga Tests
    # =========================================================================
    def test_tenant_provisioning_saga_completeness(self):
        """Verify that provisioning creates the complete foundational SaaS architecture."""
        self.assertEqual(self.tenant_a.status, Tenant.LIFECYCLE_ACTIVE)
        self.assertEqual(self.tenant_a.tier, 'mid')

        # 1. Encryption metadata
        key_meta = TenantKeyMetadata.objects.filter(tenant=self.tenant_a).first()
        self.assertIsNotNone(key_meta)
        self.assertEqual(key_meta.key_version, 1)
        self.assertTrue(len(key_meta.salt) >= 32)

        # 2. Organization profile
        profile = OrganizationProfile.objects.filter(tenant=self.tenant_a).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.tenant.name, 'Alpha Enterprises')
        self.assertIn('Alpha Enterprises', profile.legal_business_name)

        # 3. Security Policy
        policy = SecurityPolicy.objects.filter(tenant=self.tenant_a).first()
        self.assertIsNotNone(policy)
        self.assertEqual(policy.password_min_length, 8)

        # 4. Default Department ('Support')
        dept = Department.objects.filter(tenant=self.tenant_a, slug='support').first()
        self.assertIsNotNone(dept)
        self.assertTrue(dept.is_active)

        # 5. Default Roles & Permissions
        owner_role = CustomRole.objects.filter(tenant=self.tenant_a, slug='owner').first()
        self.assertIsNotNone(owner_role)
        self.assertTrue(owner_role.is_system)

        # 6. Owner membership
        membership = TenantMembership.objects.filter(tenant=self.tenant_a, user=self.owner_a).first()
        self.assertIsNotNone(membership)
        self.assertTrue(membership.is_owner)
        self.assertEqual(membership.role, 'owner')

        # 7. Subscription & Usage Counters
        sub = Subscription.objects.filter(tenant=self.tenant_a).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.plan.code, 'professional')

        users_counter = UsageCounter.objects.filter(tenant=self.tenant_a, metric_code='users').first()
        self.assertIsNotNone(users_counter)
        self.assertGreaterEqual(users_counter.current_value, 1)

        # 8. Lifecycle History Audit
        history = TenantLifecycleHistory.objects.filter(tenant=self.tenant_a).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.to_status, Tenant.LIFECYCLE_ACTIVE)

    def test_tenant_provisioning_idempotency(self):
        """Calling provision_tenant again with existing user or organization must be safe and idempotent."""
        tenant_again, owner_again = TenantService.provision_tenant(
            company_name='Alpha Enterprises',
            tier='mid',
            existing_owner_user=self.owner_a,
        )
        self.assertEqual(owner_again.id, self.owner_a.id)
        # Should not crash and memberships remain consistent
        memberships_count = TenantMembership.objects.filter(user=self.owner_a, tenant=tenant_again).count()
        self.assertEqual(memberships_count, 1)

    # =========================================================================
    # 2. Lifecycle State Machine & Concurrency Tests
    # =========================================================================
    def test_valid_lifecycle_transitions(self):
        """Verify permitted lifecycle transitions audit history and update status."""
        # ACTIVE -> SUSPENDED
        TenantService.transition_lifecycle(
            tenant=self.tenant_a,
            target_status=Tenant.LIFECYCLE_SUSPENDED,
            actor=self.superuser,
            reason='Billing past due review',
            expected_version=1,
        )
        self.tenant_a.refresh_from_db()
        self.assertEqual(self.tenant_a.status, Tenant.LIFECYCLE_SUSPENDED)
        self.assertEqual(self.tenant_a.version, 2)
        self.assertIsNotNone(self.tenant_a.suspended_at)

        # SUSPENDED -> ACTIVE
        TenantService.transition_lifecycle(
            tenant=self.tenant_a,
            target_status=Tenant.LIFECYCLE_ACTIVE,
            actor=self.superuser,
            reason='Payment cleared',
            expected_version=2,
        )
        self.tenant_a.refresh_from_db()
        self.assertEqual(self.tenant_a.status, Tenant.LIFECYCLE_ACTIVE)
        self.assertEqual(self.tenant_a.version, 3)
        self.assertIsNone(self.tenant_a.suspended_at)

    def test_invalid_lifecycle_transition_rejected(self):
        """Illegal state transitions must raise ValidationError."""
        with self.assertRaises(ValidationError):
            # Cannot jump directly from ACTIVE to PROVISIONING
            TenantService.transition_lifecycle(
                tenant=self.tenant_a,
                target_status=Tenant.LIFECYCLE_PROVISIONING,
                actor=self.superuser,
            )

    def test_optimistic_concurrency_conflict_rejected(self):
        """Out-of-order state transitions with mismatched expected_version must raise conflict."""
        with self.assertRaises(ValidationError) as ctx:
            TenantService.transition_lifecycle(
                tenant=self.tenant_a,
                target_status=Tenant.LIFECYCLE_SUSPENDED,
                actor=self.superuser,
                expected_version=999,  # Mismatched version
            )
        self.assertIn('Conflict', str(ctx.exception))

    def test_suspension_deactivates_api_keys(self):
        """Suspending a tenant must automatically propagate to revoke active API keys."""
        key_inst, raw_key = ApiKeyService.generate_api_key(
            tenant=self.tenant_a,
            name='Ingestion Key',
            scopes=['*'],
            created_by=self.owner_a,
        )
        self.assertTrue(key_inst.is_active)

        # Suspend tenant
        TenantService.transition_lifecycle(
            tenant=self.tenant_a,
            target_status=Tenant.LIFECYCLE_SUSPENDED,
            actor=self.superuser,
            reason='Security hold',
        )

        key_inst.refresh_from_db()
        self.assertFalse(key_inst.is_active)

        # Validating key while suspended must return None
        validated = ApiKeyService.validate_api_key(raw_key)
        self.assertIsNone(validated)

    # =========================================================================
    # 3. Multi-Tenant Strict Isolation Tests
    # =========================================================================
    def test_cross_tenant_isolation_departments(self):
        """Tenant A cannot see or modify Tenant B's departments."""
        # Create department in Tenant B
        dept_b = Department.objects.create(
            tenant=self.tenant_b,
            name='Beta Escalations',
            slug='beta-escalations',
            is_active=True,
        )

        # Tenant A lists departments
        res = self.client_a.get('/api/admin/departments/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        dept_names = [d['name'] for d in res.data['departments']]
        self.assertNotIn('Beta Escalations', dept_names)

        # Tenant A attempts to read Tenant B's department by ID
        res_detail = self.client_a.get(f'/api/admin/departments/{dept_b.id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Tenant A attempts to delete Tenant B's department
        res_del = self.client_a.delete(f'/api/admin/departments/{dept_b.id}/')
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)
        dept_b.refresh_from_db()
        self.assertFalse(dept_b.is_archived)

    def test_cross_tenant_isolation_templates(self):
        """Tenant A cannot see, publish, or rollback Tenant B's notification templates."""
        tmpl_b = NotificationTemplate.objects.create(
            tenant=self.tenant_b,
            name='Beta Confidential Template',
            event_type='lead.created',
            channel='WHATSAPP',
            status='published',
            current_version=1,
        )

        # Tenant A lists templates
        res = self.client_a.get('/api/admin/templates/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tmpl_ids = [t['id'] for t in res.data['templates']]
        self.assertNotIn(tmpl_b.id, tmpl_ids)

        # Tenant A attempts to publish or preview Tenant B's template
        res_pub = self.client_a.post(f'/api/admin/templates/{tmpl_b.id}/publish/', {'change_summary': 'Hack'})
        self.assertEqual(res_pub.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_isolation_api_keys(self):
        """Tenant A cannot view or revoke Tenant B's API keys."""
        key_b, _ = ApiKeyService.generate_api_key(
            tenant=self.tenant_b,
            name='Beta Secret Key',
            scopes=['*'],
            created_by=self.owner_b,
        )

        # Tenant A lists API keys
        res = self.client_a.get('/api/admin/api-keys/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        key_ids = [k['id'] for k in res.data['api_keys']]
        self.assertNotIn(key_b.id, key_ids)

        # Tenant A attempts to delete Tenant B's key
        res_del = self.client_a.delete(f'/api/admin/api-keys/{key_b.id}/')
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)
        key_b.refresh_from_db()
        self.assertTrue(key_b.is_active)

    # =========================================================================
    # 4. RBAC & Privilege Escalation Prevention Tests
    # =========================================================================
    def test_last_owner_cannot_be_deactivated_or_demoted(self):
        """Protecting the last active Owner of any tenant from accidental deletion or role alteration."""
        # Attempt to demote the sole owner to agent
        res_demote = self.client_a.patch(f'/api/admin/users/{self.owner_a.id}/', {'role': 'agent'})
        # Cannot alter own role or last owner role
        self.assertIn(res_demote.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

        # Attempt to deactivate the sole owner
        res_deact = self.client_a.delete(f'/api/admin/users/{self.owner_a.id}/')
        self.assertEqual(res_deact.status_code, status.HTTP_403_FORBIDDEN)
        self.owner_a.refresh_from_db()
        self.assertTrue(self.owner_a.is_active)
        self.assertEqual(self.owner_a.role, 'owner')

    def test_custom_role_privilege_escalation_prevention(self):
        """Non-owner users cannot create custom roles containing permissions they do not possess."""
        # Create an Agent user in Tenant A
        agent_user = User.objects.create_user(
            username='agent@alpha.test',
            email='agent@alpha.test',
            password='AgentPassword123!',
            role='agent',
            tenant=self.tenant_a,
            is_active=True,
        )
        TenantMembership.objects.create(user=agent_user, tenant=self.tenant_a, role='agent', status='active')

        client_agent = APIClient()
        client_agent.force_authenticate(user=agent_user)

        # Agent attempts to create custom role with 'security.manage' and 'subscription.manage'
        res = client_agent.post('/api/admin/roles/', {
            'name': 'Super Escalate Role',
            'permissions': {'subscription.manage': True, 'security.manage': True},
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 5. Entitlement & Capacity Limit Enforcement Tests
    # =========================================================================
    def test_entitlement_service_feature_check(self):
        """Verify centralized can_use_feature respects subscription plans."""
        # Mid tier (Professional) has CRM, INBOX, CAMPAIGNS, AUTOMATION
        self.assertTrue(EntitlementService.can_use_feature(self.tenant_a, 'INBOX'))
        self.assertTrue(EntitlementService.can_use_feature(self.tenant_a, 'CAMPAIGNS'))
        # Starter tier does NOT have CAMPAIGNS or ADVANCED_SECURITY
        self.assertFalse(EntitlementService.can_use_feature(self.tenant_b, 'ADVANCED_SECURITY'))

    def test_usage_limit_enforcement_blocks_creation(self):
        """When plan capacity limit is reached, enforce_limit raises ValidationError."""
        # Set tenant B user limit
        sub = EntitlementService.get_tenant_subscription(self.tenant_b)
        PlanLimit.objects.filter(plan=sub.plan, metric_code='users').update(max_value=1)
        UsageCounter.objects.filter(tenant=self.tenant_b, metric_code='users').update(current_value=1)

        # Try to invite another user when current is 1 and limit is 1
        with self.assertRaises(ValidationError) as ctx:
            EntitlementService.enforce_limit(self.tenant_b, 'users', quantity=1)
        self.assertIn('USAGE_LIMIT_REACHED', str(ctx.exception))

    # =========================================================================
    # 6. Safe Template Engine Tests
    # =========================================================================
    def test_safe_template_engine_allowlist_validation(self):
        """SafeTemplateEngine rejects unallowlisted variables and code execution injections."""
        valid_template = 'Hello {{lead.name}}, your appointment with {{agent.name}} is confirmed.'
        is_valid, unknown = SafeTemplateEngine.validate_content(valid_template)
        self.assertTrue(is_valid)
        self.assertEqual(len(unknown), 0)

        # Unsafe / Unknown variable injection
        unsafe_template = 'System secret: {{process.env.SECRET_KEY}} or {{__import__("os").system("id")}}'
        is_valid_unsafe, unknown_unsafe = SafeTemplateEngine.validate_content(unsafe_template)
        self.assertFalse(is_valid_unsafe)
        self.assertIn('process.env.SECRET_KEY', unknown_unsafe)

    def test_safe_template_engine_synthetic_rendering(self):
        """SafeTemplateEngine produces realistic preview with synthetic fallbacks without executing code."""
        content = 'Welcome {{lead.name}} from {{organization.name}}!'
        rendered = SafeTemplateEngine.generate_preview(content)
        self.assertIn('Rahul Sharma', rendered)
        self.assertNotIn('{{lead.name}}', rendered)

    # =========================================================================
    # 7. Cryptographic API Key Lifecycle Tests
    # =========================================================================
    def test_api_key_generation_hashing_and_revocation(self):
        """API key is generated with cvx_live_ prefix, hashed with SHA-256, and validated."""
        key_inst, raw_key = ApiKeyService.generate_api_key(
            tenant=self.tenant_a,
            name='Zapier CRM Key',
            scopes=['leads.read', 'leads.write'],
            created_by=self.owner_a,
            expires_in_days=30,
        )

        self.assertTrue(raw_key.startswith('cvx_live_'))
        # Key in DB must be a SHA-256 hash, NOT raw plaintext
        self.assertNotEqual(key_inst.key_hash, raw_key)
        self.assertEqual(key_inst.key_hash, hashlib.sha256(raw_key.encode('utf-8')).hexdigest())

        # Validate key
        validated = ApiKeyService.validate_api_key(raw_key, required_scope='leads.read')
        self.assertIsNotNone(validated)
        self.assertEqual(validated.id, key_inst.id)
        self.assertIsNotNone(validated.last_used_at)

        # Validate with unauthorized scope
        denied_scope = ApiKeyService.validate_api_key(raw_key, required_scope='admin.super')
        self.assertIsNone(denied_scope)

        # Revoke key
        ApiKeyService.revoke_api_key(key_inst, revoked_by=self.owner_a)
        key_inst.refresh_from_db()
        self.assertFalse(key_inst.is_active)
        self.assertIsNotNone(key_inst.revoked_at)

        # Validating revoked key returns None
        self.assertIsNone(ApiKeyService.validate_api_key(raw_key))

    # =========================================================================
    # 8. Controlled Platform Support Access Elevation Tests
    # =========================================================================
    def test_no_universal_super_admin_bypass(self):
        """Platform superuser has NO automatic access to tenant customer data/departments without active support session."""
        # Request context resolution for superuser with arbitrary X-Tenant-ID
        class DummyRequest:
            user = self.superuser
            headers = {'X-Tenant-ID': str(self.tenant_a.id)}
            META = {}

        # Tenant context resolver must NOT trust superuser arbitrary header without an active support session
        ctx = resolve_tenant_context(DummyRequest())
        self.assertFalse(ctx.is_elevated_support)
        self.assertEqual(len(ctx.support_scopes), 0)

    def test_support_access_elevation_workflow(self):
        """Time-limited, scoped support access elevation request, approval, and session execution."""
        # 1. Platform staff requests access
        req = SupportAccessService.request_access(
            platform_user=self.superuser,
            tenant=self.tenant_a,
            reason='Investigating webhook timeout on production number',
            ticket_reference='SUP-1094',
            requested_scopes=['support.read', 'support.diagnostics'],
            duration_minutes=60,
        )
        self.assertEqual(req.status, 'approved')
        self.assertEqual(req.ticket_reference, 'SUP-1094')

        # 2. Staff starts elevated support session
        session, raw_token = SupportAccessService.start_session(req)
        self.assertTrue(session.is_active)
        self.assertTrue(raw_token.startswith('cvx_sup_'))

        # 3. Active session verification
        verified = SupportAccessService.verify_active_support_session(self.superuser, self.tenant_a)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, session.id)

        # 4. Terminate support session
        SupportAccessService.end_session(session)
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.ended_at)

        # Now verification returns None
        self.assertIsNone(SupportAccessService.verify_active_support_session(self.superuser, self.tenant_a))

    # =========================================================================
    # 9. Secret Encryption At Rest & Masking Tests
    # =========================================================================
    def test_secret_encryption_at_rest_and_decryption(self):
        """Secrets are encrypted using Fernet + HKDF derived key and decrypted cleanly."""
        raw_meta_token = 'EAAG...MetaAccessTokenSecret12345'
        encrypted = encrypt_tenant_secret(self.tenant_a, raw_meta_token)

        # Must not be plaintext
        self.assertNotEqual(encrypted, raw_meta_token)
        self.assertTrue(len(encrypted) > 40)

        # Decrypt must recover exact secret
        decrypted = decrypt_tenant_secret(self.tenant_a, encrypted)
        self.assertEqual(decrypted, raw_meta_token)

        # Tenant B cipher cannot decrypt Tenant A's ciphertext
        decrypted_b = decrypt_tenant_secret(self.tenant_b, encrypted)
        self.assertNotEqual(decrypted_b, raw_meta_token)

    def test_get_responses_mask_secrets(self):
        """GET endpoints for WhatsApp and Integrations never expose raw secrets in responses."""
        WhatsAppConfiguration.objects.create(
            tenant=self.tenant_a,
            business_number='+919876543210',
            meta_access_token=encrypt_tenant_secret(self.tenant_a, 'EAAGsecretToken'),
            webhook_secret=encrypt_tenant_secret(self.tenant_a, 'appSecret9988'),
        )
        BusinessNumber.objects.create(
            tenant=self.tenant_a,
            number='+919876543210',
            label='Primary Line',
            is_active=True,
        )

        res = self.client_a.get('/api/admin/whatsapp/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Verify secrets are NOT in response
        self.assertNotIn('meta_access_token', res.data)
        self.assertNotIn('EAAGsecretToken', str(res.data))
        self.assertTrue(res.data['has_access_token'])

    def test_audit_logs_redact_sensitive_payloads(self):
        """Audit logging globally redacts tokens, passwords, and API keys."""
        dirty_payload = {
            'username': 'john.doe',
            'password': 'SuperSecretPassword!',
            'meta_access_token': 'EAAG1234567890',
            'api_key': 'cvx_live_abcdef123456',
            'safe_metadata': 'Normal non-sensitive data',
        }
        redacted = redact_sensitive_data(dirty_payload)
        self.assertEqual(redacted['password'], '[REDACTED]')
        self.assertEqual(redacted['meta_access_token'], '[REDACTED]')
        self.assertEqual(redacted['api_key'], '[REDACTED]')
        self.assertEqual(redacted['safe_metadata'], 'Normal non-sensitive data')
