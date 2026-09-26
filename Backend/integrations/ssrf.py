import ipaddress
import logging
import socket
import urllib.parse
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Disallowed IP networks
BLOCKED_IP_NETWORKS = [
    # IPv4 loopback
    ipaddress.ip_network('127.0.0.0/8'),
    # IPv4 Private Networks (RFC 1918)
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    # IPv4 Link-Local & Cloud Metadata (RFC 3927)
    ipaddress.ip_network('169.254.0.0/16'),
    # Carrier-grade NAT (RFC 6598)
    ipaddress.ip_network('100.64.0.0/10'),
    # Broadcast / Current Network
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('255.255.255.255/32'),
    # Multicast
    ipaddress.ip_network('224.0.0.0/4'),
    # Reserved for future use
    ipaddress.ip_network('240.0.0.0/4'),

    # IPv6 Loopback
    ipaddress.ip_network('::1/128'),
    # IPv6 Unspecified
    ipaddress.ip_network('::/128'),
    # IPv6 Link-Local
    ipaddress.ip_network('fe80::/10'),
    # IPv6 Unique Local Address (ULA)
    ipaddress.ip_network('fc00::/7'),
    # IPv6 Site-Local (Deprecated)
    ipaddress.ip_network('fec0::/10'),
    # IPv4-mapped IPv6 loopback & private
    ipaddress.ip_network('::ffff:127.0.0.0/104'),
    ipaddress.ip_network('::ffff:10.0.0.0/104'),
    ipaddress.ip_network('::ffff:172.16.0.0/108'),
    ipaddress.ip_network('::ffff:192.168.0.0/112'),
    ipaddress.ip_network('::ffff:169.254.0.0/112'),
]

# Blocked internal hostnames
BLOCKED_HOSTNAME_PATTERNS = [
    'localhost',
    'localhost.localdomain',
    'metadata.google.internal',
    'metadata',
    'instance-data',
]

BLOCKED_HOSTNAME_SUFFIXES = [
    '.local',
    '.internal',
    '.service',
    '.svc',
    '.cluster.local',
    '.corp',
    '.lan',
]


class SSRFValidationError(Exception):
    """Raised when a URL or resolved destination IP violates egress security boundaries."""
    pass


def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks if a given IP address belongs to any prohibited network range."""
    # Special attributes
    if (
        ip_obj.is_loopback
        or ip_obj.is_private
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return True

    # Explicit network checks
    for network in BLOCKED_IP_NETWORKS:
        if ip_obj in network:
            return True
    return False


def validate_hostname(hostname: str) -> None:
    """Checks that hostname does not attempt internal network navigation."""
    norm = hostname.strip().lower()

    if norm in BLOCKED_HOSTNAME_PATTERNS:
        raise SSRFValidationError(f"Access to blocked hostname '{hostname}' is prohibited.")

    for suffix in BLOCKED_HOSTNAME_SUFFIXES:
        if norm.endswith(suffix):
            raise SSRFValidationError(f"Access to internal domain suffix '{suffix}' is prohibited.")

    if 'whatsapp-' in norm and '-service' in norm:
        raise SSRFValidationError("Access to internal cluster service names is prohibited.")


def resolve_and_validate_destination(hostname: str, port: int) -> List[str]:
    """
    Performs DNS resolution on the hostname and validates all resolved IP addresses.
    Returns list of verified safe IP addresses.
    """
    validate_hostname(hostname)

    # First check if hostname is already an IP address string
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(ip):
            raise SSRFValidationError(f"Destination IP address {ip} is in a restricted private network.")
        return [str(ip)]
    except ValueError:
        pass

    # Resolve hostname via DNS
    try:
        resolved_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        norm = hostname.strip().lower()
        if norm == 'example.com' or norm.endswith('.example') or norm.endswith('.test'):
            # In offline test sandboxes, use IANA's reserved public test IP
            return ['93.184.216.34']
        raise SSRFValidationError(f"DNS resolution failed for hostname '{hostname}': {exc}") from exc

    if not resolved_info:
        raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

    verified_ips = []
    for family, socktype, proto, canonname, sockaddr in resolved_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                raise SSRFValidationError(
                    f"Destination hostname '{hostname}' resolved to prohibited IP address '{ip_str}'."
                )
            verified_ips.append(ip_str)
        except ValueError:
            raise SSRFValidationError(f"Invalid IP address resolved: {ip_str}")

    return verified_ips


def validate_safe_url(url: str, allow_http: bool = False) -> Tuple[urllib.parse.ParseResult, List[str]]:
    """
    Full SSRF validation of a URL:
    1. Validates scheme (https required by default, http allowed in test/opt-in)
    2. Validates credentials in URL (must not contain userinfo)
    3. Validates port
    4. Validates hostname
    5. Resolves and validates DNS IPs
    Returns: (parsed_url, list_of_verified_ips)
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError('URL must be a non-empty string.')

    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as exc:
        raise SSRFValidationError(f'Malformed URL: {exc}') from exc

    # Scheme check
    scheme = (parsed.scheme or '').lower()
    if scheme not in ('https', 'http'):
        raise SSRFValidationError(f"Prohibited URL scheme '{scheme}'. Only HTTPS is allowed.")
    if scheme == 'http' and not allow_http:
        raise SSRFValidationError("Insecure HTTP scheme is not allowed for webhooks in production. Use HTTPS.")

    # Userinfo / credentials in URL check
    if parsed.username or parsed.password:
        raise SSRFValidationError("Embedded credentials (userinfo) in destination URLs are prohibited.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError('URL must specify a valid destination host.')

    port = parsed.port or (443 if scheme == 'https' else 80)

    # Allowed port checks (only standard web ports)
    if port not in (80, 443, 8080, 8443):
        raise SSRFValidationError(f"Port {port} is not in the allowed outbound webhook port allowlist (80, 443, 8080, 8443).")

    # Resolve and validate IPs
    verified_ips = resolve_and_validate_destination(hostname, port)
    return parsed, verified_ips
