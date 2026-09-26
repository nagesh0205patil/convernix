from rest_framework import serializers

from .models import CampaignMetric


class CampaignMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignMetric
        fields = (
            'id',
            'campaign',
            'date',
            'sent',
            'delivered',
            'opened',
            'clicked',
            'created_by',
            'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')
