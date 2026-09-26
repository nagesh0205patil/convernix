import hashlib
import hmac
import json
from datetime import timedelta
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (BusinessNumber, Customer, Department, DepartmentMember, Enquiry, Notification,
                     WhatsAppConfiguration, WhatsAppMessage)
from .meta import (MetaAPIError, MetaAPIPermanentError, build_template_request,
                   build_text_request, send_template_message)
from .services import (apply_delivery_status, create_enquiry, parse_meta_events,
                       record_incoming_message, route_incoming_message)
from .tasks import send_department_notification

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class BusinessNumberWorkspaceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='workspace-user', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_selector_only_returns_configured_numbers_and_discovers_new_configuration(self):
        WhatsAppConfiguration.objects.create(business_number='+918035260741', phone_number_id='india-id')
        BusinessNumber.objects.create(number='+15550009999', label='Orphan demo number')

        first = self.client.get('/api/whatsapp/business-numbers/')
        self.assertEqual(first.status_code, 200)
        self.assertEqual([item['number'] for item in first.data], ['+918035260741'])

        WhatsAppConfiguration.objects.create(business_number='+12522501805', phone_number_id='usa-id')
        second = self.client.get('/api/whatsapp/business-numbers/')
        self.assertEqual(second.status_code, 200)
        self.assertCountEqual([item['number'] for item in second.data], ['+918035260741', '+12522501805'])

    def test_incoming_enquiry_preserves_custom_workspace_label(self):
        WhatsAppConfiguration.objects.create(business_number='+12522501805', phone_number_id='usa-id')
        number = BusinessNumber.objects.create(number='+12522501805', label='USA Operations')

        create_enquiry({
            'phone_number': '+12525550100', 'message': 'Hello', 'business_number': '+12522501805',
        })

        number.refresh_from_db()
        self.assertEqual(number.label, 'USA Operations')

    def test_user_number_access_limits_list_and_selection(self):
        india = WhatsAppConfiguration.objects.create(business_number='+918035260741', phone_number_id='india-id')
        usa = WhatsAppConfiguration.objects.create(business_number='+12522501805', phone_number_id='usa-id')
        user = User.objects.create_user(username='india-user', email='india@example.com', password='password123', number_access='india')
        self.client.force_authenticate(user=user)

        response = self.client.get('/api/whatsapp/business-numbers/')
        self.assertEqual([item['number'] for item in response.data], [india.business_number])
        usa_number = BusinessNumber.objects.get(number=usa.business_number)
        denied = self.client.get('/api/whatsapp/enquiries/', HTTP_X_BUSINESS_NUMBER_ID=str(usa_number.pk))
        self.assertEqual(denied.status_code, 404)


class RoutingServiceTests(TestCase):
    def setUp(self):
        configuration = WhatsAppConfiguration.load()
        configuration.business_number = '+15550009999'
        configuration.save()
        self.sales = Department.objects.create(name='Sales', slug='sales')
        self.support = Department.objects.create(name='Support', slug='support')
        for index in range(2):
            DepartmentMember.objects.create(
                department=self.sales, name=f'Sales {index}', whatsapp_number=f'+1555000000{index}',
            )

    def test_structured_category_creates_customer_enquiry_and_two_notifications(self):
        result = route_incoming_message({
            'customer_name': 'Alice', 'phone_number': '+15551234567',
            'customer_email': 'alice@example.com', 'organization_name': 'Acme',
            'category': 'Sales', 'message': 'Pricing please', 'business_number': '+15550009999',
        })
        enquiry = Enquiry.objects.get(pk=result['enquiry_id'])
        self.assertEqual(enquiry.department, self.sales)
        self.assertEqual(enquiry.customer.organization_name, 'Acme')
        self.assertEqual(result['recipient_count'], 2)
        self.assertTrue(result['reference'].startswith('ENQ-'))

    def test_only_active_notification_enabled_members_are_selected(self):
        self.sales.members.create(name='Disabled', whatsapp_number='+15550000010', notification_enabled=False)
        self.sales.members.create(name='Inactive', whatsapp_number='+15550000011', active=False)
        enquiry, _ = create_enquiry({
            'phone_number': '+15551234567', 'category': 'Sales', 'message': 'Pricing',
            'business_number': '+15550009999',
        })
        self.assertEqual(enquiry.notifications.count(), 2)

    def test_message_id_is_idempotent(self):
        data = {'phone_number': '+15551234567', 'category': 'Sales', 'message': 'Hello', 'business_number': '+15550009999'}
        first, _ = create_enquiry(data, whatsapp_message_id='wamid.1')
        second, state = create_enquiry(data, whatsapp_message_id='wamid.1')
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(state, 'duplicate')
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_repeat_customer_message_is_added_to_conversation_not_enquiries(self):
        data = {'phone_number': '+15551234567', 'category': 'Sales', 'message': 'Hello', 'business_number': '+15550009999'}
        enquiry, _ = record_incoming_message(data, whatsapp_message_id='wamid.first')

        repeated, state = record_incoming_message(
            {**data, 'message': 'Are you there?'}, whatsapp_message_id='wamid.second',
        )

        self.assertEqual(repeated, enquiry)
        self.assertEqual(state, 'existing-conversation')
        self.assertEqual(Enquiry.objects.count(), 1)
        self.assertEqual(list(enquiry.messages.values_list('content', flat=True)), ['Hello', 'Are you there?'])

    def test_delivery_status_updates_audit_records(self):
        enquiry, _ = create_enquiry(
            {'phone_number': '+15551234567', 'category': 'Sales', 'message': 'Hello', 'business_number': '+15550009999'},
            whatsapp_message_id='wamid.in',
        )
        notification = enquiry.notifications.first()
        notification.whatsapp_message_id = 'wamid.out'
        notification.save()
        WhatsAppMessage.objects.create(
            whatsapp_message_id='wamid.out', customer=enquiry.customer, enquiry=enquiry,
            direction='outgoing', message_type='template', timestamp=timezone.now(),
        )
        apply_delivery_status('wamid.out', 'delivered')
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'delivered')
        self.assertEqual(WhatsAppMessage.objects.get(whatsapp_message_id='wamid.out').status, 'delivered')

    def test_database_default_team_change_is_used_for_existing_business_number(self):
        configuration = WhatsAppConfiguration.load()
        configuration.business_number = '+15550009999'
        configuration.default_team = 'Support'
        configuration.save()
        create_enquiry({'phone_number': '+15551234567', 'message': 'First'})

        configuration.default_team = 'Customer Success'
        configuration.save()
        enquiry, _ = create_enquiry({'phone_number': '+15557654321', 'message': 'Second'})

        self.assertEqual(enquiry.department.name, 'Customer Success')

    def test_each_business_number_uses_its_own_configuration(self):
        india = WhatsAppConfiguration.load()
        india.business_number = '+918035260741'
        india.default_team = 'India Support'
        india.save()
        WhatsAppConfiguration.objects.create(
            business_number='+12125550123', default_team='USA Support',
            phone_number_id='usa-phone-id', business_account_id='usa-waba-id',
        )

        enquiry, _ = create_enquiry({
            'phone_number': '+15551234567', 'message': 'Help', 'business_number': '+1 (212) 555-0123',
        })

        self.assertEqual(enquiry.department.name, 'USA Support')
        self.assertEqual(enquiry.legacy_lead.business_number.phone_number_id, 'usa-phone-id')

    def test_display_number_mapping_and_dedicated_forwarding_recipient(self):
        configuration = WhatsAppConfiguration.load()
        configuration.business_number = '+918035260741'
        configuration.phone_number_id = 'meta-phone-id'
        configuration.save()
        BusinessNumber.objects.create(
            number='+16505551111', phone_number_id='meta-phone-id',
            forwarding_number='+919967070453', default_team='Support',
        )
        DepartmentMember.objects.create(
            department=self.support, name='Unrelated recipient', whatsapp_number='+919999999999',
        )

        enquiry, _ = create_enquiry({
            'phone_number': '+15551234567', 'message': 'Hi',
            'business_number': '+16505551111', 'phone_number_id': 'test-payload-id',
        })

        self.assertEqual(enquiry.legacy_lead.business_number.phone_number_id, 'meta-phone-id')
        self.assertEqual(
            list(enquiry.notifications.values_list('recipient__whatsapp_number', flat=True)),
            ['+919967070453'],
        )


@override_settings(SECURE_SSL_REDIRECT=False)
class WebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('whatsapp-webhook')
        self.configuration = WhatsAppConfiguration.load()

    def test_verification_challenge(self):
        self.configuration.verify_token = 'verify-me'
        self.configuration.save()
        response = self.client.get(self.url, {'hub.mode': 'subscribe', 'hub.verify_token': 'verify-me', 'hub.challenge': '1234'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'1234')
        self.assertEqual(response['Content-Type'], 'text/plain')

    @override_settings(WHATSAPP_ALLOW_UNSIGNED_WEBHOOKS=False)
    @patch('whatsapp.views.process_webhook_payload.delay')
    def test_signed_payload_is_queued_and_acknowledged(self, delay):
        self.configuration.webhook_secret = 'app-secret'
        self.configuration.save()
        payload = {'object': 'whatsapp_business_account', 'entry': []}
        body = json.dumps(payload).encode()
        signature = 'sha256=' + hmac.new(b'app-secret', body, hashlib.sha256).hexdigest()
        with self.assertLogs('whatsapp.views', level='INFO') as captured_logs:
            response = self.client.post(
                self.url, body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=signature,
            )
        self.assertEqual(response.status_code, 200)
        delay.assert_called_once_with(payload)
        self.assertIn('signature verified and payload queued', captured_logs.output[0])

    @patch('whatsapp.views.process_webhook_payload.delay')
    def test_invalid_signature_is_rejected(self, delay):
        self.configuration.webhook_secret = 'app-secret'
        self.configuration.save()
        with self.assertLogs('whatsapp.views', level='WARNING') as captured_logs:
            response = self.client.post(self.url, {'object': 'whatsapp_business_account'}, format='json', HTTP_X_HUB_SIGNATURE_256='sha256=invalid')
        self.assertEqual(response.status_code, 403)
        delay.assert_not_called()
        self.assertIn('no messages queued', captured_logs.output[0])

    @patch('whatsapp.views.process_webhook_payload.delay')
    def test_second_configuration_secret_is_accepted(self, delay):
        self.configuration.webhook_secret = 'india-secret'
        self.configuration.save()
        WhatsAppConfiguration.objects.create(business_number='+12125550123', webhook_secret='usa-secret')
        payload = {'object': 'whatsapp_business_account', 'entry': []}
        body = json.dumps(payload).encode()
        signature = 'sha256=' + hmac.new(b'usa-secret', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            self.url, body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, 200)
        delay.assert_called_once_with(payload)

    def test_real_meta_flow_payload_is_parsed(self):
        payload = {'entry': [{'changes': [{'value': {
            'metadata': {'display_phone_number': '+15550009999'},
            'contacts': [{'wa_id': '15551234567', 'profile': {'name': 'Alice'}}],
            'messages': [{'id': 'wamid.flow', 'from': '15551234567', 'timestamp': '1700000000',
                          'type': 'interactive', 'interactive': {'nfm_reply': {'response_json': json.dumps({
                              'full_name': 'Alice A', 'organization': 'Acme', 'email': 'alice@example.com',
                              'category': 'Sales', 'message': 'Pricing',
                          })}}}],
        }}]}]}
        event = parse_meta_events(payload)[0]
        self.assertEqual(event['data']['category'], 'Sales')
        self.assertEqual(event['data']['organization_name'], 'Acme')
        self.assertEqual(event['message_id'], 'wamid.flow')

    def test_meta_phone_number_id_is_parsed(self):
        payload = {'entry': [{'changes': [{'value': {
            'metadata': {'display_phone_number': '+16505551111', 'phone_number_id': 'phone-id'},
            'messages': [{'id': 'wamid.text', 'from': '15551234567', 'type': 'text',
                          'text': {'body': 'Hi'}}],
        }}]}]}

        event = parse_meta_events(payload)[0]

        self.assertEqual(event['data']['phone_number_id'], 'phone-id')


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthorizationTests(TestCase):
    def test_regular_user_cannot_manage_team_members(self):
        user = User.objects.create_user(username='person', email='person@example.com', password='password123')
        client = APIClient()
        client.force_authenticate(user=user)
        self.assertEqual(client.get('/api/team-members/').status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False)
class EnquiryExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='exporter', email='exporter@example.com', password='password123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.department = Department.objects.create(name='Export Sales', slug='export-sales')
        self.customer = Customer.objects.create(
            whatsapp_number='+15551234567', full_name='=Formula Customer',
            email='customer@example.com', organization_name='Acme',
        )

    def create_enquiry(self, days_ago, message='Pricing information'):
        enquiry = Enquiry.objects.create(
            customer=self.customer, department=self.department, message=message,
        )
        Enquiry.objects.filter(pk=enquiry.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        return enquiry

    def test_week_export_is_authenticated_and_filters_old_enquiries(self):
        recent = self.create_enquiry(3, message='Recent enquiry')
        old = self.create_enquiry(10, message='Old enquiry')

        response = self.client.get('/api/whatsapp/enquiries/export/', {'range': 'week'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="enquiries_', response['Content-Disposition'])
        content = response.content.decode('utf-8-sig')
        self.assertIn(recent.reference, content)
        self.assertNotIn(old.reference, content)
        self.assertIn("'=Formula Customer", content)

    def test_custom_export_uses_inclusive_dates(self):
        enquiry = self.create_enquiry(20)
        target_date = timezone.localdate() - timedelta(days=20)

        response = self.client.get('/api/whatsapp/enquiries/export/', {
            'range': 'custom', 'start_date': target_date.isoformat(), 'end_date': target_date.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(enquiry.reference, response.content.decode('utf-8-sig'))

    def test_invalid_custom_range_returns_400(self):
        response = self.client.get('/api/whatsapp/enquiries/export/', {
            'range': 'custom', 'start_date': '2026-08-20', 'end_date': '2026-08-01',
        })
        self.assertEqual(response.status_code, 400)

    def test_export_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/whatsapp/enquiries/export/').status_code, 401)


@override_settings(SECURE_SSL_REDIRECT=False)
class EnquiryPaginationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='pagination-agent', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        department = Department.objects.create(name='Pagination Support', slug='pagination-support')
        customer = Customer.objects.create(whatsapp_number='+15550000123', full_name='Pagination Customer')
        Enquiry.objects.bulk_create([
            Enquiry(
                reference=f'ENQ-PAGINATION-{index:03d}', customer=customer,
                department=department, message=f'Enquiry {index}',
            )
            for index in range(55)
        ])

    def test_enquiry_list_supports_requested_page_sizes_and_next_page(self):
        first_page = self.client.get('/api/whatsapp/enquiries/', {'page_size': 50})
        second_page = self.client.get('/api/whatsapp/enquiries/', {'page_size': 50, 'page': 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data['count'], 55)
        self.assertEqual(len(first_page.data['results']), 50)
        self.assertIsNotNone(first_page.data['next'])
        self.assertEqual(len(second_page.data['results']), 5)
        self.assertIsNotNone(second_page.data['previous'])

    def test_enquiry_list_accepts_only_supported_page_sizes(self):
        for page_size in (20, 50, 100, 150, 200):
            response = self.client.get('/api/whatsapp/enquiries/', {'page_size': page_size})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['results']), min(page_size, 55))

        unsupported = self.client.get('/api/whatsapp/enquiries/', {'page_size': 500})
        self.assertEqual(len(unsupported.data['results']), 20)


@override_settings(
    WHATSAPP_ACCESS_TOKEN='secret-token', WHATSAPP_PHONE_NUMBER_ID='fallback-id',
    WHATSAPP_API_VERSION='v23.0', WHATSAPP_TEMPLATE_NAME='new_lead_notification',
    WHATSAPP_TEMPLATE_LANGUAGE='en',
)
class MetaClientTests(TestCase):
    def setUp(self):
        self.configuration = WhatsAppConfiguration.load()
        self.configuration.business_number = '+15550009999'
        self.configuration.phone_number_id = 'company-phone-id'
        self.configuration.meta_access_token = 'secret-token'
        self.configuration.save()

    def test_template_uses_employee_as_recipient_and_company_phone_id_endpoint(self):
        url, token, payload = build_template_request(
            '+919876543210', ['Alice', '+15551234567', 'Sales', 'Pricing', '21-Aug-2026 10:45 AM'],
            business_number='+15550009999',
        )
        self.assertEqual(url, 'https://graph.facebook.com/v23.0/company-phone-id/messages')
        self.assertEqual(token, 'secret-token')
        self.assertEqual(payload['to'], '919876543210')
        self.assertEqual(payload['template']['name'], 'new_lead_notification')
        values = [item['text'] for item in payload['template']['components'][0]['parameters']]
        self.assertEqual(values[1], '+15551234567')

    def test_text_reply_uses_customer_as_recipient(self):
        url, token, payload = build_text_request(
            '+15551234567', 'Thanks for contacting us', business_number='+15550009999',
        )
        self.assertEqual(url, 'https://graph.facebook.com/v23.0/company-phone-id/messages')
        self.assertEqual(token, 'secret-token')
        self.assertEqual(payload['to'], '15551234567')
        self.assertEqual(payload['text']['body'], 'Thanks for contacting us')


    @patch('whatsapp.meta.request.urlopen')
    def test_403_permission_error_is_permanent_and_parsed(self, urlopen):
        body = json.dumps({'error': {'message': '(#200) No permission', 'code': 200, 'fbtrace_id': 'trace'}}).encode()
        urlopen.side_effect = HTTPError('url', 403, 'Forbidden', {}, BytesIO(body))
        with self.assertRaises(MetaAPIPermanentError) as caught:
            send_template_message('+919876543210', ['a', 'b', 'c', 'd', 'e'], business_number='+15550009999')
        self.assertEqual(caught.exception.http_status, 403)
        self.assertEqual(caught.exception.code, '200')
        self.assertEqual(caught.exception.fbtrace_id, 'trace')

    @override_settings(WHATSAPP_ACCESS_TOKEN='')
    def test_missing_token_is_controlled_and_does_not_disclose_a_secret(self):
        self.configuration.meta_access_token = ''
        self.configuration.save(update_fields=['meta_access_token'])
        with self.assertRaisesRegex(MetaAPIPermanentError, 'WHATSAPP_ACCESS_TOKEN'):
            build_template_request('+919876543210', [], business_number='+15550009999')

    def test_invalid_employee_number_is_permanent(self):
        with self.assertRaisesRegex(MetaAPIPermanentError, 'valid E.164'):
            send_template_message('invalid', [], business_number='+15550009999')

    @patch('whatsapp.meta.request.urlopen')
    def test_http_500_is_retryable(self, urlopen):
        urlopen.side_effect = HTTPError('url', 500, 'Server Error', {}, BytesIO(b'{"error":{"message":"temporary"}}'))
        with self.assertRaises(MetaAPIError) as caught:
            send_template_message('+919876543210', [], business_number='+15550009999')
        self.assertNotIsInstance(caught.exception, MetaAPIPermanentError)

    @patch('whatsapp.tasks.send_template_message')
    def test_disabled_recipient_is_not_sent(self, send):
        department = Department.objects.create(name='Accounts', slug='accounts-task')
        member = DepartmentMember.objects.create(
            department=department, name='Disabled', whatsapp_number='+919876543210',
            notification_enabled=False,
        )
        enquiry, _ = create_enquiry({
            'phone_number': '+15551234567', 'category': 'Accounts', 'message': 'Invoice',
            'business_number': '+15550009999',
        })
        notification = Notification.objects.create(
            enquiry=enquiry, recipient=member, recipient_number=member.whatsapp_number,
        )
        send_department_notification.apply(args=[notification.pk]).get()
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'permanently_failed')
        send.assert_not_called()

    @patch('whatsapp.tasks.send_template_message')
    def test_permanent_meta_failure_is_audited(self, send):
        department = Department.objects.create(name='Technical', slug='technical-task')
        member = DepartmentMember.objects.create(department=department, name='Tech', whatsapp_number='+919876543210')
        enquiry, _ = create_enquiry({
            'phone_number': '+15551234567', 'category': 'Technical', 'message': 'Broken',
            'business_number': '+15550009999',
        })
        notification = Notification.objects.get(enquiry=enquiry, recipient=member)
        send.side_effect = MetaAPIPermanentError(
            'No permission', http_status=403, code=200, response_payload={'error': {'code': 200}},
            request_payload={'messaging_product': 'whatsapp'},
        )
        send_department_notification.apply(args=[notification.pk]).get()
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'permanently_failed')
        self.assertEqual(notification.http_status_code, 403)
        self.assertEqual(notification.error_code, '200')
        self.assertNotIn('secret-token', json.dumps(notification.request_payload))

    @patch('whatsapp.tasks.send_template_message')
    def test_successful_task_sends_exact_five_fields_and_is_idempotent(self, send):
        department = Department.objects.create(name='Sales', slug='sales-task')
        member = DepartmentMember.objects.create(
            department=department, name='Employee', whatsapp_number='+919876543210',
        )
        enquiry, _ = create_enquiry({
            'customer_name': 'Alice', 'phone_number': '+15551234567', 'category': 'Sales',
            'message': 'Pricing', 'business_number': '+15550009999',
        })
        notification = Notification.objects.get(enquiry=enquiry, recipient=member)
        send.return_value = ({'messages': [{'id': 'wamid.out'}]}, {'safe': 'payload'}, 200)

        send_department_notification.apply(args=[notification.pk]).get()
        send_department_notification.apply(args=[notification.pk]).get()

        notification.refresh_from_db()
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(notification.whatsapp_message_id, 'wamid.out')
        self.assertIsNotNone(notification.sent_at)
        send.assert_called_once()
        args, kwargs = send.call_args
        self.assertEqual(args[0], '+919876543210')
        self.assertEqual(args[1][:4], ['Alice', '+15551234567', 'Sales', 'Pricing'])
        self.assertEqual(len(args[1]), 5)


@override_settings(SECURE_SSL_REDIRECT=False)
class ConversationAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent', password='password123', role='editor')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        configuration = WhatsAppConfiguration.load()
        configuration.business_number = '+15550009999'
        configuration.phone_number_id = 'company-phone-id'
        configuration.meta_access_token = 'secret-token'
        configuration.save()
        self.enquiry, _ = create_enquiry(
            {'phone_number': '+15551234567', 'message': 'Hello', 'business_number': '+15550009999'},
            whatsapp_message_id='wamid.incoming',
        )

    def test_list_contains_same_enquiry_lead_and_message_history(self):
        response = self.client.get('/api/whatsapp/conversations/')
        self.assertEqual(response.status_code, 200)
        item = response.data['results'][0]
        self.assertEqual(item['id'], self.enquiry.id)
        self.assertEqual(item['last_message'], 'Hello')
        self.assertNotIn('messages', item)

    @patch('whatsapp.views.send_text_message')
    def test_agent_can_send_and_persist_reply(self, send):
        send.return_value = ({'messages': [{'id': 'wamid.reply'}]}, {'type': 'text'}, 200)
        response = self.client.post(
            f'/api/whatsapp/conversations/{self.enquiry.id}/', {'message': 'Hello Alice'}, format='json',
        )
        self.assertEqual(response.status_code, 201)
        reply = WhatsAppMessage.objects.get(whatsapp_message_id='wamid.reply')
        self.assertEqual(reply.direction, 'outgoing')
        self.assertEqual(reply.status, 'sent')

    @patch('whatsapp.views.send_media_message')
    def test_agent_can_upload_and_send_attachment(self, send_media):
        send_media.return_value = (
            {'messages': [{'id': 'wamid.attachment'}]}, {'type': 'document'}, 200, 'document',
        )
        attachment = SimpleUploadedFile('proposal.pdf', b'%PDF-1.4 test', content_type='application/pdf')

        response = self.client.post(
            f'/api/whatsapp/conversations/{self.enquiry.id}/',
            {'message': 'Our proposal', 'file': attachment}, format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        message = WhatsAppMessage.objects.get(whatsapp_message_id='wamid.attachment')
        self.assertEqual(message.message_type, 'document')
        self.assertEqual(message.content, 'Our proposal')
        self.assertEqual(message.attachment_name, 'proposal.pdf')
        self.assertEqual(message.attachment_content_type, 'application/pdf')
        self.assertTrue(message.attachment)
        attachment_url = response.data['messages'][-1]['attachment_url']
        download = self.client.get(f'/api{attachment_url}')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), b'%PDF-1.4 test')

        other_enquiry, _ = create_enquiry(
            {'phone_number': '+15557654321', 'message': 'Other', 'business_number': '+15550009999'},
            whatsapp_message_id='wamid.other',
        )
        wrong_conversation_url = attachment_url.replace(
            f'/conversations/{self.enquiry.id}/', f'/conversations/{other_enquiry.id}/',
        )
        self.assertEqual(self.client.get(f'/api{wrong_conversation_url}').status_code, 404)

    @patch('whatsapp.views.send_media_message')
    def test_agent_can_send_multiple_attachments(self, send_media):
        send_media.side_effect = [
            ({'messages': [{'id': 'wamid.file-one'}]}, {'type': 'document'}, 200, 'document'),
            ({'messages': [{'id': 'wamid.file-two'}]}, {'type': 'image'}, 200, 'image'),
        ]
        files = [
            SimpleUploadedFile('details.txt', b'details', content_type='text/plain'),
            SimpleUploadedFile('photo.png', b'png-data', content_type='image/png'),
        ]

        response = self.client.post(
            f'/api/whatsapp/conversations/{self.enquiry.id}/',
            {'message': 'Please review', 'files': files}, format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(send_media.call_count, 2)
        self.assertTrue(WhatsAppMessage.objects.filter(whatsapp_message_id='wamid.file-one').exists())
        self.assertTrue(WhatsAppMessage.objects.filter(whatsapp_message_id='wamid.file-two').exists())

    def test_opening_conversation_can_mark_incoming_messages_read(self):
        response = self.client.patch(
            f'/api/whatsapp/conversations/{self.enquiry.id}/read/', {'is_read': True}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 0)
        self.assertIsNotNone(self.enquiry.messages.get(direction='incoming').seen_at)

    def test_conversation_can_be_marked_unread_again(self):
        self.client.patch(
            f'/api/whatsapp/conversations/{self.enquiry.id}/read/', {'is_read': True}, format='json',
        )
        response = self.client.patch(
            f'/api/whatsapp/conversations/{self.enquiry.id}/read/', {'is_read': False}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)


@override_settings(SECURE_SSL_REDIRECT=False)
class WhatsAppTenantIsolationTests(TestCase):
    def setUp(self):
        from users.models import Tenant
        self.tenant_1 = Tenant.objects.create(name='Tenant One', slug='tenant-one')
        self.tenant_2 = Tenant.objects.create(name='Tenant Two', slug='tenant-two')

        self.user_1 = User.objects.create_user(
            username='user_one', email='one@test.com', password='password123',
            tenant=self.tenant_1, role='owner',
        )
        self.user_2 = User.objects.create_user(
            username='user_two', email='two@test.com', password='password123',
            tenant=self.tenant_2, role='owner',
        )

        dept_1 = Department.objects.create(name='Dept 1', slug='dept-1', tenant=self.tenant_1)
        dept_2 = Department.objects.create(name='Dept 2', slug='dept-2', tenant=self.tenant_2)

        cust_1 = Customer.objects.create(whatsapp_number='+1111111111', full_name='Cust One', tenant=self.tenant_1)
        cust_2 = Customer.objects.create(whatsapp_number='+2222222222', full_name='Cust Two', tenant=self.tenant_2)

        self.enquiry_1 = Enquiry.objects.create(
            tenant=self.tenant_1, customer=cust_1, department=dept_1, message='Message One',
        )
        self.enquiry_2 = Enquiry.objects.create(
            tenant=self.tenant_2, customer=cust_2, department=dept_2, message='Message Two',
        )

        self.msg_1 = WhatsAppMessage.objects.create(
            whatsapp_message_id='wamid.t1', customer=cust_1, enquiry=self.enquiry_1,
            direction='incoming', content='Message One', status='received',
        )
        self.msg_2 = WhatsAppMessage.objects.create(
            whatsapp_message_id='wamid.t2', customer=cust_2, enquiry=self.enquiry_2,
            direction='incoming', content='Message Two', status='received',
        )

        self.client = APIClient()

    def test_conversation_list_isolated_to_tenant(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get('/api/whatsapp/conversations/')
        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.enquiry_1.id, ids)
        self.assertNotIn(self.enquiry_2.id, ids)

    def test_conversation_detail_denied_for_other_tenant(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get(f'/api/whatsapp/conversations/{self.enquiry_2.id}/')
        self.assertEqual(response.status_code, 404)

    def test_conversation_read_status_denied_for_other_tenant(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.patch(
            f'/api/whatsapp/conversations/{self.enquiry_2.id}/read/',
            {'is_read': True}, format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_enquiry_csv_export_isolated_to_tenant(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get('/api/whatsapp/enquiries/export/?range=week')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(self.enquiry_1.reference, content)
        self.assertNotIn(self.enquiry_2.reference, content)

