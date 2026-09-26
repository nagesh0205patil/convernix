import logging
import re
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from users.models import Tenant, TenantMembership, TenantLifecycleHistory
from organization.models import (
    OrganizationProfile,
    CustomRole,
    Permission,
    RolePermission,
    Plan,
    Feature,
    PlanEntitlement,
    PlanLimit,
    Subscription,
    UsageCounter,
    SecurityPolicy,
    TenantKeyMetadata,
)
from organization.services.audit_service import log_admin_action
from organization.services.crypto_service import get_or_create_tenant_key_metadata
from organization.services.event_service import publish_domain_event

logger = logging.getLogger(__name__)
User = get_user_model()

CANONICAL_PERMISSIONS = [
    # Settings & Organization
    ('tenant.settings.read', 'Settings', 'View organization profile and settings'),
    ('tenant.settings.update', 'Settings', 'Modify organization profile and settings'),
    # Users & IAM
    ('users.read', 'IAM', 'View team members and invitations'),
    ('users.invite', 'IAM', 'Invite new users to organization'),
    ('users.update', 'IAM', 'Edit user roles, profiles, and teams'),
    ('users.disable', 'IAM', 'Suspend or disable users'),
    ('roles.read', 'IAM', 'View system and custom roles'),
    ('roles.create', 'IAM', 'Create custom roles'),
    ('roles.update', 'IAM', 'Modify custom roles and permission mappings'),
    ('roles.delete', 'IAM', 'Delete custom roles'),
    ('departments.read', 'Departments', 'View departments and member rosters'),
    ('departments.create', 'Departments', 'Create new organization departments'),
    ('departments.update', 'Departments', 'Edit or archive departments'),
    # WhatsApp
    ('whatsapp.read', 'WhatsApp', 'View WhatsApp numbers and connection state'),
    ('whatsapp.configure', 'WhatsApp', 'Manage WhatsApp Meta credentials and numbers'),
    # Templates
    ('templates.read', 'Templates', 'View notification templates and versions'),
    ('templates.create', 'Templates', 'Create draft notification templates'),
    ('templates.update', 'Templates', 'Edit notification templates and draft versions'),
    ('templates.publish', 'Templates', 'Publish and activate template versions'),
    # Billing & Subscription
    ('billing.read', 'Billing', 'View billing details, cards, and tax invoices'),
    ('billing.manage', 'Billing', 'Update payment methods and billing profile'),
    ('subscription.read', 'Subscription', 'View current plan and entitlements'),
    ('subscription.manage', 'Subscription', 'Upgrade, downgrade, or cancel subscription'),
    ('usage.read', 'Usage', 'View metered capacity and usage metrics'),
    # Integrations
    ('integrations.read', 'Integrations', 'View connected webhooks and CRMs'),
    ('integrations.manage', 'Integrations', 'Configure third-party integrations and webhooks'),
    # Security & Audit
    ('security.read', 'Security', 'View security policies, sessions, and events'),
    ('security.manage', 'Security', 'Update MFA, password policy, and API keys'),
    ('audit.read', 'Audit', 'View immutable administrative audit logs'),
    ('audit.export', 'Audit', 'Export forensic audit logs to CSV'),
]

DEFAULT_METRIC_CODES = [
    'users',
    'departments',
    'whatsapp_numbers',
    'monthly_messages',
    'monthly_conversations',
    'campaign_contacts',
    'automation_executions',
    'storage',
    'api_requests',
    'webhook_deliveries',
]


def ensure_canonical_permissions():
    """Ensure all canonical permissions exist in the database."""
    for code, module, desc in CANONICAL_PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={'module': module, 'description': desc}
        )


def ensure_default_roles_for_tenant(tenant):
    """Ensure system roles and their permission mappings exist for this tenant."""
    ensure_canonical_permissions()
    all_perms = list(Permission.objects.all())

    role_matrix = {
        'owner': {
            'name': 'Owner',
            'desc': 'Complete authority over organization, billing, IAM, and security.',
            'perms': [p.code for p in all_perms],
        },
        'admin': {
            'name': 'Administrator',
            'desc': 'Manage operations, users, departments, WhatsApp, and workflows.',
            'perms': [p.code for p in all_perms if not p.code.startswith('subscription.manage')],
        },
        'manager': {
            'name': 'Manager',
            'desc': 'Manage team routing, campaigns, departments, and support operations.',
            'perms': [
                'tenant.settings.read', 'users.read', 'departments.read', 'departments.create', 'departments.update',
                'whatsapp.read', 'templates.read', 'templates.create', 'templates.update', 'templates.publish',
                'usage.read', 'audit.read',
            ],
        },
        'agent': {
            'name': 'Agent',
            'desc': 'Frontline WhatsApp conversations and enquiry routing.',
            'perms': [
                'tenant.settings.read', 'departments.read', 'whatsapp.read', 'templates.read',
            ],
        },
        'billing_admin': {
            'name': 'Billing Administrator',
            'desc': 'Manage subscription, invoices, payment methods, and tax details.',
            'perms': [
                'tenant.settings.read', 'billing.read', 'billing.manage', 'subscription.read',
                'subscription.manage', 'usage.read', 'audit.read',
            ],
        },
        'read_only': {
            'name': 'Read Only',
            'desc': 'Audit, compliance, and reporting observer view.',
            'perms': [
                'tenant.settings.read', 'users.read', 'roles.read', 'departments.read',
                'whatsapp.read', 'templates.read', 'billing.read', 'subscription.read',
                'usage.read', 'integrations.read', 'security.read', 'audit.read',
            ],
        },
    }

    for slug, conf in role_matrix.items():
        role, _ = CustomRole.objects.get_or_create(
            tenant=tenant,
            slug=slug,
            defaults={
                'name': conf['name'],
                'description': conf['desc'],
                'is_system': True,
                'permissions': {p: True for p in conf['perms']},
            }
        )
        for code in conf['perms']:
            perm = Permission.objects.filter(code=code).first()
            if perm:
                RolePermission.objects.get_or_create(role=role, permission=perm)


def ensure_default_plans_and_features():
    """Seed baseline catalog plans and features if missing."""
    features = [
        ('INBOX', 'WhatsApp Shared Inbox'),
        ('CRM', 'Contact & Customer CRM'),
        ('CAMPAIGNS', 'Broadcast Messaging Campaigns'),
        ('AUTOMATION', 'Workflow Automation Rules'),
        ('SUPPORT', 'Multi-Department Ticketing'),
        ('ANALYTICS', 'Analytics & Reporting Dashboard'),
        ('API_ACCESS', 'REST API Access & Keys'),
        ('WEBHOOKS', 'Real-Time Webhooks'),
        ('CUSTOM_ROLES', 'Granular Custom RBAC Roles'),
        ('AUDIT_EXPORT', 'Forensic Audit Log CSV Export'),
        ('ADVANCED_SECURITY', 'Enforced MFA & IP Allowlists'),
        ('CUSTOM_INTEGRATIONS', 'Third-Party CRM Integrations'),
    ]
    for code, name in features:
        Feature.objects.get_or_create(code=code, defaults={'name': name})

    plans_def = [
        ('starter', 'Starter Plan', 'small', 2499.00, [
            'INBOX', 'CRM', 'SUPPORT'
        ], {
            'users': 3,
            'departments': 2,
            'whatsapp_numbers': 1,
            'monthly_messages': 5000,
            'monthly_conversations': 1000,
            'campaign_contacts': 500,
            'automation_executions': 1000,
            'api_requests': 5000,
        }),
        ('professional', 'Professional Plan', 'mid', 6999.00, [
            'INBOX', 'CRM', 'CAMPAIGNS', 'AUTOMATION', 'SUPPORT', 'ANALYTICS',
            'API_ACCESS', 'WEBHOOKS', 'AUDIT_EXPORT',
        ], {
            'users': 15,
            'departments': 5,
            'whatsapp_numbers': 3,
            'monthly_messages': 25000,
            'monthly_conversations': 5000,
            'campaign_contacts': 5000,
            'automation_executions': 10000,
            'api_requests': 50000,
        }),
        ('enterprise', 'Enterprise Plan', 'large', 19999.00, [
            'INBOX', 'CRM', 'CAMPAIGNS', 'AUTOMATION', 'SUPPORT', 'ANALYTICS',
            'API_ACCESS', 'WEBHOOKS', 'CUSTOM_ROLES', 'AUDIT_EXPORT',
            'ADVANCED_SECURITY', 'CUSTOM_INTEGRATIONS',
        ], {
            'users': 100,
            'departments': 25,
            'whatsapp_numbers': 10,
            'monthly_messages': 150000,
            'monthly_conversations': 30000,
            'campaign_contacts': 50000,
            'automation_executions': 100000,
            'api_requests': 500000,
        }),
    ]

    for p_code, p_name, p_tier, p_price, p_feats, p_limits in plans_def:
        plan, _ = Plan.objects.get_or_create(
            code=p_code,
            defaults={
                'name': p_name,
                'tier': p_tier,
                'price_inr': p_price,
                'billing_interval': 'monthly',
                'is_active': True,
            }
        )
        for f_code in p_feats:
            f = Feature.objects.filter(code=f_code).first()
            if f:
                PlanEntitlement.objects.get_or_create(plan=plan, feature=f, defaults={'is_enabled': True})
        for m_code, max_val in p_limits.items():
            PlanLimit.objects.get_or_create(plan=plan, metric_code=m_code, defaults={'max_value': max_val})


class TenantService:
    """Enterprise Tenant Lifecycle and Provisioning Saga Orchestrator."""

    @classmethod
    @transaction.atomic
    def provision_tenant(
        cls,
        company_name: str,
        tier: str = 'small',
        owner_email: str = '',
        owner_password: Optional[str] = None,
        owner_first_name: str = '',
        owner_last_name: str = '',
        owner_phone: str = '',
        existing_owner_user: Optional[Any] = None,
        actor: Optional[Any] = None,
    ) -> Tuple[Tenant, Any]:
        """Idempotently provisions a tenant workspace with all required foundational models."""
        ensure_default_plans_and_features()

        slug_base = re.sub(r'[^a-z0-9]+', '-', company_name.lower()).strip('-') or 'org'
        slug = slug_base
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f'{slug_base}-{counter}'
            counter += 1

        tenant, created = Tenant.objects.get_or_create(
            slug=slug,
            defaults={
                'name': company_name,
                'tier': tier,
                'status': Tenant.LIFECYCLE_ACTIVE,
                'version': 1,
            }
        )
        tenant.apply_tier_defaults()
        tenant.save()

        # 1. Tenant Key Metadata for encryption
        get_or_create_tenant_key_metadata(tenant)

        # 2. Organization Profile
        OrganizationProfile.get_or_create_for_tenant(tenant)

        # 3. Security Policy
        SecurityPolicy.objects.get_or_create(
            tenant=tenant,
            defaults={
                'mfa_required': False,
                'password_min_length': 8,
                'password_require_special': True,
                'session_duration_minutes': 480,
            }
        )

        # 4. Default Department ('Support')
        from whatsapp.models import Department
        Department.objects.get_or_create(
            tenant=tenant,
            name='Support',
            defaults={'slug': 'support', 'is_active': True, 'description': 'Main Support Department'}
        )

        # 5. Default Roles and Permissions
        ensure_default_roles_for_tenant(tenant)

        # 6. Owner user and membership
        if existing_owner_user:
            owner_user = existing_owner_user
            if not owner_user.tenant:
                owner_user.tenant = tenant
                owner_user.save()
        else:
            owner_email = owner_email.strip().lower()
            owner_user = User.objects.filter(email=owner_email).first()
            if not owner_user:
                owner_user = User.objects.create_user(
                    username=owner_email,
                    email=owner_email,
                    password=owner_password or User.objects.make_random_password(14),
                    first_name=owner_first_name,
                    last_name=owner_last_name,
                    phone_number=owner_phone,
                    role='owner',
                    is_staff=True,
                    tenant=tenant,
                    organization=company_name,
                    team_name='Support',
                )
            else:
                if not owner_user.tenant:
                    owner_user.tenant = tenant
                    owner_user.save()

        TenantMembership.objects.get_or_create(
            user=owner_user,
            tenant=tenant,
            defaults={'role': 'owner', 'status': 'active', 'is_owner': True}
        )

        # 7. Subscription & Usage Counters
        plan_code = 'professional' if tier == 'mid' else ('enterprise' if tier == 'large' else 'starter')
        plan = Plan.objects.filter(code=plan_code).first() or Plan.objects.first()

        now = timezone.now()
        period_end = now + timedelta(days=30)

        if plan:
            Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'plan': plan,
                    'status': 'active',
                    'current_period_start': now,
                    'current_period_end': period_end,
                }
            )

        for metric in DEFAULT_METRIC_CODES:
            UsageCounter.objects.get_or_create(
                tenant=tenant,
                metric_code=metric,
                period_start=now,
                defaults={
                    'current_value': 1 if metric == 'users' else (1 if metric == 'departments' else 0),
                    'period_end': period_end,
                }
            )

        # 8. Audit Record & Lifecycle History
        TenantLifecycleHistory.objects.create(
            tenant=tenant,
            from_status=Tenant.LIFECYCLE_PENDING,
            to_status=tenant.status,
            reason='Initial tenant provisioning',
            actor=actor or owner_user,
            actor_email=(actor or owner_user).email if (actor or owner_user) else '',
        )

        log_admin_action(
            tenant=tenant,
            actor_name=owner_user.get_full_name() or owner_user.email,
            actor_email=owner_user.email,
            action='Tenant provisioned successfully',
            module='Tenant',
            resource=f'{tenant.name} ({tenant.slug})',
            status='Success',
            metadata={'tier': tenant.tier, 'plan': plan.code if plan else 'default'},
        )

        publish_domain_event(
            event_type='tenant.provisioned',
            tenant_id=tenant.id,
            data={'name': tenant.name, 'slug': tenant.slug, 'tier': tenant.tier, 'owner': owner_user.email},
        )

        return tenant, owner_user

    @classmethod
    @transaction.atomic
    def transition_lifecycle(
        cls,
        tenant: Tenant,
        target_status: str,
        actor: Optional[Any] = None,
        reason: str = '',
        expected_version: Optional[int] = None,
    ) -> Tenant:
        """Validates and applies a lifecycle state transition with optimistic concurrency check."""
        target = target_status.upper()
        current = tenant.status.upper()

        if expected_version is not None and tenant.version != expected_version:
            raise ValidationError({'version': 'Conflict: Tenant has been modified by another concurrent request.'})

        if current == target:
            return tenant

        if not tenant.can_transition_to(target):
            raise ValidationError({
                'status': f'Illegal state transition from {current} to {target}. Permitted targets: {list(tenant.PERMITTED_TRANSITIONS.get(tenant.status, []))}'
            })

        old_status = tenant.status
        tenant.status = target
        tenant.version += 1

        if target == Tenant.LIFECYCLE_SUSPENDED:
            tenant.suspended_at = timezone.now()
            tenant.suspension_reason = reason
        elif target == Tenant.LIFECYCLE_ACTIVE:
            tenant.suspended_at = None
            tenant.suspension_reason = ''
        elif target == Tenant.LIFECYCLE_DELETION_PENDING:
            tenant.deletion_requested_at = timezone.now()

        tenant.save()

        # Audit and History
        TenantLifecycleHistory.objects.create(
            tenant=tenant,
            from_status=old_status,
            to_status=target,
            reason=reason,
            actor=actor,
            actor_email=actor.email if actor else '',
        )

        log_admin_action(
            tenant=tenant,
            actor_name=actor.get_full_name() or actor.email if actor else 'System',
            actor_email=actor.email if actor else '',
            action=f'Transitioned lifecycle to {target}',
            module='Tenant',
            resource=tenant.name,
            status='Success',
            metadata={'from_status': old_status, 'to_status': target, 'reason': reason},
        )

        # Propagate suspension / activation
        if target == Tenant.LIFECYCLE_SUSPENDED:
            cls.propagate_suspension(tenant, reason)
        elif target == Tenant.LIFECYCLE_ACTIVE:
            cls.propagate_reactivation(tenant)

        publish_domain_event(
            event_type=f'tenant.{target.lower()}',
            tenant_id=tenant.id,
            data={'from_status': old_status, 'to_status': target, 'reason': reason},
        )

        return tenant

    @classmethod
    def propagate_suspension(cls, tenant: Tenant, reason: str):
        """Disables active outbound actions, campaigns, API keys, and webhooks."""
        from organization.models import TenantApiKey
        TenantApiKey.objects.filter(tenant=tenant).update(is_active=False)
        logger.warning('Propagated suspension for tenant %s: %s', tenant.slug, reason)

    @classmethod
    def propagate_reactivation(cls, tenant: Tenant):
        """Re-enables tenant operational state."""
        logger.info('Propagated reactivation for tenant %s', tenant.slug)

