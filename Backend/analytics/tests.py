from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from campaigns.models import Campaign
from whatsapp.models import Customer, Department, Enquiry


@override_settings(SECURE_SSL_REDIRECT=False)
class AnalyticsReportingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='analyst', email='analyst@example.com', password='password123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        department = Department.objects.create(name='Analytics Sales', slug='analytics-sales')
        customer = Customer.objects.create(whatsapp_number='+15550000001', full_name='Alice')
        Enquiry.objects.create(customer=customer, department=department, message='Pricing')
        Campaign.objects.create(
            created_by=self.user, name='August campaign', message='Hello', status='running',
            sent_count=100, delivered_count=80, opened_count=40, clicked_count=10,
        )

    def test_dashboard_returns_real_period_aggregates(self):
        today = timezone.localdate()
        response = self.client.get('/api/analytics/dashboard/', {'year': today.year, 'month': today.month})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['totals']['enquiries'], 1)
        self.assertEqual(response.data['totals']['campaigns'], 1)
        self.assertEqual(response.data['totals']['sent'], 100)
        self.assertEqual(response.data['enquiry_statuses'][0]['status'], 'new')
        self.assertEqual(response.data['enquiry_teams'][0]['label'], 'Analytics Sales')

    def test_both_report_types_download_as_csv(self):
        today = timezone.localdate()
        for report_type in ('enquiries', 'campaigns'):
            response = self.client.get('/api/analytics/export/', {
                'type': report_type, 'year': today.year, 'month': today.month,
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
            self.assertIn(f'{report_type}_report_', response['Content-Disposition'])

    def test_invalid_period_is_rejected(self):
        response = self.client.get('/api/analytics/dashboard/', {'year': 'invalid', 'month': 13})
        self.assertEqual(response.status_code, 400)
