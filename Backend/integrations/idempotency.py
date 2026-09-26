import functools
import hashlib
import json
import logging
from datetime import timedelta
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from .models import IdempotencyRecord

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = 'HTTP_IDEMPOTENCY_KEY'
IDEMPOTENCY_EXPIRY_HOURS = 24


def compute_request_hash(method: str, path: str, body_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(method.upper().encode('utf-8'))
    h.update(b':')
    h.update(path.encode('utf-8'))
    h.update(b':')
    h.update(body_bytes)
    return h.hexdigest()


def enforce_idempotency(expiry_hours: int = IDEMPOTENCY_EXPIRY_HOURS):
    """
    View method decorator for mutation endpoints.
    Detects Idempotency-Key header, prevents duplicate execution, returns cached response or 409 conflict.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(self, request, *args, **kwargs):
            raw_key = request.META.get(IDEMPOTENCY_HEADER) or request.headers.get('Idempotency-Key')
            if not raw_key:
                # No idempotency key provided; proceed normally
                return view_func(self, request, *args, **kwargs)

            idempotency_key = raw_key.strip()
            if len(idempotency_key) > 255:
                return Response({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Idempotency-Key header exceeds maximum length of 255 characters.',
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            tenant = getattr(request, 'tenant', None)
            if not tenant:
                from users.tenant_context import get_request_tenant
                tenant = get_request_tenant(request)

            if not tenant:
                return Response({
                    'error': {
                        'code': 'AUTHENTICATION_FAILED',
                        'message': 'Valid tenant context required for idempotent operations.',
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)

            credential_id = getattr(getattr(request, 'auth_context', None), 'principal_id', None) or str(getattr(request.user, 'pk', 'unknown'))
            request_body = request.body if hasattr(request, 'body') else b''
            req_hash = compute_request_hash(request.method, request.path, request_body)

            # Check for existing record
            existing = IdempotencyRecord.objects.filter(
                tenant=tenant,
                idempotency_key=idempotency_key
            ).first()

            if existing:
                # Payload mismatch check
                if existing.request_hash != req_hash:
                    return Response({
                        'error': {
                            'code': 'IDEMPOTENCY_CONFLICT',
                            'message': 'Idempotency key has already been used with a different request payload or endpoint.',
                            'details': {'idempotency_key': idempotency_key},
                        }
                    }, status=status.HTTP_409_CONFLICT)

                # Still processing concurrently
                if existing.status == 'in_progress':
                    return Response({
                        'error': {
                            'code': 'IDEMPOTENCY_CONFLICT',
                            'message': 'A concurrent request with this Idempotency-Key is currently in progress. Please retry shortly.',
                            'details': {'idempotency_key': idempotency_key},
                        }
                    }, status=status.HTTP_409_CONFLICT)

                # Completed: return cached response
                if existing.status == 'completed':
                    resp = Response(existing.response_body, status=existing.response_code or 200)
                    resp['X-Cache-Lookup'] = 'IDEMPOTENT_HIT'
                    resp['Idempotency-Key'] = idempotency_key
                    return resp

            # Attempt to reserve the key atomically
            expires_at = timezone.now() + timedelta(hours=expiry_hours)
            try:
                with transaction.atomic():
                    record = IdempotencyRecord.objects.create(
                        tenant=tenant,
                        credential_id=credential_id,
                        idempotency_key=idempotency_key,
                        request_hash=req_hash,
                        status='in_progress',
                        expires_at=expires_at,
                    )
            except IntegrityError:
                # Race condition: another thread inserted between our check and insert
                existing = IdempotencyRecord.objects.filter(
                    tenant=tenant,
                    idempotency_key=idempotency_key
                ).first()
                if existing and existing.status == 'completed' and existing.request_hash == req_hash:
                    resp = Response(existing.response_body, status=existing.response_code or 200)
                    resp['X-Cache-Lookup'] = 'IDEMPOTENT_HIT'
                    resp['Idempotency-Key'] = idempotency_key
                    return resp
                return Response({
                    'error': {
                        'code': 'IDEMPOTENCY_CONFLICT',
                        'message': 'Concurrent request conflict detected for this Idempotency-Key.',
                        'details': {'idempotency_key': idempotency_key},
                    }
                }, status=status.HTTP_409_CONFLICT)

            # Execute view function
            try:
                response = view_func(self, request, *args, **kwargs)
                resp_code = response.status_code if hasattr(response, 'status_code') else 200
                resp_data = response.data if hasattr(response, 'data') else {}

                # If successful or standard client error that should be persisted
                if resp_code < 500:
                    record.status = 'completed'
                    record.response_code = resp_code
                    record.response_body = resp_data
                    record.save(update_fields=['status', 'response_code', 'response_body'])
                else:
                    record.status = 'failed'
                    record.response_code = resp_code
                    record.save(update_fields=['status', 'response_code'])

                if hasattr(response, '__setitem__'):
                    response['Idempotency-Key'] = idempotency_key
                return response

            except Exception as exc:
                record.status = 'failed'
                record.save(update_fields=['status'])
                raise exc

        return wrapped
    return decorator

