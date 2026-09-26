"""
Centralized Data Classification & Record of Processing Activities (ROPA) Registry.
Supports compliance readiness for ISO/IEC 27001, ISO/IEC 27701, SOC 2, and India's DPDP Act 2023.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataCategory(str, Enum):
    PUBLIC = 'PUBLIC'
    INTERNAL = 'INTERNAL'
    CONFIDENTIAL = 'CONFIDENTIAL'
    PERSONAL_DATA = 'PERSONAL_DATA'
    HIGHLY_SENSITIVE = 'HIGHLY_SENSITIVE'
    SECRET = 'SECRET'


class EncryptionRequirement(str, Enum):
    NONE = 'NONE'
    AES_256_GCM = 'AES_256_GCM'
    KMS_ENVELOPE = 'KMS_ENVELOPE'
    PASSWORD_HASH = 'PASSWORD_HASH'
    BLIND_INDEX_HMAC = 'BLIND_INDEX_HMAC'


class MaskingRequirement(str, Enum):
    NONE = 'NONE'
    PARTIAL = 'PARTIAL'  # e.g., +91 ******3210
    REDACTED = 'REDACTED'  # e.g., [REDACTED]
    WRITE_ONLY = 'WRITE_ONLY'  # never returned in API


@dataclass
class FieldClassification:
    model_name: str
    field_name: str
    category: DataCategory
    purpose: str
    encryption: EncryptionRequirement
    masking: MaskingRequirement
    retention_category: str
    exportable: bool
    deletion_behavior: str
    audit_requirement: str
    legal_basis_default: str = 'LEGITIMATE_BUSINESS_INTEREST'


DATA_CLASSIFICATION_CATALOG: List[FieldClassification] = [
    # Customer model (PII)
    FieldClassification(
        model_name='Customer',
        field_name='full_name',
        category=DataCategory.PERSONAL_DATA,
        purpose='Customer identification and routing communication',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.NONE,
        retention_category='LEADS',
        exportable=True,
        deletion_behavior='ANONYMIZE_OR_DELETE',
        audit_requirement='LEAD_VIEWED',
        legal_basis_default='CONSENT_OR_CONTRACT',
    ),
    FieldClassification(
        model_name='Customer',
        field_name='whatsapp_number',
        category=DataCategory.PERSONAL_DATA,
        purpose='Direct messaging and enquiry resolution via WhatsApp Cloud API',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.PARTIAL,
        retention_category='LEADS',
        exportable=True,
        deletion_behavior='ANONYMIZE_OR_DELETE',
        audit_requirement='PHONE_REVEALED',
        legal_basis_default='CONSENT_OR_CONTRACT',
    ),
    FieldClassification(
        model_name='Customer',
        field_name='email',
        category=DataCategory.PERSONAL_DATA,
        purpose='Direct customer follow-up and communication',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.PARTIAL,
        retention_category='LEADS',
        exportable=True,
        deletion_behavior='ANONYMIZE_OR_DELETE',
        audit_requirement='CUSTOMER_EMAIL_REVEALED',
        legal_basis_default='CONSENT_OR_CONTRACT',
    ),
    FieldClassification(
        model_name='Customer',
        field_name='organization_name',
        category=DataCategory.CONFIDENTIAL,
        purpose='Business client relationship management',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.NONE,
        retention_category='LEADS',
        exportable=True,
        deletion_behavior='ANONYMIZE_OR_DELETE',
        audit_requirement='LEAD_VIEWED',
    ),

    # Enquiry & WhatsApp Messages
    FieldClassification(
        model_name='Enquiry',
        field_name='message',
        category=DataCategory.CONFIDENTIAL,
        purpose='Inbound customer inquiry processing and departmental routing',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.NONE,
        retention_category='CONVERSATIONS',
        exportable=True,
        deletion_behavior='CASCADE_OR_ANONYMIZE',
        audit_requirement='CONVERSATION_VIEWED',
    ),
    FieldClassification(
        model_name='WhatsAppMessage',
        field_name='content',
        category=DataCategory.CONFIDENTIAL,
        purpose='Omnichannel communication transcript history',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.NONE,
        retention_category='CONVERSATIONS',
        exportable=True,
        deletion_behavior='CASCADE_DELETE',
        audit_requirement='CONVERSATION_VIEWED',
    ),
    FieldClassification(
        model_name='WhatsAppMessage',
        field_name='attachment',
        category=DataCategory.CONFIDENTIAL,
        purpose='User and agent file attachments for support/sales resolution',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.NONE,
        retention_category='ATTACHMENTS',
        exportable=True,
        deletion_behavior='PURGE_FROM_STORAGE',
        audit_requirement='ATTACHMENT_DOWNLOADED',
    ),

    # Authentication & Secrets
    FieldClassification(
        model_name='User',
        field_name='password',
        category=DataCategory.SECRET,
        purpose='User authentication to Convernix SaaS platform',
        encryption=EncryptionRequirement.PASSWORD_HASH,
        masking=MaskingRequirement.WRITE_ONLY,
        retention_category='USERS',
        exportable=False,
        deletion_behavior='PURGE_ON_USER_DELETE',
        audit_requirement='LOGIN_ATTEMPT',
    ),
    FieldClassification(
        model_name='TenantKeyMetadata',
        field_name='wrapped_dek',
        category=DataCategory.SECRET,
        purpose='Envelope encryption of tenant PII and confidential records',
        encryption=EncryptionRequirement.KMS_ENVELOPE,
        masking=MaskingRequirement.WRITE_ONLY,
        retention_category='SYSTEM',
        exportable=False,
        deletion_behavior='DESTROY_ON_TENANT_PURGE',
        audit_requirement='KEY_PROVISIONED_OR_ROTATED',
    ),
    FieldClassification(
        model_name='WhatsAppConfiguration',
        field_name='meta_access_token',
        category=DataCategory.SECRET,
        purpose='Meta WhatsApp Cloud API authorization',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.WRITE_ONLY,
        retention_category='INTEGRATIONS',
        exportable=False,
        deletion_behavior='PURGE_ON_NUMBER_DELETE',
        audit_requirement='WHATSAPP_CREDENTIAL_CHANGED',
    ),
    FieldClassification(
        model_name='WhatsAppConfiguration',
        field_name='webhook_secret',
        category=DataCategory.SECRET,
        purpose='Meta webhook HMAC signature verification',
        encryption=EncryptionRequirement.AES_256_GCM,
        masking=MaskingRequirement.WRITE_ONLY,
        retention_category='INTEGRATIONS',
        exportable=False,
        deletion_behavior='PURGE_ON_NUMBER_DELETE',
        audit_requirement='WHATSAPP_CREDENTIAL_CHANGED',
    ),

    # Billing & Financials
    FieldClassification(
        model_name='BillingProfile',
        field_name='tax_id',
        category=DataCategory.CONFIDENTIAL,
        purpose='GST / tax compliance and statutory invoice generation',
        encryption=EncryptionRequirement.NONE,
        masking=MaskingRequirement.NONE,
        retention_category='STATUTORY_FINANCIAL',
        exportable=True,
        deletion_behavior='RETAIN_PER_STATUTE',
        audit_requirement='BILLING_VIEWED',
    ),
    FieldClassification(
        model_name='PaymentMethod',
        field_name='last4',
        category=DataCategory.INTERNAL,
        purpose='Card identification reference for billing management',
        encryption=EncryptionRequirement.NONE,
        masking=MaskingRequirement.PARTIAL,
        retention_category='FINANCIAL',
        exportable=False,
        deletion_behavior='DELETE_ON_REPLACE',
        audit_requirement='PAYMENT_METHOD_CHANGED',
    ),
]


class DataClassificationService:
    """Provides machine-readable data classification catalog and ROPA data inventory."""

    @classmethod
    def get_catalog(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model_name': item.model_name,
                'field_name': item.field_name,
                'category': item.category.value,
                'purpose': item.purpose,
                'encryption': item.encryption.value,
                'masking': item.masking.value,
                'retention_category': item.retention_category,
                'exportable': item.exportable,
                'deletion_behavior': item.deletion_behavior,
                'audit_requirement': item.audit_requirement,
                'legal_basis_default': item.legal_basis_default,
            }
            for item in DATA_CLASSIFICATION_CATALOG
        ]

    @classmethod
    def get_ropa_inventory(cls, tenant) -> List[Dict[str, Any]]:
        """
        Record of Processing Activities (ROPA) under ISO 27701 and DPDP Act.
        Returns live processing records for the specified tenant.
        """
        catalog = cls.get_catalog()
        # Group by processing purpose and model
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in catalog:
            key = f"{item['model_name']}:{item['purpose']}"
            if key not in grouped:
                grouped[key] = {
                    'entity': item['model_name'],
                    'purpose': item['purpose'],
                    'data_category': item['category'],
                    'fields': [],
                    'encryption_status': item['encryption'],
                    'retention_policy': item['retention_category'],
                    'exportable': item['exportable'],
                    'deletion_mechanism': item['deletion_behavior'],
                    'tenant_id': tenant.id if tenant else None,
                    'tenant_name': tenant.name if tenant else 'Platform-wide',
                    'storage_location': 'PostgreSQL (Cloudtronix Private VPC)',
                    'subprocessors': ['Meta Cloud API (WhatsApp messaging)', 'AWS / GCP KMS (Key wrapping)'],
                }
            grouped[key]['fields'].append(item['field_name'])
        return list(grouped.values())

