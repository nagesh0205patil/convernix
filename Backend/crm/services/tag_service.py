import logging
from typing import List
from django.db import transaction
from crm.models import Tag, CustomerTag, LeadTag, Customer, Lead
from crm.services.activity_service import ActivityService
from organization.services.event_service import publish_domain_event
from integrations.outbox import emit_outbox_event

logger = logging.getLogger(__name__)


class TagService:
    @classmethod
    @transaction.atomic
    def sync_lead_tags(cls, lead: Lead, tag_names: List[str], actor_user=None) -> List[Tag]:
        """
        Synchronizes tags assigned to a lead, creating any missing tags in tenant scope,
        and emitting activities and events for additions and removals.
        """
        tenant = lead.tenant
        cleaned_names = [t.strip() for t in tag_names if t and t.strip()]

        current_lead_tags = LeadTag.objects.filter(lead=lead).select_related('tag')
        current_tag_map = {lt.tag.name: lt for lt in current_lead_tags}
        current_names = set(current_tag_map.keys())
        target_names = set(cleaned_names)

        # Removed tags
        for removed_name in (current_names - target_names):
            lt = current_tag_map[removed_name]
            lt.delete()
            ActivityService.log_activity(
                tenant=tenant,
                customer=lead.customer,
                lead=lead,
                activity_type='TAG_REMOVED',
                title=f'Tag "{removed_name}" removed',
                actor_user=actor_user,
            )
            event_payload = {'lead_id': str(lead.lead_id), 'tag_name': removed_name}
            try:
                publish_domain_event(event_type='crm.tag.removed', tenant_id=tenant.id, data=event_payload)
                emit_outbox_event(tenant=tenant, event_type='crm.tag.removed', payload=event_payload)
            except Exception:
                pass

        # Added tags
        result_tags = []
        for name in cleaned_names:
            tag, _ = Tag.objects.get_or_create(tenant=tenant, name=name, defaults={'color': '#6366f1'})
            result_tags.append(tag)
            if name not in current_names:
                LeadTag.objects.create(tenant=tenant, lead=lead, tag=tag, tagged_by=actor_user)
                ActivityService.log_activity(
                    tenant=tenant,
                    customer=lead.customer,
                    lead=lead,
                    activity_type='TAG_ADDED',
                    title=f'Tag "{name}" added',
                    actor_user=actor_user,
                )
                event_payload = {'lead_id': str(lead.lead_id), 'tag_name': name}
                try:
                    publish_domain_event(event_type='crm.tag.added', tenant_id=tenant.id, data=event_payload)
                    emit_outbox_event(tenant=tenant, event_type='crm.tag.added', payload=event_payload)
                except Exception:
                    pass

        return result_tags

    @classmethod
    @transaction.atomic
    def sync_customer_tags(cls, customer: Customer, tag_names: List[str], actor_user=None) -> List[Tag]:
        """
        Synchronizes tags assigned to a customer.
        """
        tenant = customer.tenant
        cleaned_names = [t.strip() for t in tag_names if t and t.strip()]

        current_customer_tags = CustomerTag.objects.filter(customer=customer).select_related('tag')
        current_tag_map = {ct.tag.name: ct for ct in current_customer_tags}
        current_names = set(current_tag_map.keys())
        target_names = set(cleaned_names)

        # Removed tags
        for removed_name in (current_names - target_names):
            ct = current_tag_map[removed_name]
            ct.delete()
            ActivityService.log_activity(
                tenant=tenant,
                customer=customer,
                activity_type='TAG_REMOVED',
                title=f'Customer Tag "{removed_name}" removed',
                actor_user=actor_user,
            )

        # Added tags
        result_tags = []
        for name in cleaned_names:
            tag, _ = Tag.objects.get_or_create(tenant=tenant, name=name, defaults={'color': '#10b981'})
            result_tags.append(tag)
            if name not in current_names:
                CustomerTag.objects.create(tenant=tenant, customer=customer, tag=tag, tagged_by=actor_user)
                ActivityService.log_activity(
                    tenant=tenant,
                    customer=customer,
                    activity_type='TAG_ADDED',
                    title=f'Customer Tag "{name}" added',
                    actor_user=actor_user,
                )

        return result_tags
