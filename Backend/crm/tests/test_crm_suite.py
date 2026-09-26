import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from users.models import Tenant, TenantMembership
from organization.models import AuditLog
from organization.services.crypto_service import compute_blind_index, clear_crypto_cache
from crm.models import (
    Customer, CustomerIdentity, Lead, Pipeline, PipelineStage,
    Tag, CustomerTag, LeadTag, CustomFieldDefinition, CustomFieldValue,
    Activity, Note, CustomerMergeHistory
)
from crm.services.customer_service import CustomerService
from crm.services.lead_service import LeadService
from crm.services.pipeline_service import PipelineService
from crm.services.whatsapp_crm_service import WhatsAppCrmService
from crm.services.tag_service import TagService
from crm.services.custom_field_service import CustomFieldService
from whatsapp.models import Department, DepartmentMember

User = get_user_model()


class CrmComprehensiveTestCase(TestCase):
    def setUp(self):
        clear_crypto_cache()
        # 1. Tenants
        self.tenant_a = Tenant.objects.create(name='Acme Corp', slug='acme-corp', status='ACTIVE')
        self.tenant_b = Tenant.objects.create(name='Beta Ltd', slug='beta-ltd', status='ACTIVE')

        # 2. Users in Tenant A
        self.owner_a = User.objects.create_user(
            username='owner_a', email='owner@acme.test', password='password123',
            tenant=self.tenant_a, role='owner'
        )
        TenantMembership.objects.create(user=self.owner_a, tenant=self.tenant_a, role='owner')

        self.manager_a = User.objects.create_user(
            username='manager_a', email='manager@acme.test', password='password123',
            tenant=self.tenant_a, role='manager'
        )
        TenantMembership.objects.create(user=self.manager_a, tenant=self.tenant_a, role='manager')

        self.agent_a = User.objects.create_user(
            username='agent_a', email='agent@acme.test', password='password123',
            tenant=self.tenant_a, role='agent'
        )
        TenantMembership.objects.create(user=self.agent_a, tenant=self.tenant_a, role='agent')

        # 3. Users in Tenant B
        self.owner_b = User.objects.create_user(
            username='owner_b', email='owner@beta.test', password='password123',
            tenant=self.tenant_b, role='owner'
        )
        TenantMembership.objects.create(user=self.owner_b, tenant=self.tenant_b, role='owner')

        # 4. Departments
        self.dept_sales = Department.objects.create(tenant=self.tenant_a, name='Sales', slug='sales')
        self.dept_support = Department.objects.create(tenant=self.tenant_a, name='Support', slug='support')
        DepartmentMember.objects.create(
            department=self.dept_sales, user=self.agent_a, name='Agent A', whatsapp_number='+919876543210'
        )

        # 5. Default Pipelines
        self.pipeline_a = PipelineService.ensure_default_pipeline(self.tenant_a)
        self.pipeline_b = PipelineService.ensure_default_pipeline(self.tenant_b)

        self.client = APIClient()

    # =========================================================================
    # Phase 1 & 5: Customer Creation, AES-256-GCM Encryption & Masking
    # =========================================================================
    def test_customer_creation_encryption_and_blind_index(self):
        customer = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={
                'first_name': 'Rahul',
                'last_name': 'Sharma',
                'phone': '+91 98765 43210',
                'email': 'rahul.sharma@example.com',
                'source': 'WHATSAPP',
            },
            actor_user=self.owner_a,
        )

        # 1. Assert ciphertext contains envelope prefix cvx:v
        self.assertTrue(customer.phone_encrypted.startswith('cvx:v') or len(customer.phone_encrypted) > 20)
        self.assertNotIn('9876543210', customer.phone_encrypted)
        self.assertNotIn('rahul.sharma', customer.email_encrypted)

        # 2. Assert HMAC blind index lookup hash is calculated deterministically
        expected_phone_hash = compute_blind_index(self.tenant_a, '+919876543210', 'phone')
        self.assertEqual(customer.phone_lookup_hash, expected_phone_hash)

        # 3. Assert decrypted properties return original values
        self.assertEqual(customer.plain_phone, '+919876543210')
        self.assertEqual(customer.plain_email, 'rahul.sharma@example.com')
        self.assertEqual(customer.plain_first_name, 'Rahul')

        # 4. Assert masking works
        self.assertEqual(customer.masked_phone, '+91 ******3210')
        self.assertEqual(customer.masked_email, 'r*****a@example.com')

    def test_customer_api_pii_masking_based_on_rbac(self):
        customer = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={'first_name': 'Priya', 'last_name': 'Nair', 'phone': '+91 98765 11111', 'email': 'priya@example.com'},
        )

        # 1. Agent WITHOUT customer.view_pii receives masked values
        self.client.force_authenticate(user=self.agent_a)
        res_agent = self.client.get(f'/api/v1/customers/{customer.customer_id}/')
        self.assertEqual(res_agent.status_code, status.HTTP_200_OK)
        self.assertFalse(res_agent.data['is_pii_unmasked'])
        self.assertEqual(res_agent.data['phone'], '+91 ******1111')
        self.assertEqual(res_agent.data['email'], 'p*****a@example.com')

        # 2. Manager WITH customer.view_pii receives unmasked plaintext
        self.client.force_authenticate(user=self.manager_a)
        res_mgr = self.client.get(f'/api/v1/customers/{customer.customer_id}/')
        self.assertEqual(res_mgr.status_code, status.HTTP_200_OK)
        self.assertTrue(res_mgr.data['is_pii_unmasked'])
        self.assertEqual(res_mgr.data['phone'], '+919876511111')
        self.assertEqual(res_mgr.data['email'], 'priya@example.com')

    # =========================================================================
    # Phase 1 & Tenant Isolation
    # =========================================================================
    def test_tenant_isolation_cross_tenant_access_prevented(self):
        cust_a = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={'display_name': 'Acme Customer', 'phone': '+91 99999 00001'},
        )
        lead_a = LeadService.create_lead(
            tenant=self.tenant_a,
            customer=cust_a,
            data={'title': 'Acme Big Deal'},
        )

        # Tenant B user tries to access Tenant A's customer
        self.client.force_authenticate(user=self.owner_b)
        res_cust = self.client.get(f'/api/v1/customers/{cust_a.customer_id}/')
        self.assertEqual(res_cust.status_code, status.HTTP_404_NOT_FOUND)

        # Tenant B user tries to access Tenant A's lead
        res_lead = self.client.get(f'/api/v1/leads/{lead_a.lead_id}/')
        self.assertEqual(res_lead.status_code, status.HTTP_404_NOT_FOUND)

        # Tenant B user searches - must NOT return Tenant A's customer or lead
        res_search = self.client.get('/api/v1/crm/search?q=Acme')
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_search.data['customers']), 0)
        self.assertEqual(len(res_search.data['leads']), 0)

    # =========================================================================
    # Phase 2: WhatsApp Webhook -> CRM Lifecycle & Idempotency
    # =========================================================================
    def test_whatsapp_inbound_flow_and_idempotency(self):
        sender = '+91 91234 56789'
        # 1. First inbound message creates Customer and new Lead
        cust1, lead1, is_new1 = WhatsAppCrmService.handle_inbound_whatsapp_message(
            tenant=self.tenant_a,
            sender_phone=sender,
            sender_name='Alice Wonderland',
            message_content='Hello, I would like pricing details',
            meta_message_id='wamid_msg_001',
            department=self.dept_sales,
        )
        self.assertTrue(is_new1)
        self.assertIsNotNone(cust1)
        self.assertIsNotNone(lead1)
        self.assertEqual(lead1.status, 'OPEN')
        self.assertEqual(lead1.stage.name, 'New')

        # 2. Subsequent message from same customer does NOT create duplicate lead
        cust2, lead2, is_new2 = WhatsAppCrmService.handle_inbound_whatsapp_message(
            tenant=self.tenant_a,
            sender_phone=sender,
            sender_name='Alice Wonderland',
            message_content='Also, do you offer trial licenses?',
            meta_message_id='wamid_msg_002',
            department=self.dept_sales,
        )
        self.assertFalse(is_new2)
        self.assertEqual(cust1.customer_id, cust2.customer_id)
        self.assertEqual(lead1.lead_id, lead2.lead_id)

        # 3. Verify activities recorded
        activities = Activity.objects.filter(customer=cust1, activity_type='MESSAGE_RECEIVED')
        self.assertEqual(activities.count(), 2)

    # =========================================================================
    # Phase 4: Stage Progression, Concurrency & Optimistic Locking
    # =========================================================================
    def test_lead_stage_transition_and_concurrency(self):
        cust = CustomerService.create_customer(tenant=self.tenant_a, data={'display_name': 'Deal Customer'})
        lead = LeadService.create_lead(tenant=self.tenant_a, customer=cust, data={'title': 'Enterprise Contract'})

        qualified_stage = self.pipeline_a.stages.filter(name='Qualified').first()
        initial_version = lead.version

        # 1. Successful stage transition
        updated_lead = LeadService.transition_lead_stage(
            lead=lead,
            target_stage=qualified_stage,
            actor_user=self.manager_a,
            reason='Customer verified budget',
            client_version=initial_version,
        )
        self.assertEqual(updated_lead.stage.name, 'Qualified')
        self.assertEqual(updated_lead.version, initial_version + 1)

        # Verify Stage History entry
        history = lead.stage_history.filter(to_stage=qualified_stage).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.reason, 'Customer verified budget')

        # 2. Conflicting stale transition attempt fails optimistic concurrency
        negotiation_stage = self.pipeline_a.stages.filter(name='Negotiation').first()
        with self.assertRaises(Exception):
            LeadService.transition_lead_stage(
                lead=updated_lead,
                target_stage=negotiation_stage,
                actor_user=self.agent_a,
                client_version=initial_version,  # Stale version!
            )

    # =========================================================================
    # Phase 3 & 4: Ownership Assignment & History
    # =========================================================================
    def test_lead_assignment_and_history(self):
        cust = CustomerService.create_customer(tenant=self.tenant_a, data={'display_name': 'Test Cust'})
        lead = LeadService.create_lead(tenant=self.tenant_a, customer=cust, data={'title': 'Inbound Support'})

        updated = LeadService.assign_lead(
            lead=lead,
            owner_user=self.agent_a,
            department=self.dept_sales,
            assigned_by=self.manager_a,
            method='ROUND_ROBIN',
            reason='Auto-routing to on-duty agent',
        )
        self.assertEqual(updated.owner_user, self.agent_a)
        self.assertEqual(updated.department, self.dept_sales)

        # Verify assignment history
        hist = lead.assignment_history.first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.to_owner, self.agent_a)
        self.assertEqual(hist.assignment_method, 'ROUND_ROBIN')

    # =========================================================================
    # Phase 3: Tags & Custom Fields
    # =========================================================================
    def test_tags_and_custom_fields(self):
        cust = CustomerService.create_customer(tenant=self.tenant_a, data={'display_name': 'Tag Customer'})
        lead = LeadService.create_lead(tenant=self.tenant_a, customer=cust, data={'title': 'Custom Lead'})

        # Tag assignment
        TagService.sync_lead_tags(lead, ['VIP', 'Hot Deal'], actor_user=self.manager_a)
        self.assertEqual(lead.lead_tags.count(), 2)

        # Custom field definition and storage
        field_def = CustomFieldDefinition.objects.create(
            tenant=self.tenant_a,
            entity_type='LEAD',
            field_name='contract_tier',
            field_label='Contract Tier',
            field_type='SELECT',
            options=['Standard', 'Enterprise'],
            is_active=True,
        )
        CustomFieldService.save_custom_field_values(self.tenant_a, lead, {'contract_tier': 'Enterprise'})
        val_record = CustomFieldValue.objects.filter(lead=lead, definition=field_def).first()
        self.assertIsNotNone(val_record)
        self.assertEqual(val_record.get_plain_value(), 'Enterprise')

    # =========================================================================
    # Phase 6: Customer Merge
    # =========================================================================
    def test_customer_merge_preserves_relationships(self):
        # Create primary customer with lead1 and note
        primary = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={'display_name': 'Primary Corp', 'phone': '+91 98888 11111', 'email': 'primary@corp.test'},
        )
        lead1 = LeadService.create_lead(tenant=self.tenant_a, customer=primary, data={'title': 'Primary Lead'})

        # Create secondary customer with lead2 and note
        secondary = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={'display_name': 'Secondary Corp', 'phone': '+91 98888 22222', 'email': 'secondary@corp.test'},
        )
        lead2 = LeadService.create_lead(tenant=self.tenant_a, customer=secondary, data={'title': 'Secondary Opportunity'})

        sec_note = Note(
            tenant=self.tenant_a,
            customer=secondary,
            author_user=self.manager_a,
        )
        sec_note.set_content('Important note on secondary customer')
        sec_note.save()

        # Execute Merge
        merged = CustomerService.merge_customers(
            tenant=self.tenant_a,
            primary_customer=primary,
            secondary_customer=secondary,
            merged_by=self.owner_a,
            reason='Duplicate accounts created by customer',
        )

        # 1. Primary customer now owns both leads
        self.assertEqual(Lead.objects.filter(customer=merged).count(), 2)

        # 2. Secondary note transferred to primary
        self.assertEqual(Note.objects.filter(customer=merged).count(), 1)

        # 3. Secondary customer is soft-deleted
        secondary.refresh_from_db()
        self.assertTrue(secondary.is_deleted)

        # 4. Merge history recorded
        merge_hist = CustomerMergeHistory.objects.filter(primary_customer=merged).first()
        self.assertIsNotNone(merge_hist)
        self.assertEqual(merge_hist.secondary_customer_id, secondary.customer_id)

    # =========================================================================
    # Phase 3: Customer 360 Aggregation View
    # =========================================================================
    def test_customer_360_api_view(self):
        cust = CustomerService.create_customer(
            tenant=self.tenant_a,
            data={'display_name': '360 Test Corp', 'phone': '+91 97777 66666'},
        )
        lead = LeadService.create_lead(tenant=self.tenant_a, customer=cust, data={'title': 'Current Deal'})

        self.client.force_authenticate(user=self.manager_a)
        res = self.client.get(f'/api/v1/customers/{cust.customer_id}/360/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['profile']['display_name'], '360 Test Corp')
        self.assertEqual(len(res.data['current_leads']), 1)
        self.assertEqual(res.data['current_leads'][0]['title'], 'Current Deal')
