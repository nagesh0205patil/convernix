import logging
import re
from typing import Any, Dict, Optional
from django.utils import timezone
from organization.models import AuditLog

logger = logging.getLogger(__name__)

# Keys that must ALWAYS be redacted from metadata/payloads
SENSITIVE_KEY_PATTERNS = re.compile(
    r'(password|token|secret|api_key|apikey|private_key|card_number|cvv|authorization|auth_bearer|encryption_key)',
    re.IGNORECASE
)


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts passwords, tokens, API keys, and sensitive parameters."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                cleaned[k] = '[REDACTED]'
            elif isinstance(v, (dict, list)):
                cleaned[k] = redact_sensitive_data(v)
            elif isinstance(v, str) and (
                v.startswith('EAAB') or v.startswith('cvx_live_') or len(v) > 200 and 'secret' in v.lower()
            ):
                cleaned[k] = '[REDACTED]'
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


def log_admin_action(
    tenant,
    actor_name: str,
    action: str,
    module: str,
    resource: str,
    ip_address: str = '127.0.0.1',
    status: str = 'Success',
    metadata: Optional[Dict[str, Any]] = None,
    actor_email: str = '',
    request: Optional[Any] = None,
) -> AuditLog:
    """Create an immutable, tamper-resistant audit record with automated global secret redaction."""
    safe_meta = redact_sensitive_data(metadata or {})
    if request:
        if not ip_address or ip_address == '127.0.0.1':
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if user_agent and 'user_agent' not in safe_meta:
            safe_meta['user_agent'] = user_agent[:255]
        req_id = request.META.get('HTTP_X_REQUEST_ID', '')
        if req_id:
            safe_meta['request_id'] = req_id

    entry = AuditLog.objects.create(
        tenant=tenant,
        actor_name=actor_name,
        actor_email=actor_email,
        action=action,
        module=module,
        resource=resource,
        ip_address=ip_address,
        status=status,
        metadata=safe_meta,
    )
    logger.info(
        'AUDIT: [%s] tenant=%s actor=%s action="%s" resource="%s" status=%s',
        module,
        getattr(tenant, 'slug', tenant.id if tenant else 'none'),
        actor_email or actor_name,
        action,
        resource,
        status,
    )
    return entry

