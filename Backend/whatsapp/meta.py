import json
import logging
import ssl
import uuid
from urllib import error, request

from django.conf import settings

from .models import WhatsAppConfiguration
from .services import normalize_meta_recipient

logger = logging.getLogger(__name__)


class MetaAPIError(RuntimeError):
    def __init__(self, message, *, http_status=None, code='', subcode='', fbtrace_id='', response_payload=None,
                 request_payload=None):
        super().__init__(message)
        self.http_status = http_status
        self.code = str(code or '')
        self.subcode = str(subcode or '')
        self.fbtrace_id = fbtrace_id or ''
        self.response_payload = response_payload or {}
        self.request_payload = request_payload or {}


class MetaAPIPermanentError(MetaAPIError):
    """A request Meta rejected permanently and that should not be retried."""


def _configuration(business_number):
    configuration = WhatsAppConfiguration.for_business_number(business_number)
    if not configuration:
        raise MetaAPIPermanentError(f'WhatsApp configuration is missing for business number {business_number}')
    raw_token = configuration.meta_access_token
    if raw_token and configuration.tenant:
        try:
            from organization.services.crypto_service import decrypt_tenant_secret
            token = decrypt_tenant_secret(configuration.tenant, raw_token) or raw_token
        except Exception:
            token = raw_token
    else:
        token = raw_token or settings.WHATSAPP_ACCESS_TOKEN
    phone_number_id = configuration.phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID

    required = (
        ('WHATSAPP_ACCESS_TOKEN', token), ('WHATSAPP_PHONE_NUMBER_ID', phone_number_id),
        ('WHATSAPP_API_VERSION', configuration.api_version),
        ('WHATSAPP_TEMPLATE_NAME', configuration.notification_template),
        ('WHATSAPP_TEMPLATE_LANGUAGE', configuration.template_language),
    )
    missing = [name for name, value in required if not value]
    if missing:
        raise MetaAPIPermanentError(f'Missing WhatsApp configuration: {", ".join(missing)}')
    return configuration, token, phone_number_id


def build_template_request(to, parameters, *, business_number):
    configuration, token, phone_number_id = _configuration(business_number)
    recipient = normalize_meta_recipient(to)
    payload = {
        'messaging_product': 'whatsapp', 'to': recipient, 'type': 'template',
        'template': {
            'name': configuration.notification_template,
            'language': {'code': configuration.template_language},
            'components': [{'type': 'body', 'parameters': [
                {'type': 'text', 'text': str(value or '-')} for value in parameters
            ]}],
        },
    }
    url = f'https://graph.facebook.com/{configuration.api_version}/{phone_number_id}/messages'
    return url, token, payload


def build_text_request(to, text, *, business_number):
    """Build a Cloud API free-form text request for an active customer conversation."""
    configuration, token, phone_number_id = _configuration(business_number)
    recipient = normalize_meta_recipient(to)
    content = (text or '').strip()
    if not content:
        raise MetaAPIPermanentError('Message cannot be empty')
    if len(content) > 4096:
        raise MetaAPIPermanentError('Message cannot exceed 4096 characters')
    payload = {
        'messaging_product': 'whatsapp', 'recipient_type': 'individual',
        'to': recipient, 'type': 'text', 'text': {'preview_url': False, 'body': content},
    }
    return f'https://graph.facebook.com/{configuration.api_version}/{phone_number_id}/messages', token, payload


def _media_type(content_type):
    if content_type.startswith('image/'):
        return 'image'
    if content_type.startswith('audio/'):
        return 'audio'
    if content_type.startswith('video/'):
        return 'video'
    return 'document'


def upload_media(uploaded_file, *, business_number):
    configuration, token, phone_number_id = _configuration(business_number)
    boundary = f'----Wavely{uuid.uuid4().hex}'
    content_type = uploaded_file.content_type or 'application/octet-stream'
    filename = uploaded_file.name.replace('"', '')
    body = b''.join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\n{content_type}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
         f'Content-Type: {content_type}\r\n\r\n').encode(),
        uploaded_file.read(), f'\r\n--{boundary}--\r\n'.encode(),
    ])
    req = request.Request(
        f'https://graph.facebook.com/{configuration.api_version}/{phone_number_id}/media', data=body, method='POST',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': f'multipart/form-data; boundary={boundary}'},
    )
    try:
        with request.urlopen(req, timeout=settings.WHATSAPP_API_TIMEOUT) as response:
            result = json.loads(response.read())
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        detail = exc.read().decode(errors='replace') if isinstance(exc, error.HTTPError) else str(exc)
        raise MetaAPIError(f'Unable to upload attachment to Meta: {detail[:500]}') from exc
    if not result.get('id'):
        raise MetaAPIError('Meta accepted no media identifier.')
    return result['id'], _media_type(content_type)


def send_media_message(to, uploaded_file, caption='', *, business_number):
    media_id, media_type = upload_media(uploaded_file, business_number=business_number)
    configuration, token, phone_number_id = _configuration(business_number)
    media = {'id': media_id}
    if media_type == 'document':
        media['filename'] = uploaded_file.name
    if caption and media_type in {'image', 'video', 'document'}:
        media['caption'] = caption
    payload = {
        'messaging_product': 'whatsapp', 'recipient_type': 'individual',
        'to': normalize_meta_recipient(to), 'type': media_type, media_type: media,
    }
    result, payload, status_code = _send_request(
        f'https://graph.facebook.com/{configuration.api_version}/{phone_number_id}/messages', token, payload,
    )
    return result, payload, status_code, media_type


def _send_request(url, token, payload):
    req = request.Request(
        url, data=json.dumps(payload).encode(), method='POST',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    )
    ssl_context = None
    if settings.WHATSAPP_DISABLE_TLS_VERIFY:
        logger.warning('TLS certificate verification is disabled for the Meta API request')
        ssl_context = ssl._create_unverified_context()
    try:
        with request.urlopen(req, timeout=settings.WHATSAPP_API_TIMEOUT, context=ssl_context) as response:
            return json.loads(response.read()), payload, response.status
    except error.HTTPError as exc:
        raw_detail = exc.read().decode(errors='replace')
        try:
            response_payload = json.loads(raw_detail)
        except json.JSONDecodeError:
            response_payload = {'detail': raw_detail[:2000]}
        meta_error = response_payload.get('error', {})
        message = meta_error.get('message') or f'Meta API returned HTTP {exc.code}'
        exception_type = MetaAPIPermanentError if 400 <= exc.code < 500 and exc.code not in {408, 429} else MetaAPIError
        if exc.code == 403 or str(meta_error.get('code', '')) == '200':
            logger.error(
                'Meta WhatsApp authorization failed; verify System User, WABA assignment, access token, '
                'whatsapp_business_messaging permission, and Phone Number ID'
            )
        raise exception_type(
            message, http_status=exc.code, code=meta_error.get('code'), subcode=meta_error.get('error_subcode'),
            fbtrace_id=meta_error.get('fbtrace_id'), response_payload=response_payload, request_payload=payload,
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise MetaAPIError('Unable to reach Meta API', request_payload=payload) from exc


def send_template_message(to, parameters, *, business_number):
    try:
        url, token, payload = build_template_request(to, parameters, business_number=business_number)
    except ValueError as exc:
        raise MetaAPIPermanentError(str(exc)) from exc
    return _send_request(url, token, payload)


def send_text_message(to, text, *, business_number):
    try:
        url, token, payload = build_text_request(to, text, business_number=business_number)
    except ValueError as exc:
        raise MetaAPIPermanentError(str(exc)) from exc
    return _send_request(url, token, payload)
