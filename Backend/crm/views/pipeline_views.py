import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from crm.models import Pipeline, PipelineStage
from crm.serializers import PipelineSerializer, PipelineStageSerializer
from crm.services.pipeline_service import PipelineService
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class PipelineListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = require_request_tenant(request)
        PipelineService.ensure_default_pipeline(tenant)
        pipelines = Pipeline.objects.filter(tenant=tenant, is_active=True).prefetch_related('stages')
        serializer = PipelineSerializer(pipelines, many=True)
        return Response(serializer.data)

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'pipeline.manage')):
            raise PermissionDenied("You do not have permission to manage pipelines.")

        name = request.data.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Pipeline name is required.'})

        pipeline = Pipeline.objects.create(
            tenant=tenant,
            name=name,
            description=request.data.get('description', ''),
            is_default=bool(request.data.get('is_default', False)),
            display_order=request.data.get('display_order', 0),
        )
        if pipeline.is_default:
            Pipeline.objects.filter(tenant=tenant).exclude(pipeline_id=pipeline.pipeline_id).update(is_default=False)

        serializer = PipelineSerializer(pipeline)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PipelineDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_pipeline(self, request, pk):
        tenant = require_request_tenant(request)
        pipeline = Pipeline.objects.filter(tenant=tenant, pipeline_id=pk).prefetch_related('stages').first()
        if not pipeline:
            raise NotFound({'detail': 'Pipeline not found.', 'code': 'PIPELINE_NOT_FOUND'})
        return tenant, pipeline

    def get(self, request, pk):
        tenant, pipeline = self._get_pipeline(request, pk)
        serializer = PipelineSerializer(pipeline)
        return Response(serializer.data)

    def patch(self, request, pk):
        tenant, pipeline = self._get_pipeline(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'pipeline.manage')):
            raise PermissionDenied("You do not have permission to manage pipelines.")

        if 'name' in request.data:
            pipeline.name = request.data['name']
        if 'description' in request.data:
            pipeline.description = request.data['description']
        if 'is_default' in request.data:
            pipeline.is_default = bool(request.data['is_default'])
            if pipeline.is_default:
                Pipeline.objects.filter(tenant=tenant).exclude(pipeline_id=pipeline.pipeline_id).update(is_default=False)
        if 'display_order' in request.data:
            pipeline.display_order = request.data['display_order']
        if 'is_active' in request.data:
            pipeline.is_active = bool(request.data['is_active'])

        pipeline.save()
        serializer = PipelineSerializer(pipeline)
        return Response(serializer.data)


class PipelineStageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pipeline_id):
        tenant = require_request_tenant(request)
        stages = PipelineStage.objects.filter(tenant=tenant, pipeline_id=pipeline_id, is_active=True).order_by('display_order')
        serializer = PipelineStageSerializer(stages, many=True)
        return Response(serializer.data)

    def post(self, request, pipeline_id):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'pipeline.manage')):
            raise PermissionDenied("You do not have permission to manage pipeline stages.")

        pipeline = Pipeline.objects.filter(tenant=tenant, pipeline_id=pipeline_id).first()
        if not pipeline:
            raise NotFound({'detail': 'Pipeline not found.', 'code': 'PIPELINE_NOT_FOUND'})

        name = request.data.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Stage name is required.'})

        stage = PipelineStage.objects.create(
            tenant=tenant,
            pipeline=pipeline,
            name=name,
            description=request.data.get('description', ''),
            display_order=request.data.get('display_order', 0),
            classification=request.data.get('classification', 'OPEN'),
            color=request.data.get('color', '#3b82f6'),
            is_terminal=bool(request.data.get('is_terminal', False)),
        )

        serializer = PipelineStageSerializer(stage)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PipelineStageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'pipeline.manage')):
            raise PermissionDenied("You do not have permission to manage pipeline stages.")

        stage = PipelineStage.objects.filter(tenant=tenant, stage_id=pk).first()
        if not stage:
            raise NotFound({'detail': 'Stage not found.', 'code': 'INVALID_STAGE_TRANSITION'})

        if 'name' in request.data:
            stage.name = request.data['name']
        if 'description' in request.data:
            stage.description = request.data['description']
        if 'display_order' in request.data:
            stage.display_order = request.data['display_order']
        if 'classification' in request.data:
            stage.classification = request.data['classification']
        if 'color' in request.data:
            stage.color = request.data['color']
        if 'is_terminal' in request.data:
            stage.is_terminal = bool(request.data['is_terminal'])
        if 'is_active' in request.data:
            stage.is_active = bool(request.data['is_active'])

        stage.save()
        serializer = PipelineStageSerializer(stage)
        return Response(serializer.data)
