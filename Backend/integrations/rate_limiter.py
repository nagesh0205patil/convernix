import functools
import logging
import time
from typing import Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# Default limits (requests per minute window)
DEFAULT_RATE_LIMIT = 120
BURST_CAPACITY = 150

# In-memory fallback if cache is down
_MEMORY_BUCKETS = {}


class TokenBucketLimiter:
    """Distributed token bucket rate limiter backed by Django cache / Redis."""

    def __init__(self, key: str, capacity: int = BURST_CAPACITY, fill_rate: float = 2.0):
        # fill_rate: tokens added per second (e.g. 2.0 tokens/sec = 120 tokens/min)
        self.key = f"cvx_rl:{key}"
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)

    def consume(self, tokens: int = 1) -> Tuple[bool, int, int, int]:
        """
        Consumes tokens from the bucket.
        Returns: (is_allowed, remaining_tokens, retry_after_seconds, limit)
        """
        now = time.time()
        bucket_data = None

        try:
            bucket_data = cache.get(self.key)
        except Exception as exc:
            logger.warning('Cache error in rate limiter for key %s: %s', self.key, exc)

        if bucket_data is None:
            bucket_data = _MEMORY_BUCKETS.get(self.key, {
                'tokens': self.capacity,
                'last_updated': now,
            })

        current_tokens = float(bucket_data.get('tokens', self.capacity))
        last_updated = float(bucket_data.get('last_updated', now))

        # Add tokens accumulated since last update
        elapsed = max(0.0, now - last_updated)
        new_tokens = min(self.capacity, current_tokens + (elapsed * self.fill_rate))

        if new_tokens >= tokens:
            new_tokens -= tokens
            is_allowed = True
            retry_after = 0
        else:
            is_allowed = False
            needed = tokens - new_tokens
            retry_after = max(1, int(needed / self.fill_rate) + 1)

        updated_state = {
            'tokens': new_tokens,
            'last_updated': now,
        }

        # Store with TTL covering full refill time + buffer
        ttl = int(self.capacity / self.fill_rate) + 60
        try:
            cache.set(self.key, updated_state, timeout=ttl)
        except Exception:
            _MEMORY_BUCKETS[self.key] = updated_state

        remaining = max(0, int(new_tokens))
        limit = int(self.capacity)
        return is_allowed, remaining, retry_after, limit


def get_rate_limit_key(request, resource: str) -> str:
    tenant = getattr(request, 'tenant', None)
    tenant_id = tenant.id if tenant else 'anon'

    auth_context = getattr(request, 'auth_context', None)
    if auth_context:
        client_id = f"sa_{auth_context.principal_id}"
    elif getattr(request.user, 'is_authenticated', False):
        client_id = f"u_{request.user.pk}"
    else:
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
        client_id = f"ip_{client_ip}"

    return f"t_{tenant_id}:{client_id}:{resource}"


def rate_limit(capacity: int = BURST_CAPACITY, fill_rate: float = 2.0):
    """
    Decorator for DRF API view methods to enforce rate limits.
    Returns HTTP 429 when quota is exceeded.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(self, request, *args, **kwargs):
            endpoint_name = getattr(self, '__class__', type(self)).__name__
            limit_key = get_rate_limit_key(request, endpoint_name)

            limiter = TokenBucketLimiter(limit_key, capacity=capacity, fill_rate=fill_rate)
            allowed, remaining, retry_after, limit = limiter.consume(1)

            if not allowed:
                response = Response({
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': f'API rate limit exceeded. Please retry after {retry_after} seconds.',
                        'details': {
                            'retry_after': retry_after,
                            'limit': limit,
                        }
                    }
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                response['Retry-After'] = str(retry_after)
                response['X-RateLimit-Limit'] = str(limit)
                response['X-RateLimit-Remaining'] = '0'
                response['X-RateLimit-Reset'] = str(retry_after)
                return response

            response = view_func(self, request, *args, **kwargs)
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(limit)
                response['X-RateLimit-Remaining'] = str(remaining)
            return response

        return wrapped
    return decorator

