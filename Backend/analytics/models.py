from django.conf import settings
from django.db import models


class CampaignMetric(models.Model):
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.CASCADE, related_name='metrics')
    date = models.DateField()
    sent = models.IntegerField(default=0)
    delivered = models.IntegerField(default=0)
    opened = models.IntegerField(default=0)
    clicked = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='metrics')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.campaign.name} - {self.date}'
