import uuid
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import status


class InboxAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'INBOX_ERROR'
    default_detail = 'An inbox error occurred.'

    def __init__(self, message=None, code=None, status_code=None, request_id=None):
        if status_code:
            self.status_code = status_code
        self.code = code or self.default_code
        self.message = str(message or self.default_detail)
        self.request_id = request_id or str(uuid.uuid4())
        super().__init__(detail=self.message, code=self.code)

    def to_response_data(self):
        return {
            'error': {
                'code': self.code,
                'message': self.message,
                'requestId': self.request_id,
            }
        }


class ConversationNotFoundException(InboxAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'CONVERSATION_NOT_FOUND'
    default_detail = 'The requested conversation was not found in the current tenant scope.'


class ConversationAlreadyAssignedException(InboxAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'CONVERSATION_ALREADY_ASSIGNED'
    default_detail = 'This conversation has already been claimed or assigned by another agent.'


class PermissionDeniedInboxException(InboxAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'PERMISSION_DENIED'
    default_detail = 'You do not have permission to perform this action.'


class DepartmentAccessDeniedException(InboxAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'DEPARTMENT_ACCESS_DENIED'
    default_detail = 'You do not have access to this department queue.'


class MessageSendFailedException(InboxAPIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'MESSAGE_SEND_FAILED'
    default_detail = 'Failed to deliver message via WhatsApp Meta Cloud API.'


class MetaAPIErrorException(InboxAPIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'META_API_ERROR'
    default_detail = 'Meta Cloud API reported an error.'


class MetaRateLimitedException(InboxAPIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = 'META_RATE_LIMITED'
    default_detail = 'WhatsApp Cloud API rate limit exceeded. Please back off.'


class AttachmentTooLargeException(InboxAPIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_code = 'ATTACHMENT_TOO_LARGE'
    default_detail = 'Attachment size exceeds maximum permitted limit.'


class AttachmentTypeNotAllowedException(InboxAPIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_code = 'ATTACHMENT_TYPE_NOT_ALLOWED'
    default_detail = 'Attachment file type or MIME type is not allowed.'


class InvalidConversationStateException(InboxAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'INVALID_CONVERSATION_STATE'
    default_detail = 'The conversation is not in a valid state for this transition.'


class TenantAccessDeniedException(InboxAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'TENANT_ACCESS_DENIED'
    default_detail = 'Access to this tenant organization resource is denied.'


def inbox_error_response(code: str, message: str, status_code: int = 400, request_id: str = None) -> Response:
    req_id = request_id or str(uuid.uuid4())
    return Response({
        'error': {
            'code': code,
            'message': message,
            'requestId': req_id,
        }
    }, status=status_code)

