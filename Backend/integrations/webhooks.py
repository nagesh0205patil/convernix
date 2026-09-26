import hashlib
import hmac
import json
import logging
import random
import time
import urllib.request
import urllib.error
from datetime import timedelta
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from .models import WebhookEndpoint, WebhookDelivery, OutboxEvent
from .ssrf import validate_safe_url, SSRFValidationError

logger = logging.getLogger(__name__)

# Delivery retry backoff schedule in seconds: attempt 1=10s, attempt 2=60s, attempt 3=300s, attempt 4=1800s
RETRY_BACKOFF_SCHEDULE = [10, 60, 300, 1800, 7200]
MAX_DELIVERY_ATTEMPTS = 5
MAX_CONSECUTIVE_FAILURES_BEFORE_AUTO_DISABLE = 10


def generate_webhook_secret() -> str:
    import secrets
    return f"whsec_{secrets.token_urlsafe(32)}"


def compute_webhook_signature(secret: str, timestamp: str, raw_payload: str) -> str:
    """
    Computes HMAC-SHA256 signature over: timestamp + "." + raw_body.
    """
    canonical_payload = f"{timestamp}.{raw_payload}".encode('utf-8')
    signing_key = secret.encode('utf-8')
    return hmac.new(signing_key, canonical_payload, hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, timestamp: str, raw_payload: str, signature: str, tolerance_seconds: int = 300) -> bool:
    """
    Consumer verification helper for signature verification with constant-time comparison
    and timestamp tolerance window to prevent replay attacks.
    """
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > tolerance_seconds:
            return False
    except (ValueError, TypeError):
        return False

    expected_sig = compute_webhook_signature(secret, timestamp, raw_payload)
    return hmac.compare_digest(expected_sig, signature)


def matches_event_filter(filter_patterns: List[str], event_type: str) -> bool:
    """
    Evaluates whether an event type matches any pattern in event_filters list.
    Supports wildcards like '*' or 'lead.*' or exact match 'lead.created'.
    """
    if not filter_patterns or '*' in filter_patterns:
        return True

    for pattern in filter_patterns:
        pattern = pattern.strip()
        if pattern == event_type:
            return True
        if pattern.endswith('.*'):
            prefix = pattern[:-2]
            if event_type.startswith(prefix + '.'):
                return True
    return False


def dispatch_webhook_event_for_outbox(outbox_event: OutboxEvent):
    """
    Finds active webhook endpoints for the event's tenant that subscribe to the event_type,
    creates pending WebhookDelivery records, and schedules immediate or async execution.
    """
    tenant = outbox_event.tenant
    event_type = outbox_event.event_type
    payload = outbox_event.payload

    endpoints = WebhookEndpoint.objects.filter(
        tenant=tenant,
        status='active'
    )

    for endpoint in endpoints:
        if matches_event_filter(endpoint.event_filters, event_type):
            delivery = WebhookDelivery.objects.create(
                tenant=tenant,
                endpoint=endpoint,
                event_id=outbox_event.id,
                event_type=event_type,
                payload=payload,
                attempt_number=1,
                status='retrying',
            )
            # Execute delivery (can run synchronously or be passed to worker)
            execute_webhook_delivery(delivery.id)


def execute_webhook_delivery(delivery_id: str) -> WebhookDelivery:
    """
    Asynchronously or synchronously sends the webhook payload to the customer endpoint.
    Performs SSRF validation, canonical HMAC-SHA256 signing, timing measurement, and backoff scheduling.
    """
    try:
        delivery = WebhookDelivery.objects.select_related('endpoint', 'tenant').get(id=delivery_id)
    except WebhookDelivery.DoesNotExist:
        logger.error('WebhookDelivery %s not found', delivery_id)
        return None

    endpoint = delivery.endpoint
    if endpoint.status != 'active':
        delivery.status = 'failed'
        delivery.error_message = f'Endpoint is {endpoint.status}'
        delivery.error_category = 'client_error'
        delivery.save(update_fields=['status', 'error_message', 'error_category'])
        return delivery

    # 1. SSRF URL validation
    allow_http = getattr(settings, 'DEBUG', False) or getattr(settings, 'TESTING', False) or 'test' in getattr(settings, 'DATABASES', {}).get('default', {}).get('NAME', '')
    try:
        validate_safe_url(endpoint.url, allow_http=allow_http)
    except SSRFValidationError as ssrf_err:
        logger.warning('SSRF blocked for webhook delivery %s to url %s: %s', delivery.id, endpoint.url, ssrf_err)
        delivery.status = 'failed'
        delivery.error_category = 'ssrf_blocked'
        delivery.error_message = str(ssrf_err)
        delivery.save(update_fields=['status', 'error_category', 'error_message'])
        return delivery

    # 2. Prepare payload & signature
    timestamp = str(int(time.time()))
    json_body = json.dumps(delivery.payload, separators=(',', ':'), sort_keys=True)
    secret = endpoint.get_signing_secret()
    signature = compute_webhook_signature(secret, timestamp, json_body)

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Convernix-Webhook-Dispatcher/1.0',
        'X-Convernix-Event-ID': str(delivery.event_id),
        'X-Convernix-Timestamp': timestamp,
        'X-Convernix-Signature': signature,
    }

    req = urllib.request.Request(
        endpoint.url,
        data=json_body.encode('utf-8'),
        headers=headers,
        method='POST'
    )

    start_time = time.time()
    http_status = None
    error_cat = ''
    error_msg = ''

    try:
        # 10 second timeout for webhook deliveries
        with urllib.request.urlopen(req, timeout=10) as resp:
            http_status = resp.status
            duration_ms = int((time.time() - start_time) * 1000)

            if 200 <= http_status < 300:
                delivery.status = 'success'
                delivery.http_status = http_status
                delivery.duration_ms = duration_ms
                delivery.delivered_at = timezone.now()
                delivery.next_retry_at = None
                delivery.error_category = ''
                delivery.error_message = ''
                delivery.save()

                # Reset consecutive failures on endpoint
                if endpoint.consecutive_failures > 0:
                    endpoint.consecutive_failures = 0
                    endpoint.save(update_fields=['consecutive_failures'])
                return delivery

    except urllib.error.HTTPError as http_err:
        http_status = http_err.code
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"HTTP {http_status}: {http_err.reason}"
        error_cat = 'client_error' if 400 <= http_status < 500 else 'server_error'

    except urllib.error.URLError as url_err:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(url_err.reason)
        if 'timed out' in error_msg.lower():
            error_cat = 'timeout'
        else:
            error_cat = 'network'

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(exc)
        error_cat = 'network'

    # Handle delivery failure & retry scheduling
    delivery.http_status = http_status
    delivery.duration_ms = duration_ms
    delivery.error_category = error_cat
    delivery.error_message = error_msg

    # Increment failure counter on endpoint
    endpoint.consecutive_failures += 1
    if endpoint.consecutive_failures >= MAX_CONSECUTIVE_FAILURES_BEFORE_AUTO_DISABLE:
        endpoint.status = 'disabled'
        endpoint.disabled_reason = f'Automatically disabled after {endpoint.consecutive_failures} consecutive delivery failures.'
    endpoint.save(update_fields=['consecutive_failures', 'status', 'disabled_reason'])

    # Determine retry eligibility
    # Permanent client errors (400, 401, 403, 404, 405, 410) are NOT retried, except 429
    is_permanent_client_error = (http_status is not None and 400 <= http_status < 500 and http_status != 429)

    if delivery.attempt_number >= MAX_DELIVERY_ATTEMPTS or is_permanent_client_error:
        delivery.status = 'dlq'  # Dead Letter Queue
        delivery.next_retry_at = None
    else:
        delivery.status = 'retrying'
        # Exponential backoff with jitter
        backoff_idx = min(delivery.attempt_number - 1, len(RETRY_BACKOFF_SCHEDULE) - 1)
        base_delay = RETRY_BACKOFF_SCHEDULE[backoff_idx]
        jitter = random.uniform(0.8, 1.2)
        delay_seconds = int(base_delay * jitter)
        delivery.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        delivery.attempt_number += 1

    delivery.save()
    return delivery


def replay_webhook_delivery(delivery: WebhookDelivery, actor=None) -> WebhookDelivery:
    """
    Manually re-triggers a delivery attempt from the Dead Letter Queue or historical logs.
    Audited through organization.models.AuditLog.
    """
    from organization.models import AuditLog

    delivery.status = 'retrying'
    delivery.attempt_number += 1
    delivery.next_retry_at = None
    delivery.save(update_fields=['status', 'attempt_number', 'next_retry_at'])

    AuditLog.log(
        tenant=delivery.tenant,
        actor_name=getattr(actor, 'email', 'System Operator') if actor else 'System Operator',
        actor_email=getattr(actor, 'email', '') if actor else '',
        action='WEBHOOK_REPLAY_REQUESTED',
        module='Integrations',
        resource=f'WebhookDelivery #{delivery.id} ({delivery.event_type})',
        status='Success',
        metadata={
            'delivery_id': str(delivery.id),
            'endpoint_id': str(delivery.endpoint_id),
            'endpoint_url': delivery.endpoint.url,
            'event_type': delivery.event_type,
        }
    )

    return execute_webhook_delivery(str(delivery.id))

