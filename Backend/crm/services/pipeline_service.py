import logging
from typing import List, Optional
from django.db import transaction
from crm.models import Pipeline, PipelineStage

logger = logging.getLogger(__name__)

DEFAULT_STAGES = [
    {'name': 'New', 'classification': 'OPEN', 'color': '#3b82f6', 'display_order': 0, 'is_terminal': False},
    {'name': 'Contacted', 'classification': 'OPEN', 'color': '#6366f1', 'display_order': 1, 'is_terminal': False},
    {'name': 'Qualified', 'classification': 'OPEN', 'color': '#8b5cf6', 'display_order': 2, 'is_terminal': False},
    {'name': 'Proposal Sent', 'classification': 'OPEN', 'color': '#ec4899', 'display_order': 3, 'is_terminal': False},
    {'name': 'Negotiation', 'classification': 'OPEN', 'color': '#f59e0b', 'display_order': 4, 'is_terminal': False},
    {'name': 'Won', 'classification': 'WON', 'color': '#10b981', 'display_order': 5, 'is_terminal': True},
    {'name': 'Lost', 'classification': 'LOST', 'color': '#ef4444', 'display_order': 6, 'is_terminal': True},
]


class PipelineService:
    @classmethod
    @transaction.atomic
    def ensure_default_pipeline(cls, tenant) -> Pipeline:
        """
        Ensures tenant has at least one active default sales pipeline with standard stages.
        """
        pipeline = Pipeline.objects.filter(tenant=tenant, is_default=True).first()
        if not pipeline:
            pipeline = Pipeline.objects.filter(tenant=tenant).first()

        if not pipeline:
            pipeline = Pipeline.objects.create(
                tenant=tenant,
                name='Sales Pipeline',
                description='Default sales and enquiry pipeline',
                is_default=True,
                is_active=True,
                display_order=0,
            )

        # Ensure standard stages exist
        existing_stage_names = set(pipeline.stages.values_list('name', flat=True))
        stages_to_create = []
        for defn in DEFAULT_STAGES:
            if defn['name'] not in existing_stage_names:
                stages_to_create.append(
                    PipelineStage(
                        tenant=tenant,
                        pipeline=pipeline,
                        name=defn['name'],
                        classification=defn['classification'],
                        color=defn['color'],
                        display_order=defn['display_order'],
                        is_terminal=defn['is_terminal'],
                        is_active=True,
                    )
                )
        if stages_to_create:
            PipelineStage.objects.bulk_create(stages_to_create)

        return pipeline

    @classmethod
    def get_initial_stage(cls, pipeline: Pipeline) -> PipelineStage:
        """Retrieves the first active, non-terminal stage of a pipeline."""
        stage = pipeline.stages.filter(is_active=True, is_terminal=False).order_by('display_order').first()
        if not stage:
            stage = pipeline.stages.filter(is_active=True).order_by('display_order').first()
        return stage
