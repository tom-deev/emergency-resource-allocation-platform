import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time


logger = logging.getLogger(__name__)

DEFAULT_TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 hours
OTP_CHALLENGE_TTL_SECONDS = 5 * 60       # 5 minutes
OTP_MAX_ATTEMPTS = 5

TOKEN_PURPOSE_ACCESS = "ACCESS"
TOKEN_PURPOSE_OTP_CHALLENGE = "OTP_CHALLENGE"

_EPHEMERAL_FALLBACK_SECRET = None


class AuthError(Exception):
    """Raised when authentication fails (HTTP 401)."""


class ForbiddenError(Exception):
    """Raised when an authenticated user lacks the required role (HTTP 403)."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist (HTTP 404)."""


def _get_signing_secret() -> bytes:
    """
    Return the HMAC signing secret from the AUTH_TOKEN_SECRET environment variable.

    If AUTH_TOKEN_SECRET is not configured (for example during isolated unit tests),
    a random per-process secret is generated at runtime so no secret is ever hardcoded.
    """
    global _EPHEMERAL_FALLBACK_SECRET

    env_secret = os.environ.get("AUTH_TOKEN_SECRET")
    if env_secret and env_secret.strip():
        return env_secret.strip().encode("utf-8")

    if _EPHEMERAL_FALLBACK_SECRET is None:
        logger.warning(
            "AUTH_TOKEN_SECRET environment variable is not set; "
            "using an ephemeral per-process secret."
        )
        _EPHEMERAL_FALLBACK_SECRET = secrets.token_hex(32).encode("utf-8")

    return _EPHEMERAL_FALLBACK_SECRET


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def _sign_payload(payload: dict) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_segment = _b64url_encode(payload_bytes)

    signature = hmac.new(
        _get_signing_secret(),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    signature_segment = _b64url_encode(signature)

    return f"{payload_segment}.{signature_segment}"


def create_token(user: dict, ttl_seconds: int | None = None) -> str:
    """Create a lightweight HMAC-SHA256 operational ACCESS token with expiry."""
    if ttl_seconds is None:
        raw_ttl = os.environ.get("AUTH_TOKEN_TTL_SECONDS")
        try:
            ttl_seconds = int(raw_ttl) if raw_ttl else DEFAULT_TOKEN_TTL_SECONDS
        except ValueError:
            ttl_seconds = DEFAULT_TOKEN_TTL_SECONDS

    now = int(time.time())
    payload = {
        "purpose": TOKEN_PURPOSE_ACCESS,
        "sub": user.get("userId"),
        "username": user.get("username"),
        "role": user.get("role"),
        "iat": now,
        "exp": now + int(ttl_seconds),
    }
    return _sign_payload(payload)


def create_otp_challenge_token(
    user: dict,
    challenge_id: str,
    ttl_seconds: int = OTP_CHALLENGE_TTL_SECONDS,
) -> str:
    """
    Create a short-lived HMAC-SHA256 OTP_CHALLENGE token.
    This token is NEVER accepted as an operational ACCESS token.
    """
    now = int(time.time())
    payload = {
        "purpose": TOKEN_PURPOSE_OTP_CHALLENGE,
        "challengeId": challenge_id,
        "sub": user.get("userId"),
        "username": user.get("username"),
        "role": user.get("role"),
        "iat": now,
        "exp": now + int(ttl_seconds),
    }
    return _sign_payload(payload)


def generate_otp_code() -> str:
    """Generate a cryptographically secure 6-digit OTP using secrets."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp_code: str, challenge_id: str) -> str:
    """Hash a 6-digit OTP bound to its unique challenge ID."""
    return hashlib.sha256(
        f"{challenge_id}:{otp_code}".encode("utf-8")
    ).hexdigest()


def verify_token(token: str, expected_purpose: str = TOKEN_PURPOSE_ACCESS) -> dict:
    """Verify token signature, expiry, and explicit purpose; return decoded payload."""
    if not token or not isinstance(token, str) or "." not in token:
        raise AuthError("Invalid authentication token.")

    parts = token.split(".")
    if len(parts) != 2:
        raise AuthError("Invalid authentication token.")

    payload_segment, signature_segment = parts

    expected_signature = hmac.new(
        _get_signing_secret(),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        provided_signature = _b64url_decode(signature_segment)
    except Exception as exc:
        raise AuthError("Invalid authentication token.") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AuthError("Invalid authentication token.")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise AuthError("Invalid authentication token.") from exc

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or int(time.time()) >= exp:
        raise AuthError("Authentication token has expired.")

    if not payload.get("sub") or not payload.get("role"):
        raise AuthError("Invalid authentication token payload.")

    token_purpose = payload.get("purpose", TOKEN_PURPOSE_ACCESS)
    if token_purpose != expected_purpose:
        raise AuthError("Invalid token purpose.")

    if expected_purpose == TOKEN_PURPOSE_OTP_CHALLENGE and not payload.get("challengeId"):
        raise AuthError("Invalid OTP challenge token.")

    return payload


def extract_bearer_token(event: dict) -> str | None:
    """Extract Bearer token from API Gateway event headers (case-insensitive)."""
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        return None

    auth_header = None
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == "authorization":
            auth_header = value
            break

    if not auth_header or not isinstance(auth_header, str):
        return None

    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthError("Authorization header must use Bearer token format.")

    return parts[1].strip()


def authenticate_request(event: dict, allowed_roles=None) -> dict:
    """
    Validate the caller's operational ACCESS Bearer token and optionally
    enforce allowed roles. OTP_CHALLENGE tokens are always rejected (401).
    """
    token = extract_bearer_token(event)
    if not token:
        raise AuthError("Authentication required.")

    claims = verify_token(token, expected_purpose=TOKEN_PURPOSE_ACCESS)

    if allowed_roles is not None and claims.get("role") not in allowed_roles:
        raise ForbiddenError(
            "You do not have permission to perform this action."
        )

    return claims
