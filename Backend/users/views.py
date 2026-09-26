from django.contrib.auth import get_user_model
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from smtplib import SMTPException
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Tenant
from .permissions import PlatformAdminPermission, access_role
from .tenant_context import filter_by_tenant, get_request_tenant, require_request_tenant
from rest_framework.exceptions import PermissionDenied
from .serializers import (AcceptInvitationSerializer, CustomTokenObtainPairSerializer,
                          IAMInvitationSerializer, RegisterSerializer, RegisterTenantSerializer,
                          TeamMemberSerializer, TenantSerializer, UserSerializer)

User = get_user_model()


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok', 'service': 'backend'})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        if not settings.ENABLE_PUBLIC_REGISTRATION:
            return Response({'detail': 'Public registration is disabled.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class TeamDirectoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = filter_by_tenant(User.objects.filter(is_active=True).exclude(team_name=''), request)
        users = users.order_by('team_name', 'first_name', 'last_name')
        grouped = {}

        for user in users:
            grouped.setdefault(user.team_name, []).append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'whatsapp_number': user.whatsapp_number or user.phone_number,
                'team_name': user.team_name,
                'role': user.role,
            })

        return Response({
            'teams': [
                {
                    'team_name': team_name,
                    'members': members,
                }
                for team_name, members in grouped.items()
            ]
        })


class TeamMemberListCreateView(generics.ListAPIView):
    permission_classes = [PlatformAdminPermission]
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        queryset = User.objects.order_by('-is_active', 'email')
        return filter_by_tenant(queryset, self.request)


class TeamMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PlatformAdminPermission]
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        return filter_by_tenant(User.objects.all(), self.request)

    def get_object(self):
        instance = super().get_object()
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if instance.pk == self.request.user.pk:
                raise PermissionDenied('You cannot change or revoke your own access.')
            if instance.is_superuser:
                raise PermissionDenied('Superuser access must be managed through Django administration.')
            if access_role(instance) == 'owner' and access_role(self.request.user) != 'owner':
                raise PermissionDenied('Only an Owner can manage another Owner.')
        return instance

    def perform_destroy(self, instance):
        instance.delete()


class TenantCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = get_request_tenant(request)
        if not tenant and request.user.is_superuser:
            override_id = request.headers.get('X-Tenant-ID') or request.META.get('HTTP_X_TENANT_ID')
            if override_id:
                try:
                    tenant = Tenant.objects.filter(pk=int(override_id)).first()
                except (ValueError, TypeError):
                    pass

        if not tenant:
            if request.user.is_superuser:
                # Return synthetic platform administrator info
                return Response({
                    'id': 0,
                    'name': 'Platform Administration',
                    'slug': 'platform-admin',
                    'tier': 'large',
                    'tier_display': 'Large (Enterprise)',
                    'status': 'active',
                    'status_display': 'Active',
                    'max_numbers': 999,
                    'max_users': 999,
                    'max_campaigns_monthly': 9999,
                    'users_count': User.objects.filter(is_active=True).count(),
                    'numbers_count': 1,
                    'campaigns_count': 0,
                    'is_platform_admin': True,
                    'tenant': None,
                })
            return Response({'detail': 'No organization assigned.'}, status=status.HTTP_404_NOT_FOUND)

        if tenant.status == 'suspended' and not request.user.is_superuser:
            raise PermissionDenied('Your organization account has been suspended.')

        data = TenantSerializer(tenant).data
        data['is_platform_admin'] = False
        data['tenant'] = TenantSerializer(tenant).data
        return Response(data)


class PlatformTenantListView(generics.ListCreateAPIView):
    queryset = Tenant.objects.all().order_by('name')
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            raise PermissionDenied('Only Platform Administrators can view all tenants.')
        return super().get_queryset()

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied('Only Platform Administrators can create tenants directly.')
        tenant = serializer.save()
        tenant.apply_tier_defaults()
        tenant.save()


class PlatformTenantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            raise PermissionDenied('Only Platform Administrators can manage tenants.')
        return super().get_queryset()

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied('Only Platform Administrators can manage tenants.')
        old_tier = serializer.instance.tier
        old_status = serializer.instance.status
        tenant = serializer.save()

        # Lifecycle state machine enforcement
        new_status = self.request.data.get('status')
        if new_status and new_status.upper() != old_status.upper():
            from organization.services.tenant_service import TenantService
            reason = self.request.data.get('reason', 'Platform admin lifecycle update')
            TenantService.transition_lifecycle(
                tenant=tenant,
                target_status=new_status,
                actor=self.request.user,
                reason=reason,
            )

        if 'tier' in self.request.data and tenant.tier != old_tier:
            if 'max_numbers' not in self.request.data and 'max_users' not in self.request.data and 'max_campaigns_monthly' not in self.request.data:
                tenant.apply_tier_defaults()
                tenant.save()



class RegisterTenantView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        import re
        from rest_framework_simplejwt.tokens import RefreshToken
        from whatsapp.models import Department

        from organization.services.tenant_service import TenantService

        serializer = RegisterTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_name = serializer.validated_data['company_name'].strip()
        tier = serializer.validated_data['tier']
        email = serializer.validated_data['email'].strip().lower()
        password = serializer.validated_data['password']
        first_name = serializer.validated_data['first_name'].strip()
        last_name = serializer.validated_data.get('last_name', '').strip()
        phone_number = serializer.validated_data.get('phone_number', '').strip()

        tenant, user = TenantService.provision_tenant(
            company_name=company_name,
            tier=tier,
            owner_email=email,
            owner_password=password,
            owner_first_name=first_name,
            owner_last_name=last_name,
            owner_phone=phone_number,
        )

        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['username'] = user.username
        refresh['tenant_id'] = tenant.id
        refresh['is_superuser'] = user.is_superuser

        return Response({
            'message': 'Tenant and workspace created successfully.',
            'tenant': TenantSerializer(tenant).data,
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)



class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class IAMInvitationView(APIView):
    permission_classes = [PlatformAdminPermission]

    @transaction.atomic
    def post(self, request):
        serializer = IAMInvitationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        existing = User.objects.filter(email=email).first()
        if existing and existing.is_active:
            return Response({'detail': 'An active user already exists with this email.'}, status=status.HTTP_409_CONFLICT)
        if existing and (existing.is_superuser or (
            access_role(existing) == 'owner' and access_role(request.user) != 'owner'
        )):
            raise PermissionDenied('You cannot replace this identity invitation.')
        tenant = get_request_tenant(request)
        if not tenant and not request.user.is_superuser:
            raise PermissionDenied('No active organization/tenant is associated with your account.')
        if tenant and tenant.status == 'suspended' and not request.user.is_superuser:
            raise PermissionDenied('Your organization account has been suspended. Please contact platform support.')
        if tenant and not request.user.is_superuser:
            active_users = tenant.users.filter(is_active=True).count()
            if active_users >= tenant.max_users:
                return Response({
                    'detail': f'Your {tenant.get_tier_display()} plan seat limit allows up to {tenant.max_users} team member(s). Please upgrade to invite more.'
                }, status=status.HTTP_400_BAD_REQUEST)

        user = existing or User(email=email, username=email)
        user.tenant = tenant
        user.role = serializer.validated_data['role']
        user.number_access = serializer.validated_data.get('number_access', 'both')
        user.team_name = serializer.validated_data.get('team_name', 'Support')
        user.is_active = False
        user.is_staff = user.role in ('admin', 'owner')
        user.set_unusable_password()
        user.save()
        token = signing.dumps({'user_id': user.pk, 'email': user.email, 'tenant_id': tenant.id if tenant else None}, salt='iam-invitation')
        invite_url = f"{settings.FRONTEND_URL.rstrip('/')}/?invite={token}"
        try:
            delivered = send_mail(
                'You are invited to Convernix',
                f'You have been invited with {user.get_role_display()} access. Activate your account: {invite_url}',
                None, [user.email], fail_silently=False,
            )
            if delivered != 1:
                raise SMTPException('Email was not accepted by SMTP.')
        except (SMTPException, OSError, ImproperlyConfigured, ValidationError):
            transaction.set_rollback(True)
            return Response(
                {'detail': 'Invitation could not be sent. Ask a server administrator to check SMTP configuration and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'message': 'Invitation sent.', 'email': user.email, 'role': user.role}, status=status.HTTP_201_CREATED)


class AcceptInvitationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = signing.loads(
                serializer.validated_data['token'], salt='iam-invitation',
                max_age=settings.IAM_INVITATION_MAX_AGE_SECONDS,
            )
            user = User.objects.get(pk=payload['user_id'], email=payload['email'], is_active=False)
        except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError):
            return Response({'detail': 'This invitation is invalid or has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        user.first_name = serializer.validated_data['first_name']
        user.last_name = serializer.validated_data.get('last_name', '')
        user.set_password(serializer.validated_data['password'])
        if not user.tenant and payload.get('tenant_id'):
            user.tenant_id = payload['tenant_id']
        tenant = user.tenant or (Tenant.objects.filter(pk=payload.get('tenant_id')).first() if payload.get('tenant_id') else None)
        if tenant and not user.is_superuser:
            if tenant.status == 'suspended':
                return Response({'detail': 'Your organization account has been suspended. Please contact platform support.'}, status=status.HTTP_403_FORBIDDEN)
            active_users = tenant.users.filter(is_active=True).count()
            if active_users >= tenant.max_users:
                return Response({
                    'detail': f'Your {tenant.get_tier_display()} plan seat limit allows up to {tenant.max_users} active team member(s). Please ask your administrator to upgrade your plan.'
                }, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save()
        return Response({'message': 'Account activated. You can now sign in.'})


class AuthProviderView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            'password': True,
            'google': {'enabled': bool(settings.GOOGLE_OAUTH_CLIENT_ID)},
            'microsoft': {'enabled': bool(settings.MICROSOFT_OAUTH_CLIENT_ID)},
        })
