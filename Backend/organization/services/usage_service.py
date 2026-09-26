import logging
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional
from django.db import transaction
from django.utils import timezone
from users.models import Tenant
from organization.models import UsageCounter, UsageEvent
from organization.services.entitlement_service import EntitlementService
from organization.services.event_service import publish_domain_event

logger = logging.getLogger(__name__)


class UsageService:
    """Enterprise metered usage ingestion and quota threshold monitor."""

    @classmethod
    @transaction.atomic
    def record_usage_event(
        cls,
        tenant: Tenant,
        metric_code: str,
        quantity: int = 1,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        """Idempotently records consumption of a metered metric."""
        if not idempotency_key:
            idempotency_key = f'evt_{uuid.uuid4().hex[:16]}'

        # Idempotency check: if event with this key already recorded for this tenant, return it
        existing = UsageEvent.objects.filter(tenant=tenant, idempotency_key=idempotency_key).first()
        if existing:
            return existing

        now = timezone.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1)

        counter, _ = UsageCounter.objects.get_or_create(
            tenant=tenant,
            metric_code=metric_code,
            period_start=period_start,
            defaults={'period_end': period_end, 'current_value': 0}
        )
        counter.current_value += quantity
        counter.save()

        event = UsageEvent.objects.create(
            event_id=f'UEVT-{uuid.uuid4().hex[:12].upper()}',
            tenant=tenant,
            metric_code=metric_code,
            quantity=quantity,
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            timestamp=now,
        )

        # Check threshold percentages (80%, 90%, 100%)
        cls._evaluate_thresholds(tenant, metric_code, counter.current_value)

        return event

    @classmethod
    def _evaluate_thresholds(cls, tenant: Tenant, metric_code: str, current_value: int):
        is_allowed, _, limit = EntitlementService.check_limit(tenant, metric_code, quantity=0)
        if limit and limit > 0:
            pct = (current_value / limit) * 100.0
            if pct >= 100:
                publish_domain_event(
                    event_type='usage.limit_reached',
                    tenant_id=tenant.id,
                    data={'metric': metric_code, 'current': current_value, 'limit': limit, 'percentage': pct}
                )
            elif pct >= 80:
                publish_domain_event(
                    event_type='usage.threshold_reached',
                    tenant_id=tenant.id,
                    data={'metric': metric_code, 'current': current_value, 'limit': limit, 'percentage': pct}
                )

