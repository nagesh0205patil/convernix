from django.urls import path
from .views import (
    ConversationListCreateView, ConversationDetailView,
    ConversationClaimView, ConversationAssignView,
    ConversationUnassignView, ConversationTransferView,
    ConversationResolveView, ConversationReopenView,
    ConversationReadView, ConversationMessagesListView,
    ConversationSendMessageView, ConversationCreateNoteView,
    MessageRetryView, MentionListView, MentionMarkReadView,
    AttachmentDownloadView, DepartmentQueueListView, TagListView,
    InboxSSEView,
)

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='inbox-conversation-list'),
    path('conversations/<int:id>/', ConversationDetailView.as_view(), name='inbox-conversation-detail'),
    path('conversations/<int:id>/claim/', ConversationClaimView.as_view(), name='inbox-conversation-claim'),
    path('conversations/<int:id>/assign/', ConversationAssignView.as_view(), name='inbox-conversation-assign'),
    path('conversations/<int:id>/unassign/', ConversationUnassignView.as_view(), name='inbox-conversation-unassign'),
    path('conversations/<int:id>/transfer/', ConversationTransferView.as_view(), name='inbox-conversation-transfer'),
    path('conversations/<int:id>/resolve/', ConversationResolveView.as_view(), name='inbox-conversation-resolve'),
    path('conversations/<int:id>/reopen/', ConversationReopenView.as_view(), name='inbox-conversation-reopen'),
    path('conversations/<int:id>/read/', ConversationReadView.as_view(), name='inbox-conversation-read'),
    path('conversations/<int:id>/messages/', ConversationMessagesListView.as_view(), name='inbox-conversation-messages'),
    path('conversations/<int:id>/messages/send/', ConversationSendMessageView.as_view(), name='inbox-conversation-messages-send'),
    path('conversations/<int:id>/notes/', ConversationCreateNoteView.as_view(), name='inbox-conversation-notes'),
    path('messages/<int:id>/retry/', MessageRetryView.as_view(), name='inbox-message-retry'),
    path('mentions/', MentionListView.as_view(), name='inbox-mentions-list'),
    path('mentions/<int:id>/read/', MentionMarkReadView.as_view(), name='inbox-mentions-read'),
    path('attachments/<int:id>/download/', AttachmentDownloadView.as_view(), name='inbox-attachment-download'),
    path('departments/', DepartmentQueueListView.as_view(), name='inbox-departments-queue'),
    path('tags/', TagListView.as_view(), name='inbox-tags-list'),
    path('events/', InboxSSEView.as_view(), name='inbox-sse-events'),
]

