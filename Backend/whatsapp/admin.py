from django.contrib import admin
from django import forms

from .models import (BusinessNumber, Customer, Department, DepartmentMember, Enquiry,
                     Lead, Notification, RoutingRule, WhatsAppConfiguration,
                     WhatsAppMessage)


class WhatsAppConfigurationAdminForm(forms.ModelForm):
    class Meta:
        model = WhatsAppConfiguration
        fields = '__all__'
        widgets = {
            'verify_token': forms.PasswordInput(render_value=True),
            'webhook_secret': forms.PasswordInput(render_value=True),
            'meta_access_token': forms.PasswordInput(render_value=True),
        }


@admin.register(WhatsAppConfiguration)
class WhatsAppConfigurationAdmin(admin.ModelAdmin):
    form = WhatsAppConfigurationAdminForm
    list_display = (
        'tenant', 'business_number', 'phone_number_id', 'business_account_id', 'api_version',
        'notification_template', 'default_team', 'updated_at',
    )
    list_filter = ('tenant', 'default_team')
    search_fields = ('tenant__name', 'business_number', 'phone_number_id', 'business_account_id')
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('WhatsApp account', {'fields': (
            'tenant', 'business_number', 'default_team',
        )}),
        ('Meta Cloud API', {
            'fields': (
                'meta_app_id', 'business_account_id', 'phone_number_id', 'api_version',
                'meta_access_token',
            ),
            'description': 'App, WABA, sender Phone Number ID, Graph API version, and System User token.',
        }),
        ('Employee notification template', {
            'fields': ('notification_template', 'template_language'),
            'description': 'Exact name and language code of the approved Meta template.',
        }),
        ('Webhook security', {
            'fields': ('verify_token', 'webhook_secret'),
            'description': 'Callback verification token and Meta App Secret used to validate signed webhook requests.',
        }),
        ('Audit', {'fields': ('updated_at',)}),
    )

@admin.register(BusinessNumber)
class BusinessNumberAdmin(admin.ModelAdmin):
    list_display = ('number', 'tenant', 'phone_number_id', 'forwarding_number', 'label', 'default_team', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('number', 'tenant__name', 'phone_number_id', 'forwarding_number', 'label')


class DepartmentMemberInline(admin.TabularInline):
    model = DepartmentMember
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'slug', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name', 'tenant__name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DepartmentMemberInline]


@admin.register(DepartmentMember)
class DepartmentMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'whatsapp_number', 'active', 'notification_enabled')
    list_filter = ('department', 'active', 'notification_enabled')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'tenant', 'whatsapp_number', 'organization_name', 'email', 'updated_at')
    list_filter = ('tenant',)
    search_fields = ('full_name', 'tenant__name', 'whatsapp_number', 'email', 'organization_name')


class NotificationInline(admin.TabularInline):
    model = Notification
    extra = 0
    readonly_fields = ('recipient', 'whatsapp_message_id', 'status', 'error_message', 'created_at', 'updated_at')


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'tenant', 'customer', 'department', 'status', 'created_at')
    list_filter = ('tenant', 'department', 'status', 'created_at')
    search_fields = ('reference', 'tenant__name', 'customer__full_name', 'customer__whatsapp_number', 'message')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    inlines = [NotificationInline]


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_message_id', 'direction', 'message_type', 'status', 'timestamp')
    list_filter = ('direction', 'status', 'message_type')
    search_fields = ('whatsapp_message_id', 'content')
    readonly_fields = ('raw_payload', 'created_at', 'attachment_name', 'attachment_content_type')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'enquiry', 'recipient', 'template_name', 'status', 'retry_count', 'created_at', 'sent_at')
    list_filter = ('status', 'recipient__department', 'recipient', 'created_at')
    search_fields = ('enquiry__reference', 'recipient__name', 'whatsapp_message_id', 'error_message')
    readonly_fields = (
        'enquiry', 'recipient', 'recipient_number', 'template_name', 'whatsapp_message_id', 'status',
        'request_payload', 'response_payload', 'http_status_code', 'error_code', 'error_subcode',
        'error_message', 'fbtrace_id', 'retry_count', 'created_at', 'sent_at', 'updated_at',
    )
admin.site.register(RoutingRule)
admin.site.register(Lead)
