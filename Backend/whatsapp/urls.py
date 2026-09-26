from django.urls import path

from .views import (AutomationRuleDetailView, AutomationRuleListView, BusinessNumberListView, BusinessNumberView,
                    ConversationAttachmentView, ConversationDetailView, ConversationListView, ConversationReadView,
                    CustomerRevealView, EnquiryExportView, EnquiryListView, WhatsAppHealthView, WhatsAppWebhookView)

urlpatterns = [
    path('health/', WhatsAppHealthView.as_view(), name='whatsapp-health'),
    path('webhook/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
    path('enquiries/', EnquiryListView.as_view(), name='enquiry-list'),
    path('enquiries/export/', EnquiryExportView.as_view(), name='enquiry-export'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:enquiry_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:enquiry_id>/messages/<int:message_id>/attachment/', ConversationAttachmentView.as_view(), name='conversation-attachment'),
    path('conversations/<int:enquiry_id>/read/', ConversationReadView.as_view(), name='conversation-read'),
    path('customers/<int:customer_id>/reveal/', CustomerRevealView.as_view(), name='customer-reveal'),
    path('customers/<int:customer_id>/reveal-phone/', CustomerRevealView.as_view(), name='customer-reveal-phone'),
    path('settings/', BusinessNumberView.as_view(), name='business-number-settings'),
    path('business-numbers/', BusinessNumberListView.as_view(), name='business-number-list'),
    path('automations/', AutomationRuleListView.as_view(), name='automation-rules-list'),
    path('automations/<int:pk>/', AutomationRuleDetailView.as_view(), name='automation-rules-detail'),
]
