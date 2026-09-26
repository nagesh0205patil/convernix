import re
from typing import Any, Dict, List, Tuple
from rest_framework.exceptions import ValidationError

ALLOWED_VARIABLES = {
    'lead.name': 'Customer / Lead full name',
    'lead.phone': 'Customer WhatsApp phone number',
    'lead.email': 'Customer email address',
    'lead.service': 'Requested service or subject',
    'department.name': 'Assigned department name',
    'agent.name': 'Assigned agent name',
    'conversation.initial_message': 'First message sent in conversation',
    'organization.name': 'Organization name',
    'event.created_at': 'Timestamp of event occurrence',
}

VARIABLE_REGEX = re.compile(r'\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}')

SYNTHETIC_DATA = {
    'lead.name': 'Rahul Sharma',
    'lead.phone': '+91 98765 43210',
    'lead.email': 'rahul.sharma@example.com',
    'lead.service': 'Enterprise CRM Suite',
    'department.name': 'Enterprise Sales',
    'agent.name': 'Priya Deshmukh',
    'conversation.initial_message': 'Hello, we would like a demo of your WhatsApp platform.',
    'organization.name': 'Convernix Cloud',
    'event.created_at': '2026-09-25 14:30 UTC',
}


class SafeTemplateEngine:
    """Safe, sandboxed template engine with allowlisted variable substitution and zero code execution."""

    @classmethod
    def extract_variables(cls, template_content: str) -> List[str]:
        """Finds all {{variable}} placeholders in the template string."""
        matches = VARIABLE_REGEX.findall(template_content or '')
        # Return unique list maintaining order
        seen = set()
        res = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                res.append(m)
        return res

    @classmethod
    def validate_content(cls, template_content: str) -> Tuple[bool, List[str]]:
        """Verifies that all variables used in template_content are in the ALLOWED_VARIABLES registry.

        Returns (is_valid, unknown_variables).
        """
        used_vars = cls.extract_variables(template_content)
        unknown = [v for v in used_vars if v not in ALLOWED_VARIABLES]
        if unknown:
            return False, unknown
        return True, []

    @classmethod
    def render(cls, template_content: str, context: Dict[str, Any], use_synthetic_fallbacks: bool = True) -> str:
        """Safely renders template using regex substitution. No eval, exec, or code execution."""
        def replacer(match):
            var_name = match.group(1).strip()
            if var_name in context:
                val = context[var_name]
                return str(val) if val is not None else ''
            if use_synthetic_fallbacks and var_name in SYNTHETIC_DATA:
                return SYNTHETIC_DATA[var_name]
            return f'[{var_name}]'

        return VARIABLE_REGEX.sub(replacer, template_content or '')

    @classmethod
    def generate_preview(cls, template_content: str, custom_sample_data: Dict[str, Any] = None) -> str:
        """Generates a synthetic rendered preview for administrative testing."""
        sample = dict(SYNTHETIC_DATA)
        if custom_sample_data:
            sample.update(custom_sample_data)
        return cls.render(template_content, sample, use_synthetic_fallbacks=True)

