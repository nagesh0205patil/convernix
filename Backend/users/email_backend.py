"""Read the current SMTP configuration on every send; never cache credentials."""
from copy import copy
from email.utils import formataddr

from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.views.decorators.debug import sensitive_variables

from .models import SMTPConfiguration
from .smtp_crypto import decrypt_secret


class DatabaseSMTPBackend(BaseEmailBackend):
    @sensitive_variables()
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        try:
            configuration = SMTPConfiguration.objects.filter(pk=1, enabled=True).first()
            if configuration is None:
                raise ImproperlyConfigured('Enable SMTP configuration in Django admin before sending invitations.')
            configuration.full_clean()
            connection = SMTPEmailBackend(
                host=configuration.host,
                port=configuration.port,
                username=decrypt_secret(configuration.username_encrypted) if configuration.use_authentication else '',
                password=decrypt_secret(configuration.password_encrypted) if configuration.use_authentication else '',
                use_tls=configuration.security == 'starttls',
                use_ssl=configuration.security == 'ssl',
                timeout=configuration.timeout,
                fail_silently=self.fail_silently,
            )
            sender = formataddr((configuration.from_name, configuration.from_email))
            messages = []
            for message in email_messages:
                message = copy(message)
                message.from_email = sender
                messages.append(message)
            return connection.send_messages(messages)
        except Exception:
            if self.fail_silently:
                return 0
            raise
