import logging
import re
from typing import Any, Dict
from django.utils import timezone
from .models import IntegrationApiLog

logger = logging.getLogger(__name__)

SENSITIVE_KEYS_REGEX = re.compile(
    r'(?i)(token|secret|password|key|authorization|bearer|cookie|credential|cvx_live|cvx_test)'
)


def redact_sensitive_dict(data: Any) -> Any:
    """Recursively redacts values for sensitive keys in dictionaries or lists."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if SENSITIVE_KEYS_REGEX.search(k):
                cleaned[k] = '***REDACTED***'
            elif isinstance(v, (dict, list)):
                cleaned[k] = redact_sensitive_dict(v)
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]
    return data


def log_api_request(
    request,
    response,
    duration_ms: int,
    endpoint: str,
    api_version: str = 'v1'
) -> IntegrationApiLog:
    """Safely logs API request metadata without storing credentials or sensitive payloads."""
    tenant = getattr(request, 'tenant', None)
    auth_context = getattr(request, 'auth_context', None)

    service_account_id = ''
    api_key_id = ''

    if auth_context:
        service_account_id = auth_context.principal_id if auth_context.principal_type == 'service_account' else ''
        api_key_id = str(auth_context.api_key.id) if auth_context.api_key else ''

    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:250]
    request_id = getattr(request, 'request_id', '') or request.headers.get('X-Request-ID', '')

    status_code = getattr(response, 'status_code', 200)

    try:
        log_entry = IntegrationApiLog.objects.create(
            request_id=request_id or f"req_{timezone.now().timestamp()}",
            tenant=tenant,
            service_account_id=service_account_id,
            api_key_id=api_key_id,
            endpoint=endpoint[:250],
            http_method=request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            source_ip=client_ip,
            user_agent=user_agent,
            api_version=api_version,
        )
        return log_entry
    except Exception as exc:
        logger.error('Failed to write IntegrationApiLog: %s', exc)
        return None

