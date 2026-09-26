import base64
import hashlib
import hmac
import logging
import os
import struct
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class MfaService:
    """RFC 6238 Time-Based One-Time Password (TOTP) & Emergency Recovery Code Engine."""

    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a cryptographically secure 160-bit (20-byte) Base32 secret key."""
        random_bytes = os.urandom(20)
        return base64.b32encode(random_bytes).decode('ascii').rstrip('=')

    @staticmethod
    def get_provisioning_uri(secret: str, user_email: str, issuer: str = 'Convernix') -> str:
        """Construct standard otpauth:// URL for authenticator QR code generation."""
        import urllib.parse
        encoded_email = urllib.parse.quote(user_email)
        encoded_issuer = urllib.parse.quote(issuer)
        return f'otpauth://totp/{encoded_issuer}:{encoded_email}?secret={secret}&issuer={encoded_issuer}&algorithm=SHA1&digits=6&period=30'

    @staticmethod
    def _compute_totp(secret: str, interval: int) -> str:
        """Computes 6-digit TOTP code for a given 30-second interval."""
        # Pad secret to valid base32 boundary if needed
        padding_needed = (8 - len(secret) % 8) % 8
        padded_secret = secret + ('=' * padding_needed)
        key = base64.b32decode(padded_secret, casefold=True)
        counter_bytes = struct.pack('>Q', interval)
        mac = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = mac[-1] & 0x0f
        binary = struct.unpack('>I', mac[offset:offset + 4])[0] & 0x7fffffff
        code = binary % 1000000
        return f'{code:06d}'

    @classmethod
    def verify_totp(cls, secret: str, submitted_code: str, window: int = 1) -> bool:
        """
        Verifies submitted 6-digit code against secret with +/- window (30s drift allowance).
        Never logs the secret or submitted code.
        """
        if not secret or not submitted_code:
            return False
        clean_code = str(submitted_code).strip()
        if len(clean_code) != 6 or not clean_code.isdigit():
            return False

        current_interval = int(time.time()) // 30
        for offset in range(-window, window + 1):
            expected = cls._compute_totp(secret, current_interval + offset)
            if hmac.compare_digest(expected, clean_code):
                return True
        return False

    @staticmethod
    def generate_recovery_codes(count: int = 8) -> Tuple[List[str], List[str]]:
        """
        Generates one-time backup recovery codes.
        Returns: (plaintext_codes_for_user, hashed_codes_for_db)
        """
        plaintext_codes = []
        hashed_codes = []
        for _ in range(count):
            code = f'{os.urandom(4).hex()}-{os.urandom(4).hex()}'.upper()
            hashed = hashlib.sha256(code.encode('utf-8')).hexdigest()
            plaintext_codes.append(code)
            hashed_codes.append(hashed)
        return plaintext_codes, hashed_codes

    @classmethod
    def verify_and_consume_recovery_code(cls, user, submitted_code: str) -> bool:
        """
        Validates an emergency recovery code. If valid, consumes it to prevent replay attacks.
        """
        if not getattr(user, 'mfa_recovery_codes', None) or not submitted_code:
            return False
        
        submitted_hash = hashlib.sha256(str(submitted_code).strip().upper().encode('utf-8')).hexdigest()
        codes = list(user.mfa_recovery_codes)
        
        for idx, stored_hash in enumerate(codes):
            if hmac.compare_digest(stored_hash, submitted_hash):
                # Consume the code
                codes.pop(idx)
                user.mfa_recovery_codes = codes
                user.save(update_fields=['mfa_recovery_codes'])
                return True
        return False

