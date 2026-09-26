from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from .models import SMTPConfiguration, Tenant
from .smtp_crypto import encrypt_secret

User = get_user_model()


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tier', 'status', 'max_numbers', 'max_users', 'max_campaigns_monthly', 'created_at')
    list_filter = ('tier', 'status', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'tenant', 'first_name', 'last_name', 'team_name', 'role', 'number_access', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('tenant', 'phone_number', 'whatsapp_number', 'team_name', 'role', 'number_access', 'organization')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Info', {'fields': ('tenant', 'email', 'first_name', 'last_name', 'phone_number', 'whatsapp_number', 'team_name', 'role', 'number_access', 'organization')}),
    )
    search_fields = ('email', 'username', 'first_name', 'last_name', 'team_name', 'whatsapp_number', 'tenant__name')
    list_filter = ('tenant', 'team_name', 'role', 'number_access', 'is_staff', 'is_active')


class SMTPConfigurationForm(forms.ModelForm):
    smtp_username = forms.CharField(
        required=False, strip=False, label='New SMTP username',
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Write-only. Leave blank to keep the saved username.',
    )
    smtp_password = forms.CharField(
        required=False, strip=False, label='New SMTP password',
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Write-only. Leave blank to keep the saved password.',
    )

    class Meta:
        model = SMTPConfiguration
        fields = ('enabled', 'host', 'port', 'security', 'use_authentication',
                  'from_email', 'from_name', 'timeout')

    def clean(self):
        data = super().clean()
        for field, destination in [('smtp_username', 'username_encrypted'), ('smtp_password', 'password_encrypted')]:
            if data.get(field):
                try:
                    setattr(self.instance, destination, encrypt_secret(data[field]))
                except ImproperlyConfigured as error:
                    self.add_error(field, str(error))
        return data


@admin.register(SMTPConfiguration)
class SMTPConfigurationAdmin(admin.ModelAdmin):
    form = SMTPConfigurationForm
    list_display = ('__str__', 'host', 'port', 'security', 'enabled', 'updated_at')
    readonly_fields = ('username_encrypted', 'password_encrypted', 'updated_at')
    fieldsets = (
        ('SMTP server', {'fields': ('enabled', 'host', 'port', 'security', 'timeout')}),
        ('Sender', {'fields': ('from_email', 'from_name')}),
        ('Authentication', {
            'fields': ('use_authentication', 'smtp_username', 'smtp_password'),
            'description': 'Saved credentials are never returned to this form. Enter new values only to replace them.',
        }),
        ('Encrypted stored credentials', {
            'fields': ('username_encrypted', 'password_encrypted'),
            'description': 'Authenticated ciphertext, not plaintext or reversible Base64 encoding. The encryption key is held on the server outside the database.',
        }),
        ('Audit', {'fields': ('updated_at',)}),
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser and not SMTPConfiguration.objects.exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    @method_decorator(sensitive_post_parameters('smtp_username', 'smtp_password'))
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        return super().changeform_view(request, object_id, form_url, extra_context)
