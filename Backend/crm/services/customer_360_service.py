import logging
from typing import Any, Dict, List, Optional
from crm.models import Customer, Lead, Activity, Note, CustomerTag, CustomFieldValue
from users.permissions import has_tenant_permission
from organization.services.masking_service import MaskingService

logger = logging.getLogger(__name__)


class Customer360Service:
    @classmethod
    def get_customer_360(cls, tenant, customer: Customer, user) -> Dict[str, Any]:
        """
        Aggregates complete Customer 360 view for a customer contact:
        - Customer profile (masked or unmasked according to customer.view_pii permission)
        - Current & historical leads with stages and owners
        - Inbox conversation history threads
        - CRM activity timeline
        - Notes
        - Custom fields
        - Tags
        - Attachments
        """
        can_view_pii = has_tenant_permission(user, tenant, 'customer.view_pii') or user.is_superuser

        # 1. Profile information
        plain_phone = customer.plain_phone
        plain_email = customer.plain_email
        masked_phone = MaskingService.mask_phone(plain_phone)
        masked_email = MaskingService.mask_email(plain_email)

        profile = {
            'customer_id': str(customer.customer_id),
            'display_name': customer.display_name or customer.plain_full_name,
            'first_name': customer.plain_first_name if can_view_pii else '',
            'last_name': customer.plain_last_name if can_view_pii else '',
            'phone': plain_phone if can_view_pii else masked_phone,
            'email': plain_email if can_view_pii else masked_email,
            'is_pii_unmasked': can_view_pii,
            'status': customer.status,
            'source': customer.source,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat(),
            'version': customer.version,
        }

        # 2. Leads (Current & Historical)
        leads_qs = Lead.objects.filter(
            tenant=tenant,
            customer=customer,
            deleted_at__isnull=True,
        ).select_related('pipeline', 'stage', 'department', 'owner_user').prefetch_related('lead_tags__tag').order_by('-created_at')

        current_leads = []
        historical_leads = []
        for lead in leads_qs:
            lead_summary = {
                'lead_id': str(lead.lead_id),
                'title': lead.title,
                'status': lead.status,
                'priority': lead.priority,
                'estimated_value': float(lead.estimated_value) if lead.estimated_value else None,
                'currency': lead.currency,
                'win_probability': lead.win_probability,
                'pipeline': {
                    'id': str(lead.pipeline.pipeline_id),
                    'name': lead.pipeline.name,
                },
                'stage': {
                    'id': str(lead.stage.stage_id),
                    'name': lead.stage.name,
                    'classification': lead.stage.classification,
                    'color': lead.stage.color,
                    'is_terminal': lead.stage.is_terminal,
                },
                'department': {
                    'id': lead.department.id,
                    'name': lead.department.name,
                } if lead.department else None,
                'owner': {
                    'id': lead.owner_user.id,
                    'name': getattr(lead.owner_user, 'get_full_name', lambda: '')() or lead.owner_user.email,
                    'email': lead.owner_user.email,
                } if lead.owner_user else None,
                'tags': [{'id': str(lt.tag.tag_id), 'name': lt.tag.name, 'color': lt.tag.color} for lt in lead.lead_tags.all()],
                'created_at': lead.created_at.isoformat(),
                'closed_at': lead.closed_at.isoformat() if lead.closed_at else None,
                'version': lead.version,
            }
            if lead.status == 'OPEN':
                current_leads.append(lead_summary)
            else:
                historical_leads.append(lead_summary)

        # 3. Conversations (Source of truth: Inbox Conversation service)
        conversations = []
        attachments = []
        if customer.legacy_whatsapp_customer:
            from inbox.models import Conversation, MessageAttachment
            inbox_convs = Conversation.objects.filter(
                tenant=tenant,
                contact=customer.legacy_whatsapp_customer,
            ).select_related('department', 'assigned_user').prefetch_related('messages').order_by('-last_message_at')[:10]

            for conv in inbox_convs:
                conversations.append({
                    'conversation_id': conv.id,
                    'status': conv.status,
                    'priority': conv.priority,
                    'department': conv.department.name if conv.department else None,
                    'assigned_user': conv.assigned_user.email if conv.assigned_user else None,
                    'last_message_preview': conv.plain_last_message_preview,
                    'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
                })

            conv_ids = [c.id for c in inbox_convs]
            conv_attachments = MessageAttachment.objects.filter(
                tenant=tenant,
                message__conversation_id__in=conv_ids,
            ).select_related('message')[:20]

            for att in conv_attachments:
                attachments.append({
                    'id': att.id,
                    'filename': att.filename,
                    'content_type': att.content_type,
                    'file_size': att.file_size,
                    'created_at': att.created_at.isoformat(),
                    'message_id': att.message.id if att.message else None,
                })

        # 4. Activities Timeline
        activities_qs = Activity.objects.filter(
            tenant=tenant,
            customer=customer,
        ).order_by('-created_at')[:50]

        activities = [
            {
                'activity_id': str(act.activity_id),
                'lead_id': str(act.lead_id) if act.lead_id else None,
                'activity_type': act.activity_type,
                'title': act.title,
                'description': act.description,
                'actor_name': act.actor_name,
                'metadata': act.metadata,
                'created_at': act.created_at.isoformat(),
            }
            for act in activities_qs
        ]

        # 5. Notes (Encrypted at rest, decrypted for authorized user)
        notes_qs = Note.objects.filter(
            tenant=tenant,
            customer=customer,
        ).select_related('author_user').order_by('-is_pinned', '-created_at')

        notes = [
            {
                'note_id': str(n.note_id),
                'lead_id': str(n.lead_id) if n.lead_id else None,
                'content': n.plain_content,
                'is_pinned': n.is_pinned,
                'author': {
                    'id': n.author_user.id,
                    'name': getattr(n.author_user, 'get_full_name', lambda: '')() or n.author_user.email,
                },
                'created_at': n.created_at.isoformat(),
                'updated_at': n.updated_at.isoformat(),
            }
            for n in notes_qs
        ]

        # 6. Tags
        tags = [
            {
                'tag_id': str(ct.tag.tag_id),
                'name': ct.tag.name,
                'color': ct.tag.color,
            }
            for ct in CustomerTag.objects.filter(customer=customer).select_related('tag')
        ]

        # 7. Custom Fields
        custom_fields = []
        for cfv in CustomFieldValue.objects.filter(customer=customer).select_related('definition'):
            custom_fields.append({
                'field_id': str(cfv.definition.field_id),
                'field_name': cfv.definition.field_name,
                'field_label': cfv.definition.field_label,
                'field_type': cfv.definition.field_type,
                'value': cfv.get_plain_value(),
            })

        return {
            'profile': profile,
            'current_leads': current_leads,
            'historical_leads': historical_leads,
            'conversations': conversations,
            'activities': activities,
            'notes': notes,
            'attachments': attachments,
            'tags': tags,
            'custom_fields': custom_fields,
        }
