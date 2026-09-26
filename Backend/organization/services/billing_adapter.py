import abc
import hashlib
import hmac
import logging
import uuid
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from users.models import Tenant
from organization.models import (
    BillingCustomer,
    BillingEvent,
    Invoice,
    InvoiceItem,
    Payment,
    Plan,
    Subscription,
)
from organization.services.audit_service import log_admin_action
from organization.services.event_service import publish_domain_event

logger = logging.getLogger(__name__)


class BillingProviderAdapter(abc.ABC):
    """Abstract interface decoupling billing vendors from Convernix core."""

    @abc.abstractmethod
    def create_customer(self, tenant: Tenant, email: str, name: str) -> str:
        """Registers a customer in the payment gateway; returns provider_customer_id."""
        pass

    @abc.abstractmethod
    def create_checkout_session(self, tenant: Tenant, plan: Plan, return_url: str) -> Dict[str, Any]:
        """Creates hosted payment/subscription checkout session."""
        pass

    @abc.abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        """Validates webhook HMAC signature."""
        pass

    @abc.abstractmethod
    def handle_webhook_event(self, event_type: str, event_id: str, payload: Dict[str, Any]) -> bool:
        """Idempotently handles payment/subscription lifecycle events."""
        pass


class ConvernixBillingAdapter(BillingProviderAdapter):
    """Enterprise billing adapter supporting tokenized checkouts and idempotent webhooks."""

    def create_customer(self, tenant: Tenant, email: str, name: str) -> str:
        bc = BillingCustomer.objects.filter(tenant=tenant).first()
        if bc and bc.provider_customer_id:
            return bc.provider_customer_id

        prov_id = f'cus_cvx_{uuid.uuid4().hex[:14]}'
        BillingCustomer.objects.update_or_create(
            tenant=tenant,
            defaults={'provider_customer_id': prov_id, 'currency': 'INR'}
        )
        return prov_id

    def create_checkout_session(self, tenant: Tenant, plan: Plan, return_url: str) -> Dict[str, Any]:
        cust_id = self.create_customer(tenant, f'billing@{tenant.slug}.example', tenant.name)
        session_id = f'cs_live_{uuid.uuid4().hex[:16]}'
        checkout_url = f'{return_url}?checkout_session={session_id}&plan={plan.code}'
        return {
            'session_id': session_id,
            'checkout_url': checkout_url,
            'customer_id': cust_id,
            'amount': float(plan.price_inr),
            'currency': 'INR',
        }

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        secret = getattr(settings, 'BILLING_WEBHOOK_SECRET', '') or 'cvx_billing_webhook_secret'
        if not signature_header:
            return False
        expected = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header.strip())

    def handle_webhook_event(self, event_type: str, event_id: str, payload: Dict[str, Any]) -> bool:
        # Idempotency check: record billing event
        existing = BillingEvent.objects.filter(idempotency_key=event_id).first()
        if existing:
            logger.info('Duplicate billing webhook ignored: %s', event_id)
            return True

        tenant_id = payload.get('tenant_id')
        tenant = Tenant.objects.filter(pk=tenant_id).first() if tenant_id else None

        BillingEvent.objects.create(
            tenant=tenant,
            event_type=event_type,
            idempotency_key=event_id,
            payload=payload,
        )

        if not tenant:
            return True

        if event_type == 'invoice.paid':
            inv_number = payload.get('invoice_number', f'INV-{uuid.uuid4().hex[:8].upper()}')
            amount = payload.get('amount', 6999.00)
            inv, _ = Invoice.objects.get_or_create(
                tenant=tenant,
                invoice_number=inv_number,
                defaults={
                    'billing_period': timezone.now().strftime('%B %Y'),
                    'amount': amount,
                    'status': 'paid',
                }
            )
            inv.status = 'paid'
            inv.save()

            Payment.objects.create(
                tenant=tenant,
                invoice=inv,
                payment_reference=f'PAY-{uuid.uuid4().hex[:12].upper()}',
                amount=amount,
                currency='INR',
                status='succeeded',
            )

            publish_domain_event('invoice.paid', tenant.id, {'invoice': inv_number, 'amount': amount})

        elif event_type == 'invoice.payment_failed':
            publish_domain_event('invoice.payment_failed', tenant.id, {'reason': payload.get('failure_reason')})

        return True

