from rest_framework import serializers

from .models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = (
            'id',
            'name',
            'message',
            'status',
            'target_audience',
            'scheduled_at',
            'sent_count',
            'delivered_count',
            'opened_count',
            'clicked_count',
            'created_by',
            'business_number',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'business_number', 'created_at', 'updated_at')
