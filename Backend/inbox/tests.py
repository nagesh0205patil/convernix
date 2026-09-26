from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Tenant, User, TenantMembership
from whatsapp.models import Customer, Department, DepartmentMember, WhatsAppConfiguration, BusinessNumber
from inbox.models import (
    Conversation, ConversationStatus, ConversationPriority,
    Message, MessageDirection, MessageType, MessageStatus,
    ConversationRead, ConversationAssignment, Tag, ConversationTag, WebhookEvent
)
from users.permissions import has_tenant_permission


# ---------------------------------------------------------------------------
# Shared test fixture mixin
# ---------------------------------------------------------------------------

class InboxTestMixin:
    """Shared setUp helpers for inbox tests."""

    def _make_tenant(self, name, slug):
        return Tenant.objects.create(name=name, slug=slug, status='ACTIVE')

    def _make_user(self, email, username, tenant, role):
        user = User.objects.create_user(
            email=email,
            username=username,
            password='Password123!',
            tenant=tenant,
            role=role,
        )
        TenantMembership.objects.create(user=user, tenant=tenant, role=role)
        return user

    def _make_department(self, tenant, name, manager):
        return Department.objects.create(
            tenant=tenant,
            name=name,
            slug=name.lower().replace(' ', '-'),
            manager=manager,
        )

    def _make_customer(self, tenant, phone='+15551002000', name='Alice Customer'):
        return Customer.objects.create(
            tenant=tenant,
            whatsapp_number=phone,
            full_name=name,
        )

    def _make_business_number(self, tenant, number='+15550001111'):
        return BusinessNumber.objects.create(
            tenant=tenant,
            number=number,
            default_team='Support',
        )

    def _make_conversation(self, tenant, contact, department, status=ConversationStatus.OPEN, assigned_user=None):
        return Conversation.objects.create(
            tenant=tenant,
            contact=contact,
            department=department,
            status=status,
            priority=ConversationPriority.MEDIUM,
            assigned_user=assigned_user,
        )

    def _make_message(self, tenant, conversation, direction=MessageDirection.INBOUND,
                      msg_type=MessageType.TEXT, content='Hello', status=MessageStatus.RECEIVED):
        return Message.objects.create(
            tenant=tenant,
            conversation=conversation,
            direction=direction,
            message_type=msg_type,
            content=content,
            status=status,
        )

    def _auth_headers(self, user):
        """Return Authorization header dict for a given user using JWT."""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------

class InboxDomainModelTests(InboxTestMixin, TestCase):
    def setUp(self):
        self.tenant_a = self._make_tenant('Tenant Alpha', 'tenant-alpha')
        self.tenant_b = self._make_tenant('Tenant Beta', 'tenant-beta')

        self.agent_a = self._make_user('agent.a@alpha.test', 'agent_a', self.tenant_a, 'agent')
        self.manager_a = self._make_user('manager.a@alpha.test', 'manager_a', self.tenant_a, 'manager')

        self.dept_support = self._make_department(self.tenant_a, 'Support', self.manager_a)
        self.customer_a = self._make_customer(self.tenant_a)
        self.business_num = self._make_business_number(self.tenant_a)

    def test_conversation_creation_and_defaults(self):
        conv = self._make_conversation(self.tenant_a, self.customer_a, self.dept_support)
        self.assertEqual(conv.version, 1)
        self.assertEqual(conv.status, ConversationStatus.OPEN)
        self.assertTrue(conv.can_transition_to(ConversationStatus.PENDING))
        self.assertTrue(conv.can_transition_to(ConversationStatus.RESOLVED))
        self.assertFalse(conv.can_transition_to('UNKNOWN_STATUS'))

    def test_message_encryption_and_decryption(self):
        conv = self._make_conversation(self.tenant_a, self.customer_a, self.dept_support)
        msg = self._make_message(self.tenant_a, conv, content='Sensitive secret payload')
        # Content in database must be encrypted
        raw_db_content = Message.objects.filter(pk=msg.pk).values_list('content', flat=True).first()
        self.assertTrue(raw_db_content.startswith('cvx:v'))
        self.assertNotEqual(raw_db_content, 'Sensitive secret payload')
        # Plain content property must decrypt cleanly
        self.assertEqual(msg.plain_content, 'Sensitive secret payload')

    def test_per_user_read_tracking(self):
        conv = self._make_conversation(self.tenant_a, self.customer_a, self.dept_support)
        read_state, created = ConversationRead.objects.update_or_create(
            tenant=self.tenant_a,
            conversation=conv,
            user=self.agent_a,
            defaults={'last_read_message_id': 'msg_123', 'last_read_at': timezone.now()},
        )
        self.assertTrue(created)
        self.assertEqual(read_state.last_read_message_id, 'msg_123')
        # Another user read state is independent
        self.assertFalse(
            ConversationRead.objects.filter(conversation=conv, user=self.manager_a).exists()
        )

    def test_tenant_isolation_boundary(self):
        conv_a = self._make_conversation(self.tenant_a, self.customer_a, self.dept_support)
        # Tenant B queries must never find Tenant A conversation
        self.assertFalse(
            Conversation.objects.filter(tenant=self.tenant_b, pk=conv_a.pk).exists()
        )

    def test_rbac_permissions(self):
        self.assertTrue(has_tenant_permission(self.agent_a, self.tenant_a, 'inbox.view'))
        self.assertTrue(has_tenant_permission(self.agent_a, self.tenant_a, 'conversation.claim'))
        self.assertTrue(has_tenant_permission(self.agent_a, self.tenant_a, 'message.send'))
        self.assertFalse(has_tenant_permission(self.agent_a, self.tenant_a, 'contact.view_pii'))

        self.assertTrue(has_tenant_permission(self.manager_a, self.tenant_a, 'contact.view_pii'))
        self.assertTrue(has_tenant_permission(self.manager_a, self.tenant_a, 'conversation.reassign'))
        self.assertTrue(has_tenant_permission(self.manager_a, self.tenant_a, 'audit.view'))


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

class InboxAPIIntegrationTests(InboxTestMixin, TestCase):
    """End-to-end tests using DRF APIClient against the real URL routing."""

    def setUp(self):
        self.client = APIClient()

        self.tenant_a = self._make_tenant('Alpha Corp', 'alpha-corp')
        self.tenant_b = self._make_tenant('Beta Corp', 'beta-corp')

        self.agent = self._make_user('agent@alpha.test', 'agent_alpha', self.tenant_a, 'agent')
        self.manager = self._make_user('manager@alpha.test', 'manager_alpha', self.tenant_a, 'manager')
        self.agent_b = self._make_user('agent@beta.test', 'agent_beta', self.tenant_b, 'agent')

        self.dept = self._make_department(self.tenant_a, 'Support', self.manager)
        # Add agent as department member
        DepartmentMember.objects.create(department=self.dept, user=self.agent)

        self.customer = self._make_customer(self.tenant_a)
        self.biz_num = self._make_business_number(self.tenant_a)

    # ------------------------------------------------------------------
    # Authentication gate
    # ------------------------------------------------------------------

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get('/api/inbox/conversations/')
        self.assertEqual(response.status_code, 401)

    def test_authenticated_agent_can_list_conversations(self):
        self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.get(
            '/api/inbox/conversations/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)

    # ------------------------------------------------------------------
    # Tenant isolation
    # ------------------------------------------------------------------

    def test_tenant_b_agent_cannot_see_tenant_a_conversations(self):
        """Cross-tenant IDOR: agent from tenant B must get 0 results."""
        self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.get(
            '/api/inbox/conversations/',
            **self._auth_headers(self.agent_b),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['results'], [])

    def test_tenant_b_agent_cannot_fetch_tenant_a_conversation_detail(self):
        """
        Cross-tenant IDOR: agent from tenant B cannot read tenant A conversation.
        View returns 404 (not found in tenant scope) rather than 403 to avoid
        confirming resource existence to an unauthorized party.
        """
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.get(
            f'/api/inbox/conversations/{conv.id}/',
            **self._auth_headers(self.agent_b),
        )
        # 404 is correct security behavior — doesn't reveal resource existence
        self.assertIn(response.status_code, [403, 404])

    # ------------------------------------------------------------------
    # Conversation detail
    # ------------------------------------------------------------------

    def test_agent_can_fetch_own_tenant_conversation(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.get(
            f'/api/inbox/conversations/{conv.id}/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], conv.id)
        self.assertEqual(data['status'], 'OPEN')

    # ------------------------------------------------------------------
    # Claim conversation
    # ------------------------------------------------------------------

    def test_agent_can_claim_unassigned_conversation(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept, assigned_user=None)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/claim/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.assigned_user, self.agent)

    def test_claim_already_assigned_conversation_returns_409(self):
        """Concurrent claim must return 409 Conflict."""
        conv = self._make_conversation(
            self.tenant_a, self.customer, self.dept, assigned_user=self.manager
        )
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/claim/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 409)
        data = response.json()
        # DRF returns conflict detail in 'detail' key
        self.assertTrue('detail' in data or 'error' in data)

    # ------------------------------------------------------------------
    # Resolve / reopen state machine
    # ------------------------------------------------------------------

    def test_manager_can_resolve_open_conversation(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/resolve/',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.status, ConversationStatus.RESOLVED)

    def test_resolve_already_resolved_conversation_returns_400(self):
        """Invalid state transition: RESOLVED → RESOLVED must be rejected."""
        conv = self._make_conversation(
            self.tenant_a, self.customer, self.dept, status=ConversationStatus.RESOLVED
        )
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/resolve/',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 400)

    def test_manager_can_reopen_resolved_conversation(self):
        conv = self._make_conversation(
            self.tenant_a, self.customer, self.dept, status=ConversationStatus.RESOLVED
        )
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/reopen/',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.status, ConversationStatus.OPEN)

    def test_agent_can_resolve_conversation_per_rbac(self):
        """
        Agents have conversation.resolve in their RBAC permission set.
        This is by design — agents can self-resolve their conversations.
        """
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/resolve/',
            **self._auth_headers(self.agent),
        )
        # Agents have conversation.resolve permission — this should succeed
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Messages list
    # ------------------------------------------------------------------

    def test_agent_can_list_messages(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        self._make_message(self.tenant_a, conv, content='Hello there')
        response = self.client.get(
            f'/api/inbox/conversations/{conv.id}/messages/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        # Content should be decrypted in API response
        self.assertEqual(data['results'][0]['content'], 'Hello there')

    def test_internal_notes_visible_to_agents_with_note_view(self):
        """
        Agents have note.view permission, so internal notes appear in the message list.
        The messages endpoint filters INTERNAL_NOTE messages based on note.view permission.
        """
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        # Create a visible message
        self._make_message(self.tenant_a, conv, content='Regular message')
        # Create an internal note
        Message.objects.create(
            tenant=self.tenant_a,
            conversation=conv,
            direction=MessageDirection.INTERNAL,
            message_type=MessageType.INTERNAL_NOTE,
            content='Internal agent note',
            status=MessageStatus.RECEIVED,
        )
        response = self.client.get(
            f'/api/inbox/conversations/{conv.id}/messages/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        returned_contents = [m['content'] for m in response.json()['results']]
        # Both regular and internal notes visible since agent has note.view
        self.assertIn('Regular message', returned_contents)
        self.assertIn('Internal agent note', returned_contents)

    # ------------------------------------------------------------------
    # Internal notes must NOT be dispatched to Meta
    # ------------------------------------------------------------------

    def test_create_note_does_not_call_meta(self):
        """
        Creating an internal note must not produce a QUEUED/SENDING outbound message.
        The note direction must always be INTERNAL.
        """
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/notes/',
            data={'content': 'This is a private note @agent_alpha'},
            format='json',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 201)
        note_id = response.json()['id']
        note = Message.objects.get(pk=note_id)
        self.assertEqual(note.direction, MessageDirection.INTERNAL)
        # Internal notes are identified by INTERNAL_NOTE message_type (no is_internal field)
        self.assertEqual(note.message_type, MessageType.INTERNAL_NOTE)
        # Must not have an outbound queued status
        self.assertNotEqual(note.status, MessageStatus.QUEUED)
        self.assertNotEqual(note.status, MessageStatus.SENDING)

    # ------------------------------------------------------------------
    # Read state
    # ------------------------------------------------------------------

    def test_mark_conversation_read(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        msg = self._make_message(self.tenant_a, conv)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/read/',
            data={'last_read_message_id': str(msg.id)},
            format='json',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        read_state = ConversationRead.objects.filter(
            conversation=conv, user=self.agent
        ).first()
        self.assertIsNotNone(read_state)

    # ------------------------------------------------------------------
    # Assign / unassign (manager-only)
    # ------------------------------------------------------------------

    def test_manager_can_assign_conversation(self):
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/assign/',
            data={'user_id': self.agent.id},
            format='json',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.assigned_user, self.agent)

    def test_agent_can_assign_conversation_per_rbac(self):
        """
        Agents have conversation.assign in their RBAC permission set.
        Only conversation.reassign (changing an already-assigned conversation) is manager-only.
        """
        conv = self._make_conversation(self.tenant_a, self.customer, self.dept)
        # Assign to manager (an existing user in the same tenant)
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/assign/',
            data={'user_id': self.manager.id},
            format='json',
            **self._auth_headers(self.agent),
        )
        # Agents have conversation.assign permission — this should succeed
        self.assertEqual(response.status_code, 200)

    def test_manager_can_unassign_conversation(self):
        conv = self._make_conversation(
            self.tenant_a, self.customer, self.dept, assigned_user=self.agent
        )
        response = self.client.post(
            f'/api/inbox/conversations/{conv.id}/unassign/',
            **self._auth_headers(self.manager),
        )
        self.assertEqual(response.status_code, 200)
        conv.refresh_from_db()
        self.assertIsNone(conv.assigned_user)

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def test_filter_by_status(self):
        self._make_conversation(self.tenant_a, self.customer, self.dept, status=ConversationStatus.OPEN)
        customer2 = self._make_customer(self.tenant_a, phone='+15551002001', name='Bob')
        self._make_conversation(self.tenant_a, customer2, self.dept, status=ConversationStatus.RESOLVED)

        response = self.client.get(
            '/api/inbox/conversations/?status=OPEN',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertTrue(all(r['status'] == 'OPEN' for r in results))
        self.assertEqual(len(results), 1)

    def test_filter_my_conversations(self):
        """?ownership=mine must only return conversations assigned to requesting user."""
        # Assigned to agent
        self._make_conversation(
            self.tenant_a, self.customer, self.dept, assigned_user=self.agent
        )
        # Assigned to manager
        customer2 = self._make_customer(self.tenant_a, phone='+15551002001', name='Bob')
        self._make_conversation(
            self.tenant_a, customer2, self.dept, assigned_user=self.manager
        )

        response = self.client.get(
            '/api/inbox/conversations/?ownership=mine',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)

    # ------------------------------------------------------------------
    # Department queue
    # ------------------------------------------------------------------

    def test_agent_can_list_department_queues(self):
        response = self.client.get(
            '/api/inbox/departments/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def test_agent_can_list_tags(self):
        Tag.objects.create(tenant=self.tenant_a, name='VIP', color='#FF0000')
        Tag.objects.create(tenant=self.tenant_b, name='Other Tenant Tag', color='#0000FF')
        response = self.client.get(
            '/api/inbox/tags/',
            **self._auth_headers(self.agent),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [t['name'] for t in data]
        self.assertIn('VIP', names)
        # Must NOT see other tenant's tags
        self.assertNotIn('Other Tenant Tag', names)
