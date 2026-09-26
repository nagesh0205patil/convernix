"""SMTP credentials are encrypted with a key kept outside the database."""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables


@sensitive_variables()
def cipher():
    key = settings.SMTP_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured('SMTP_ENCRYPTION_KEY must be configured on the server.')
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeError):
        raise ImproperlyConfigured('SMTP_ENCRYPTION_KEY is invalid.') from None


@sensitive_variables()
def encrypt_secret(value):
    return cipher().encrypt(value.encode('utf-8')).decode('ascii') if value else ''


@sensitive_variables()
def decrypt_secret(value):
    if not value:
        return ''
    try:
        return cipher().decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError):
        raise ImproperlyConfigured('SMTP credentials cannot be decrypted. Check the server encryption key or replace the credentials.') from None
