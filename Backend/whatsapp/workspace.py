from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import BusinessNumber, WhatsAppConfiguration


def accessible_business_numbers(user, request=None):
    configured = WhatsAppConfiguration.objects.exclude(business_number='')
    numbers = BusinessNumber.objects.filter(is_active=True)

    tenant = getattr(user, 'tenant', None)
    if getattr(user, 'is_superuser', False):
        if request:
            from users.tenant_context import get_request_tenant
            req_tenant = get_request_tenant(request)
            if req_tenant:
                configured = configured.filter(tenant=req_tenant)
                numbers = numbers.filter(tenant=req_tenant)
    else:
        if not tenant:
            configured = configured.filter(tenant__isnull=True)
            numbers = numbers.filter(tenant__isnull=True)
        else:
            if tenant.status == 'suspended':
                raise PermissionDenied('Your organization account has been suspended. Please contact platform support.')
            configured = configured.filter(tenant=tenant)
            numbers = numbers.filter(tenant=tenant)

    configured_numbers = configured.values_list('business_number', flat=True)
    numbers = numbers.filter(number__in=configured_numbers)

    access = getattr(user, 'number_access', 'both')
    if access == 'india':
        numbers = numbers.filter(number__startswith='+91')
    elif access == 'us':
        numbers = numbers.filter(number__startswith='+1')
    elif access != 'both':
        return numbers.none()
    return numbers


def sync_business_numbers(tenant=None):
    """Keep selectable workspaces aligned with configured Meta senders."""
    configs = WhatsAppConfiguration.objects.exclude(business_number='')
    if tenant:
        configs = configs.filter(tenant=tenant)
    else:
        configs = configs.filter(tenant__isnull=True)
    for configuration in configs:
        BusinessNumber.objects.update_or_create(
            number=configuration.business_number,
            defaults={
                'tenant': configuration.tenant,
                'phone_number_id': configuration.phone_number_id,
                'default_team': configuration.default_team,
            },
        )


def selected_business_number(request):
    selected_id = request.headers.get('X-Business-Number-ID')
    numbers = accessible_business_numbers(request.user, request=request)
    if selected_id:
        try:
            return numbers.get(pk=selected_id)
        except (BusinessNumber.DoesNotExist, ValueError):
            raise NotFound('The selected WhatsApp business number is unavailable.')
    if numbers.count() == 1:
        return numbers.first()
    if not numbers.exists():
        # Supports fresh installations and legacy records until a sender is configured.
        tenant = getattr(request.user, 'tenant', None)
        sync_business_numbers(tenant=tenant)
        numbers = accessible_business_numbers(request.user, request=request)
        if numbers.count() == 1:
            return numbers.first()
        if not numbers.exists():
            if getattr(request.user, 'number_access', 'both') != 'both':
                raise PermissionDenied('No WhatsApp business numbers are assigned to your account.')
            return None
    raise ValidationError({'business_number': 'Select a WhatsApp business number to continue.'})


def workspace_is_explicit(request):
    """Scope configured workspaces even when clients omit the selection header."""
    return bool(
        request.headers.get('X-Business-Number-ID')
        or getattr(request.user, 'number_access', 'both') != 'both'
        or WhatsAppConfiguration.objects.exclude(business_number='').exists()
    )
