from smtplib import SMTPAuthenticationError
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, get_connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .admin import SMTPConfigurationForm
from .models import SMTPConfiguration
from .smtp_crypto import decrypt_secret, encrypt_secret


@override_settings(
    SMTP_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    EMAIL_BACKEND='users.email_backend.DatabaseSMTPBackend',
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class SMTPTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser(
            username='smtp-owner', email='smtp-owner@example.com', password='password123',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def form_data(self, **changes):
        data = {
            'enabled': True, 'host': 'smtp.example.com', 'port': 587, 'security': 'starttls',
            'use_authentication': True, 'smtp_username': 'private-login',
            'smtp_password': 'private-password', 'from_email': 'invites@example.com',
            'from_name': 'Wavely', 'timeout': 15,
        }
        data.update(changes)
        return data

    def configure(self):
        form = SMTPConfigurationForm(data=self.form_data())
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_admin_form_stores_only_ciphertext_and_blank_inputs_keep_secrets(self):
        configuration = self.configure()
        configuration.refresh_from_db()
        stored = SMTPConfiguration.objects.values().get()
        self.assertNotIn('private-login', str(stored))
        self.assertNotIn('private-password', str(stored))
        self.assertEqual(decrypt_secret(configuration.username_encrypted), 'private-login')
        self.assertEqual(decrypt_secret(configuration.password_encrypted), 'private-password')
        original = configuration.password_encrypted
        form = SMTPConfigurationForm(instance=configuration, data=self.form_data(smtp_username='', smtp_password='', port=465, security='ssl'))
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.password_encrypted, original)
        replacement = SMTPConfigurationForm(instance=updated, data=self.form_data(smtp_username='', smtp_password='replacement-secret'))
        self.assertTrue(replacement.is_valid(), replacement.errors)
        self.assertEqual(decrypt_secret(replacement.save().password_encrypted), 'replacement-secret')

    def test_admin_never_renders_plaintext_and_denies_regular_staff(self):
        configuration = self.configure()
        self.client.force_login(self.owner)
        url = reverse('admin:users_smtpconfiguration_change', args=[configuration.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'private-login')
        self.assertNotContains(response, 'private-password')
        self.assertContains(response, configuration.password_encrypted)
        self.assertEqual(self.client.get(reverse('admin:users_smtpconfiguration_add')).status_code, 403)
        staff = get_user_model().objects.create_user(username='smtp-staff', email='smtp-staff@example.com', is_staff=True, role='admin')
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_missing_key_and_invalid_configuration_are_rejected(self):
        with override_settings(SMTP_ENCRYPTION_KEY=''):
            form = SMTPConfigurationForm(data=self.form_data())
            self.assertFalse(form.is_valid())
            self.assertIn('smtp_password', form.errors)
        for changes in ({'port': 65536}, {'timeout': 0}, {'smtp_username': '', 'smtp_password': ''}):
            form = SMTPConfigurationForm(data=self.form_data(**changes))
            self.assertFalse(form.is_valid())

    def test_wrong_key_and_tampered_ciphertext_fail_closed(self):
        value = encrypt_secret('secret')
        with override_settings(SMTP_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertRaises(ImproperlyConfigured):
                decrypt_secret(value)
        with self.assertRaises(ImproperlyConfigured):
            decrypt_secret(value[:-8] + 'tampered')

    @patch('users.email_backend.SMTPEmailBackend')
    def test_smtp_uses_database_settings_and_refreshes_without_restart(self, smtp):
        configuration = self.configure()
        smtp.return_value.send_messages.return_value = 1
        connection = get_connection()
        original = EmailMessage('Subject', 'Body', 'old@example.com', ['recipient@example.com'])
        self.assertEqual(connection.send_messages([original]), 1)
        smtp.assert_called_once_with(host='smtp.example.com', port=587, username='private-login', password='private-password', use_tls=True, use_ssl=False, timeout=15, fail_silently=False)
        sent = smtp.return_value.send_messages.call_args.args[0][0]
        self.assertEqual(sent.from_email, 'Wavely <invites@example.com>')
        self.assertEqual(original.from_email, 'old@example.com')
        configuration.security = 'ssl'
        configuration.port = 465
        configuration.use_authentication = False
        configuration.save()
        connection.send_messages([original])
        self.assertTrue(smtp.call_args.kwargs['use_ssl'])
        self.assertFalse(smtp.call_args.kwargs['use_tls'])
        self.assertEqual(smtp.call_args.kwargs['username'], '')
        self.assertEqual(smtp.call_args.kwargs['password'], '')

    @patch('users.email_backend.SMTPEmailBackend')
    def test_invitation_uses_configured_sender_and_returns_success(self, smtp):
        self.configure()
        smtp.return_value.send_messages.return_value = 1
        response = self.client.post('/api/iam/invitations/', {'email': 'invited@example.com', 'role': 'viewer', 'number_access': 'india'}, format='json')
        self.assertEqual(response.status_code, 201)
        sent = smtp.return_value.send_messages.call_args.args[0][0]
        self.assertEqual(sent.to, ['invited@example.com'])
        self.assertEqual(sent.from_email, 'Wavely <invites@example.com>')
        self.assertIn('?invite=', sent.body)
        self.assertFalse(get_user_model().objects.get(email='invited@example.com').is_active)

    @patch('users.email_backend.SMTPEmailBackend')
    def test_smtp_failure_is_sanitized_and_rolls_back_invitation(self, smtp):
        self.configure()
        smtp.return_value.send_messages.side_effect = SMTPAuthenticationError(535, b'private-password')
        response = self.client.post('/api/iam/invitations/', {'email': 'failed@example.com', 'role': 'viewer'}, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private-password', str(response.data))
        self.assertFalse(get_user_model().objects.filter(email='failed@example.com').exists())
        pending = get_user_model().objects.create_user(username='pending-smtp', email='pending-smtp@example.com', is_active=False, number_access='us')
        response = self.client.post('/api/iam/invitations/', {'email': pending.email, 'role': 'editor', 'number_access': 'india'}, format='json')
        self.assertEqual(response.status_code, 503)
        pending.refresh_from_db()
        self.assertEqual(pending.number_access, 'us')
        self.assertEqual(pending.role, 'viewer')

    @patch('users.email_backend.SMTPEmailBackend')
    def test_missing_disabled_configuration_and_zero_delivery_never_report_success(self, smtp):
        payload = {'email': 'unavailable@example.com', 'role': 'viewer'}
        self.assertEqual(self.client.post('/api/iam/invitations/', payload, format='json').status_code, 503)
        configuration = self.configure()
        configuration.enabled = False
        configuration.save()
        self.assertEqual(self.client.post('/api/iam/invitations/', payload, format='json').status_code, 503)
        smtp.assert_not_called()
        configuration.enabled = True
        configuration.save()
        smtp.return_value.send_messages.return_value = 0
        self.assertEqual(self.client.post('/api/iam/invitations/', payload, format='json').status_code, 503)
        self.assertFalse(get_user_model().objects.filter(email=payload['email']).exists())
