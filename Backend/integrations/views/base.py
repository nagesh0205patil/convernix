import time
import uuid
from typing import Any, Dict, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, pagination
from rest_framework_simplejwt.authentication import JWTAuthentication

from integrations.authentication import ApiKeyAuthentication
from integrations.api_logger import log_api_request
from users.tenant_context import require_request_tenant, get_request_tenant


class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data,
        })


class BaseV1ApiView(APIView):
    """
    Base view for all /api/v1/ endpoints.
    Enforces tenant context, API logging, and standardized response envelopes.
    """
    authentication_classes = [ApiKeyAuthentication, JWTAuthentication]
    pagination_class = StandardResultsSetPagination

    def initial(self, request, *args, **kwargs):
        self._start_time = time.time()
        if not hasattr(request, 'request_id') or not request.request_id:
            request.request_id = request.headers.get('X-Request-ID') or f"req_{uuid.uuid4().hex[:16]}"

        super().initial(request, *args, **kwargs)

        # Enforce that tenant identity is properly bound
        self.tenant = require_request_tenant(request)
        request.tenant = self.tenant

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # Attach standard correlation & security headers
        req_id = getattr(request, 'request_id', '') or f"req_{uuid.uuid4().hex[:16]}"
        response['X-Request-ID'] = req_id
        response['X-API-Version'] = 'v1'

        # Log request safe metadata
        if hasattr(self, '_start_time'):
            duration_ms = int((time.time() - self._start_time) * 1000)
            endpoint_name = request.path
            log_api_request(request, response, duration_ms, endpoint_name, api_version='v1')

        return response

    def paginate_queryset(self, queryset):
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class()
        return self._paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class()
        return self._paginator.get_paginated_response(data)

    def success_response(self, data: Any, status_code: int = status.HTTP_200_OK) -> Response:
        return Response(data, status=status_code)

    def error_response(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ) -> Response:
        req_id = getattr(self.request, 'request_id', '')
        return Response({
            'error': {
                'code': code,
                'message': message,
                'request_id': req_id,
                'details': details or {},
            }
        }, status=status_code)

