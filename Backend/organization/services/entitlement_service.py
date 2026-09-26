import logging
from typing import Tuple
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from users.models import Tenant
from organization.models import PlanEntitlement, PlanLimit, Subscription, UsageCounter

logger = logging.getLogger(__name__)


class EntitlementService:
    """Centralized feature entitlement and capacity limit evaluation engine."""

    @classmethod
    def get_tenant_subscription(cls, tenant: Tenant) -> Subscription:
        sub = Subscription.objects.filter(tenant=tenant).select_related('plan').first()
        if not sub:
            # Lazy provision baseline subscription if missing
            from organization.models import Plan
            plan = Plan.objects.filter(code='starter').first() or Plan.objects.first()
            if plan:
                sub = Subscription.objects.create(
                    tenant=tenant,
                    plan=plan,
                    status='active',
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timezone.timedelta(days=30),
                )
        return sub

    @classmethod
    def can_use_feature(cls, tenant: Tenant, feature_code: str) -> bool:
        """Determines if a tenant is entitled to use a specific feature module."""
        if not tenant:
            return False

        # Suspended tenants have restricted feature access
        if tenant.status.upper() in (Tenant.LIFECYCLE_SUSPENDED, 'SUSPENDED', Tenant.LIFECYCLE_DELETED):
            return False

        sub = cls.get_tenant_subscription(tenant)
        if not sub or not sub.plan:
            return False

        entitlement = PlanEntitlement.objects.filter(
            plan=sub.plan,
            feature__code=feature_code,
        ).first()

        if entitlement:
            return entitlement.is_enabled

        # Baseline fallback for essential core modules
        if feature_code in ('INBOX', 'CRM', 'SUPPORT'):
            return True

        return False

    @classmethod
    def check_limit(cls, tenant: Tenant, metric_code: str, quantity: int = 1) -> Tuple[bool, int, int]:
        """Evaluates whether consuming quantity units of metric_code remains within plan capacity.

        Returns (is_allowed, current_usage, limit_max). limit_max == 0 indicates unlimited.
        """
        if not tenant:
            return False, 0, 0

        sub = cls.get_tenant_subscription(tenant)
        if not sub or not sub.plan:
            # Fallback to tenant model limits
            if metric_code == 'users':
                limit = tenant.max_users
            elif metric_code == 'whatsapp_numbers':
                limit = tenant.max_numbers
            elif metric_code == 'campaign_contacts':
                limit = tenant.max_campaigns_monthly * 500
            else:
                limit = 1000
        else:
            plan_limit = PlanLimit.objects.filter(plan=sub.plan, metric_code=metric_code).first()
            if plan_limit:
                limit = plan_limit.max_value
            else:
                # Defaults based on tier
                if metric_code == 'users':
                    limit = tenant.max_users
                elif metric_code == 'whatsapp_numbers':
                    limit = tenant.max_numbers
                else:
                    limit = 0  # 0 = unlimited

        # Current counter
        counter = UsageCounter.objects.filter(tenant=tenant, metric_code=metric_code).order_by('-period_start').first()
        current_val = counter.current_value if counter else 0

        if limit == 0:
            # Unlimited
            return True, current_val, limit

        if current_val + quantity > limit:
            return False, current_val, limit

        return True, current_val, limit

    @classmethod
    def enforce_limit(cls, tenant: Tenant, metric_code: str, quantity: int = 1):
        """Authoritatively enforces capacity limit; raises ValidationError if exceeded."""
        is_allowed, current, limit = cls.check_limit(tenant, metric_code, quantity)
        if not is_allowed:
            raise ValidationError({
                'error_code': 'USAGE_LIMIT_REACHED',
                'detail': f'Your plan limit for {metric_code.replace("_", " ")} ({limit}) has been reached (current: {current}). Please upgrade your subscription.',
                'metric': metric_code,
                'current': current,
                'limit': limit,
            })

