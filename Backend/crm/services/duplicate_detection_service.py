import logging
from typing import Any, Dict, List, Optional
from django.db.models import Q
from crm.models import Customer, CustomerIdentity
from organization.services.crypto_service import compute_blind_index, normalize_search_term

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    @classmethod
    def compute_hashes(cls, tenant, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, str]:
        """
        Normalizes phone/email and computes deterministic HMAC-SHA256 blind index hashes.
        """
        hashes = {'phone_hash': '', 'email_hash': '', 'canonical_phone': '', 'canonical_email': ''}
        if phone:
            canonical_phone = normalize_search_term(phone, 'phone')
            hashes['canonical_phone'] = canonical_phone
            hashes['phone_hash'] = compute_blind_index(tenant, canonical_phone, 'phone')
        if email:
            canonical_email = normalize_search_term(email, 'email')
            hashes['canonical_email'] = canonical_email
            hashes['email_hash'] = compute_blind_index(tenant, canonical_email, 'email')
        return hashes

    @classmethod
    def find_exact_customer(
        cls, tenant, phone: Optional[str] = None, email: Optional[str] = None
    ) -> Optional[Customer]:
        """
        Finds an existing non-deleted customer in the tenant by phone or email lookup hash.
        """
        hashes = cls.compute_hashes(tenant, phone=phone, email=email)
        query = Q(tenant=tenant, deleted_at__isnull=True)

        match_q = Q()
        if hashes['phone_hash']:
            match_q |= Q(phone_lookup_hash=hashes['phone_hash'])
        if hashes['email_hash']:
            match_q |= Q(email_lookup_hash=hashes['email_hash'])

        if not match_q:
            return None

        # Check Customer direct hashes
        customer = Customer.objects.filter(query & match_q).first()
        if customer:
            return customer

        # Check CustomerIdentity provider table
        if hashes['phone_hash']:
            identity = CustomerIdentity.objects.filter(
                tenant=tenant,
                provider__in=['WHATSAPP', 'PHONE'],
                lookup_hash=hashes['phone_hash'],
                customer__deleted_at__isnull=True,
            ).select_related('customer').first()
            if identity and identity.customer:
                return identity.customer

        if hashes['email_hash']:
            identity = CustomerIdentity.objects.filter(
                tenant=tenant,
                provider='EMAIL',
                lookup_hash=hashes['email_hash'],
                customer__deleted_at__isnull=True,
            ).select_related('customer').first()
            if identity and identity.customer:
                return identity.customer

        return None

    @classmethod
    def find_potential_duplicates(
        cls,
        tenant,
        customer_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Exposes possible duplicate customers for authorized agent/manager review.
        Does NOT automatically merge.
        """
        duplicates = []
        hashes = cls.compute_hashes(tenant, phone=phone, email=email)
        base_qs = Customer.objects.filter(tenant=tenant, deleted_at__isnull=True)
        if customer_id:
            base_qs = base_qs.exclude(customer_id=customer_id)

        # 1. Exact phone match
        if hashes['phone_hash']:
            phone_matches = base_qs.filter(phone_lookup_hash=hashes['phone_hash'])
            for c in phone_matches:
                duplicates.append({
                    'customer_id': str(c.customer_id),
                    'display_name': c.display_name or c.plain_full_name,
                    'match_reason': 'Exact phone number match',
                    'confidence': 1.0,
                    'created_at': c.created_at.isoformat(),
                })

        # 2. Exact email match
        if hashes['email_hash']:
            email_matches = base_qs.filter(email_lookup_hash=hashes['email_hash'])
            for c in email_matches:
                if not any(d['customer_id'] == str(c.customer_id) for d in duplicates):
                    duplicates.append({
                        'customer_id': str(c.customer_id),
                        'display_name': c.display_name or c.plain_full_name,
                        'match_reason': 'Exact email address match',
                        'confidence': 0.95,
                        'created_at': c.created_at.isoformat(),
                    })

        # 3. Identity matches (e.g. WhatsApp identity)
        if hashes['phone_hash']:
            ident_matches = CustomerIdentity.objects.filter(
                tenant=tenant,
                lookup_hash=hashes['phone_hash'],
                customer__deleted_at__isnull=True,
            ).select_related('customer')
            if customer_id:
                ident_matches = ident_matches.exclude(customer_id=customer_id)
            for ident in ident_matches:
                cid = str(ident.customer_id)
                if not any(d['customer_id'] == cid for d in duplicates):
                    duplicates.append({
                        'customer_id': cid,
                        'display_name': ident.customer.display_name or ident.customer.plain_full_name,
                        'match_reason': f'Matched on {ident.provider} identity',
                        'confidence': 0.98,
                        'created_at': ident.customer.created_at.isoformat(),
                    })

        # 4. Same display name match if significant length
        if name and len(name.strip()) >= 4:
            clean_name = name.strip()
            name_matches = base_qs.filter(display_name__iexact=clean_name)[:5]
            for c in name_matches:
                cid = str(c.customer_id)
                if not any(d['customer_id'] == cid for d in duplicates):
                    duplicates.append({
                        'customer_id': cid,
                        'display_name': c.display_name or c.plain_full_name,
                        'match_reason': 'Identical display name',
                        'confidence': 0.65,
                        'created_at': c.created_at.isoformat(),
                    })

        return duplicates
