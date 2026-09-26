from django.contrib import admin
from .models import Campaign


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'status', 'business_number', 'sent_count', 'created_by', 'created_at')
    list_filter = ('tenant', 'status', 'created_at')
    search_fields = ('name', 'tenant__name', 'message')
    readonly_fields = ('created_at', 'updated_at')

