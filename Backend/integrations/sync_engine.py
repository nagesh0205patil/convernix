import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
from django.utils import timezone
from .models import (
    ConnectorInstance,
    ConnectorFieldMapping,
    ConnectorObjectMapping,
    ConnectorSyncJob,
    ConnectorSyncRecord,
)

logger = logging.getLogger(__name__)


def apply_transformation(raw_val: Any, transform_type: str, config: Dict[str, Any]) -> Any:
    """Transforms a single field value according to configured transformation rules."""
    if raw_val is None:
        return config.get('default', None)

    if transform_type == 'direct':
        return raw_val

    elif transform_type == 'enum_map':
        mapping_dict = config.get('mapping', {})
        str_val = str(raw_val)
        return mapping_dict.get(str_val, config.get('default', str_val))

    elif transform_type == 'default_value':
        return raw_val if raw_val not in (None, '', []) else config.get('default')

    elif transform_type == 'boolean_cast':
        if isinstance(raw_val, bool):
            return raw_val
        str_val = str(raw_val).strip().lower()
        return str_val in ('true', '1', 'yes', 'y', 't')

    elif transform_type == 'number_cast':
        try:
            return float(raw_val) if '.' in str(raw_val) else int(raw_val)
        except (ValueError, TypeError):
            return config.get('default', 0)

    elif transform_type == 'date_format':
        fmt = config.get('format', '%Y-%m-%dT%H:%M:%SZ')
        if isinstance(raw_val, (datetime.datetime, datetime.date)):
            return raw_val.strftime(fmt)
        return str(raw_val)

    return raw_val


def transform_convernix_to_external(instance: ConnectorInstance, object_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Applies configured field mappings to translate Convernix payload into external schema."""
    mappings = ConnectorFieldMapping.objects.filter(
        connector_instance=instance,
        object_type=object_type,
        is_active=True,
    )

    if not mappings.exists():
        # Default pass-through if no explicit mappings customized
        return dict(data)

    output = {}
    for mapping in mappings:
        cvx_field = mapping.convernix_field
        ext_field = mapping.external_field
        val = data.get(cvx_field)

        transformed = apply_transformation(val, mapping.transformation_type, mapping.transformation_config)
        output[ext_field] = transformed

    return output


def sync_object_push(
    instance: ConnectorInstance,
    object_type: str,
    convernix_object_id: str,
    convernix_data: Dict[str, Any],
    job: Optional[ConnectorSyncJob] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Pushes an individual Convernix entity to the external system, checking object mapping and conflict strategy.
    """
    from .connectors.registry import get_connector_instance_handler
    handler = get_connector_instance_handler(instance)
    if not handler:
        return False, None, f"No handler registered for connector {instance.connector_key}"

    # Check for existing object mapping
    obj_mapping = ConnectorObjectMapping.objects.filter(
        tenant=instance.tenant,
        connector_instance=instance,
        object_type=object_type,
        convernix_object_id=convernix_object_id,
    ).first()

    external_id = obj_mapping.external_object_id if obj_mapping else None

    # Check conflict strategy
    if obj_mapping and instance.conflict_strategy == 'manual':
        if job:
            ConnectorSyncRecord.objects.create(
                sync_job=job,
                tenant=instance.tenant,
                object_type=object_type,
                convernix_object_id=convernix_object_id,
                external_object_id=external_id or '',
                action='conflict',
                conflict_strategy='manual',
                error_message='Manual resolution required prior to push overwrite.',
            )
        return False, external_id, "Manual resolution required"

    success, new_ext_id, err = handler.push(object_type, convernix_data, external_id=external_id)

    if success and new_ext_id:
        if not obj_mapping:
            ConnectorObjectMapping.objects.create(
                tenant=instance.tenant,
                connector_instance=instance,
                object_type=object_type,
                convernix_object_id=convernix_object_id,
                external_object_id=new_ext_id,
            )
        else:
            obj_mapping.external_object_id = new_ext_id
            obj_mapping.save(update_fields=['external_object_id', 'last_synced_at'])

        if job:
            ConnectorSyncRecord.objects.create(
                sync_job=job,
                tenant=instance.tenant,
                object_type=object_type,
                convernix_object_id=convernix_object_id,
                external_object_id=new_ext_id,
                action='updated' if obj_mapping else 'created',
                conflict_strategy=instance.conflict_strategy,
            )
        return True, new_ext_id, None

    if job:
        ConnectorSyncRecord.objects.create(
            sync_job=job,
            tenant=instance.tenant,
            object_type=object_type,
            convernix_object_id=convernix_object_id,
            external_object_id=external_id or '',
            action='failed',
            error_message=err or 'Push failed',
        )
    return False, external_id, err

