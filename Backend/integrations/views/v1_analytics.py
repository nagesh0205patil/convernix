from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from whatsapp.models import Lead, Enquiry, Customer, WhatsAppMessage
from campaigns.models import Campaign


class AnalyticsOverviewView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('analytics:read')()]

    @rate_limit(capacity=60, fill_rate=1.0)
    def get(self, request):
        total_leads = Lead.objects.filter(business_number__tenant=self.tenant).count()
        total_contacts = Customer.objects.filter(tenant=self.tenant).count()
        total_conversations = Enquiry.objects.filter(tenant=self.tenant).count()
        total_messages = WhatsAppMessage.objects.filter(customer__tenant=self.tenant).count()
        total_campaigns = Campaign.objects.filter(tenant=self.tenant).count()

        open_tickets = Enquiry.objects.filter(tenant=self.tenant).exclude(status='closed').count()

        return self.success_response({
            'tenant_id': self.tenant.id,
            'metrics': {
                'total_leads': total_leads,
                'total_contacts': total_contacts,
                'total_conversations': total_conversations,
                'open_tickets': open_tickets,
                'total_messages': total_messages,
                'total_campaigns': total_campaigns,
            }
        })

