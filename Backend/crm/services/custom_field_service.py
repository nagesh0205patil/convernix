import re
import logging
from typing import Any, Dict, List, Optional
from django.db import transaction
from rest_framework.exceptions import ValidationError
from crm.models import CustomFieldDefinition, CustomFieldValue
from organization.services.crypto_service import encrypt_tenant_data

logger = logging.getLogger(__name__)


class CustomFieldService:
    @classmethod
    def validate_value(cls, definition: CustomFieldDefinition, raw_value: Any) -> Any:
        """
        Validates a value against the field definition's type and rules.
        """
        if raw_value is None or raw_value == '':
            if definition.is_required:
                raise ValidationError({definition.field_name: f'{definition.field_label} is required.', 'code': 'INVALID_CUSTOM_FIELD'})
            return None

        ftype = definition.field_type

        if ftype in ('NUMBER',):
            try:
                return int(raw_value)
            except (ValueError, TypeError):
                raise ValidationError({definition.field_name: f'{definition.field_label} must be a valid integer.', 'code': 'INVALID_CUSTOM_FIELD'})

        elif ftype in ('DECIMAL',):
            try:
                return float(raw_value)
            except (ValueError, TypeError):
                raise ValidationError({definition.field_name: f'{definition.field_label} must be a valid number.', 'code': 'INVALID_CUSTOM_FIELD'})

        elif ftype in ('BOOLEAN',):
            if isinstance(raw_value, bool):
                return raw_value
            if str(raw_value).lower() in ('true', '1', 'yes'):
                return True
            if str(raw_value).lower() in ('false', '0', 'no'):
                return False
            raise ValidationError({definition.field_name: f'{definition.field_label} must be true or false.', 'code': 'INVALID_CUSTOM_FIELD'})

        elif ftype in ('EMAIL',):
            val = str(raw_value).strip().lower()
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', val):
                raise ValidationError({definition.field_name: f'{definition.field_label} must be a valid email address.', 'code': 'INVALID_CUSTOM_FIELD'})
            return val

        elif ftype in ('PHONE',):
            val = re.sub(r'[^0-9+]', '', str(raw_value).strip())
            if len(val) < 7:
                raise ValidationError({definition.field_name: f'{definition.field_label} must be a valid phone number.', 'code': 'INVALID_CUSTOM_FIELD'})
            return val

        elif ftype in ('SELECT',):
            val = str(raw_value).strip()
            allowed = [str(opt) for opt in (definition.options or [])]
            if allowed and val not in allowed:
                raise ValidationError({definition.field_name: f'Value "{val}" is not one of the allowed options.', 'code': 'INVALID_CUSTOM_FIELD'})
            return val

        elif ftype in ('MULTI_SELECT',):
            if isinstance(raw_value, list):
                val_list = [str(x) for x in raw_value]
            else:
                val_list = [str(raw_value)]
            allowed = [str(opt) for opt in (definition.options or [])]
            if allowed:
                invalid = [x for x in val_list if x not in allowed]
                if invalid:
                    raise ValidationError({definition.field_name: f'Invalid options: {invalid}', 'code': 'INVALID_CUSTOM_FIELD'})
            return val_list

        return str(raw_value)

    @classmethod
    @transaction.atomic
    def save_custom_field_values(
        cls,
        tenant,
        entity,
        values_dict: Dict[str, Any],
        actor_user=None,
    ) -> List[CustomFieldValue]:
        """
        Validates, encrypts sensitive attributes, and saves custom field values for Customer or Lead.
        """
        from crm.models import Customer, Lead
        is_customer = isinstance(entity, Customer)
        entity_type = 'CUSTOMER' if is_customer else 'LEAD'

        definitions = {
            defn.field_name: defn
            for defn in CustomFieldDefinition.objects.filter(tenant=tenant, entity_type=entity_type, is_active=True)
        }

        saved_records = []
        for field_name, raw_val in values_dict.items():
            if field_name not in definitions:
                continue
            defn = definitions[field_name]
            clean_val = cls.validate_value(defn, raw_val)

            cfv_kwargs = {
                'tenant': tenant,
                'definition': defn,
                'customer': entity if is_customer else None,
                'lead': entity if not is_customer else None,
            }

            cfv = CustomFieldValue.objects.filter(**cfv_kwargs).first()
            if not cfv:
                cfv = CustomFieldValue(**cfv_kwargs)

            if defn.is_sensitive_pii and clean_val is not None:
                cfv.value_encrypted = encrypt_tenant_data(tenant, str(clean_val))
                cfv.value_text = ''
                cfv.value_json = None
            elif isinstance(clean_val, (dict, list, bool)):
                cfv.value_json = clean_val
                cfv.value_text = str(clean_val)
                cfv.value_encrypted = ''
            else:
                cfv.value_text = str(clean_val) if clean_val is not None else ''
                cfv.value_json = None
                cfv.value_encrypted = ''

            cfv.save()
            saved_records.append(cfv)

        return saved_records
