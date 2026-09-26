from django.urls import path
from crm.views.customer_views import (
    CustomerListCreateView, CustomerDetailView, Customer360View,
    CustomerConversationsView, CustomerActivitiesView, CustomerNotesView,
    CustomerMergeView
)
from crm.views.lead_views import (
    LeadListCreateView, LeadDetailView, LeadAssignView,
    LeadStageTransitionView, LeadTagsView
)
from crm.views.pipeline_views import (
    PipelineListCreateView, PipelineDetailView,
    PipelineStageListCreateView, PipelineStageDetailView
)
from crm.views.tag_views import TagListCreateView, TagDetailView
from crm.views.custom_field_views import (
    CustomFieldDefinitionListCreateView, CustomFieldDefinitionDetailView
)
from crm.views.search_views import CrmSearchView

urlpatterns = [
    # Leads
    path('leads', LeadListCreateView.as_view(), name='crm-lead-list-create-noslash'),
    path('leads/', LeadListCreateView.as_view(), name='crm-lead-list-create'),
    path('leads/<uuid:pk>', LeadDetailView.as_view(), name='crm-lead-detail-noslash'),
    path('leads/<uuid:pk>/', LeadDetailView.as_view(), name='crm-lead-detail'),
    path('leads/<uuid:pk>/assign', LeadAssignView.as_view(), name='crm-lead-assign-noslash'),
    path('leads/<uuid:pk>/assign/', LeadAssignView.as_view(), name='crm-lead-assign'),
    path('leads/<uuid:pk>/stage', LeadStageTransitionView.as_view(), name='crm-lead-stage-noslash'),
    path('leads/<uuid:pk>/stage/', LeadStageTransitionView.as_view(), name='crm-lead-stage'),
    path('leads/<uuid:pk>/tags', LeadTagsView.as_view(), name='crm-lead-tags-noslash'),
    path('leads/<uuid:pk>/tags/', LeadTagsView.as_view(), name='crm-lead-tags'),

    # Customers
    path('customers', CustomerListCreateView.as_view(), name='crm-customer-list-create-noslash'),
    path('customers/', CustomerListCreateView.as_view(), name='crm-customer-list-create'),
    path('customers/<uuid:pk>', CustomerDetailView.as_view(), name='crm-customer-detail-noslash'),
    path('customers/<uuid:pk>/', CustomerDetailView.as_view(), name='crm-customer-detail'),
    path('customers/<uuid:pk>/360', Customer360View.as_view(), name='crm-customer-360-noslash'),
    path('customers/<uuid:pk>/360/', Customer360View.as_view(), name='crm-customer-360'),
    path('customers/<uuid:pk>/conversations', CustomerConversationsView.as_view(), name='crm-customer-conversations-noslash'),
    path('customers/<uuid:pk>/conversations/', CustomerConversationsView.as_view(), name='crm-customer-conversations'),
    path('customers/<uuid:pk>/activities', CustomerActivitiesView.as_view(), name='crm-customer-activities-noslash'),
    path('customers/<uuid:pk>/activities/', CustomerActivitiesView.as_view(), name='crm-customer-activities'),
    path('customers/<uuid:pk>/notes', CustomerNotesView.as_view(), name='crm-customer-notes-noslash'),
    path('customers/<uuid:pk>/notes/', CustomerNotesView.as_view(), name='crm-customer-notes'),
    path('customers/merge', CustomerMergeView.as_view(), name='crm-customer-merge-noslash'),
    path('customers/merge/', CustomerMergeView.as_view(), name='crm-customer-merge'),

    # CRM Global Search
    path('crm/search', CrmSearchView.as_view(), name='crm-search-noslash'),
    path('crm/search/', CrmSearchView.as_view(), name='crm-search'),

    # Pipelines & Stages
    path('crm/pipelines', PipelineListCreateView.as_view(), name='crm-pipeline-list-create-noslash'),
    path('crm/pipelines/', PipelineListCreateView.as_view(), name='crm-pipeline-list-create'),
    path('crm/pipelines/<uuid:pk>', PipelineDetailView.as_view(), name='crm-pipeline-detail-noslash'),
    path('crm/pipelines/<uuid:pk>/', PipelineDetailView.as_view(), name='crm-pipeline-detail'),
    path('crm/pipelines/<uuid:pipeline_id>/stages', PipelineStageListCreateView.as_view(), name='crm-pipeline-stages-noslash'),
    path('crm/pipelines/<uuid:pipeline_id>/stages/', PipelineStageListCreateView.as_view(), name='crm-pipeline-stages'),
    path('crm/stages/<uuid:pk>', PipelineStageDetailView.as_view(), name='crm-stage-detail-noslash'),
    path('crm/stages/<uuid:pk>/', PipelineStageDetailView.as_view(), name='crm-stage-detail'),

    # Tags
    path('crm/tags', TagListCreateView.as_view(), name='crm-tags-list-create-noslash'),
    path('crm/tags/', TagListCreateView.as_view(), name='crm-tags-list-create'),
    path('crm/tags/<uuid:pk>', TagDetailView.as_view(), name='crm-tags-detail-noslash'),
    path('crm/tags/<uuid:pk>/', TagDetailView.as_view(), name='crm-tags-detail'),

    # Custom Fields
    path('crm/custom-fields', CustomFieldDefinitionListCreateView.as_view(), name='crm-custom-fields-list-create-noslash'),
    path('crm/custom-fields/', CustomFieldDefinitionListCreateView.as_view(), name='crm-custom-fields-list-create'),
    path('crm/custom-fields/<uuid:pk>', CustomFieldDefinitionDetailView.as_view(), name='crm-custom-fields-detail-noslash'),
    path('crm/custom-fields/<uuid:pk>/', CustomFieldDefinitionDetailView.as_view(), name='crm-custom-fields-detail'),
]
