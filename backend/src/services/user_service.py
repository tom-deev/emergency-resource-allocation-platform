from datetime import datetime, timedelta, timezone
import hmac
import os
from uuid import uuid4

from constants import USER_ROLES
from services.email_service import EmailDeliveryError, send_operator_otp_email
from utils.auth import (
    AuthError,
    OTP_CHALLENGE_TTL_SECONDS,
    OTP_MAX_ATTEMPTS,
    TOKEN_PURPOSE_OTP_CHALLENGE,
    create_otp_challenge_token,
    generate_otp_code,
    hash_otp,
    verify_token,
)


def _parse_utc_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    normalized = ts.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


class UserService:
    def __init__(self, user_repository, otp_email_sender=None):
        self.user_repository = user_repository
        self.otp_email_sender = otp_email_sender or send_operator_otp_email

    @staticmethod
    def _get_value(user, field):
        if isinstance(user, dict):
            return user.get(field)

        return getattr(user, field, None)

    def create_user(self, user):
        username = self._get_value(user, "username")
        role = self._get_value(user, "role")

        if not username:
            raise ValueError("Username is required.")

        if role not in USER_ROLES:
            raise ValueError(f"Invalid user role: {role}")

        existing_user = self.user_repository.find_by_username(
            username
        )

        if existing_user:
            raise ValueError("Username already exists.")

        return self.user_repository.create(user)

    def authenticate_user(self, username, password_hash):
        if not username:
            raise ValueError("Username is required.")

        if not password_hash:
            raise ValueError("Password is required.")

        user = self.user_repository.find_by_username(username)

        if user is None:
            raise ValueError("Invalid username or password.")

        if user.get("passwordHash") != password_hash:
            raise ValueError("Invalid username or password.")

        return user

    def issue_operator_otp(self, user, ttl_seconds: int = OTP_CHALLENGE_TTL_SECONDS):
        """
        Issue a cryptographically secure 6-digit OTP challenge for a
        RESOURCE_OPERATOR. Invalidates any prior active challenge.

        Delivery modes:
        - `gmail` (default): sends OTP via Gmail SMTP STARTTLS. Never prints OTP to terminal.
        - `console` (explicit opt-in only when OTP_DELIVERY_MODE=console AND LOCAL_OTP_CONSOLE=true):
          local demonstration fallback.

        If delivery fails, the newly created challenge is invalidated immediately
        so no usable challenge remains, and no ACCESS token is ever issued.
        """
        delivery_mode = (os.environ.get("OTP_DELIVERY_MODE") or "gmail").strip().lower()
        local_console = (os.environ.get("LOCAL_OTP_CONSOLE") or "false").strip().lower() == "true"

        user_id = self._get_value(user, "userId")
        username = self._get_value(user, "username")
        role = self._get_value(user, "role")

        if role != "RESOURCE_OPERATOR":
            raise ValueError("OTP challenge is only required for RESOURCE_OPERATOR accounts.")

        challenge_id = uuid4().hex
        otp_code = generate_otp_code()
        otp_hash = hash_otp(otp_code, challenge_id)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=int(ttl_seconds))
        ).isoformat()

        self.user_repository.set_otp_challenge(
            user_id=user_id,
            challenge_id=challenge_id,
            otp_hash=otp_hash,
            expires_at=expires_at,
            max_attempts=OTP_MAX_ATTEMPTS,
        )

        if delivery_mode == "gmail":
            try:
                self.otp_email_sender(
                    username=username,
                    otp_code=otp_code,
                    ttl_seconds=int(ttl_seconds),
                )
            except (EmailDeliveryError, Exception) as exc:
                self.user_repository.invalidate_otp_challenge(user_id, challenge_id)
                raise RuntimeError(
                    "Unable to deliver login OTP email. Please try again."
                ) from exc
        elif delivery_mode == "console" and local_console:
            print(
                f"[LOCAL DEMO ONLY] Resource Operator OTP for '{username}': {otp_code} "
                f"(valid for {int(ttl_seconds) // 60} minutes, single-use)",
                flush=True,
            )
        else:
            self.user_repository.invalidate_otp_challenge(user_id, challenge_id)
            raise RuntimeError(
                "Operator OTP delivery channel is not configured for this environment."
            )

        challenge_token = create_otp_challenge_token(
            {"userId": user_id, "username": username, "role": role},
            challenge_id=challenge_id,
            ttl_seconds=ttl_seconds,
        )

        return {
            "challengeToken": challenge_token,
            "expiresInSeconds": int(ttl_seconds),
        }

    def verify_operator_otp(self, challenge_token: str, otp_code: str):
        """
        Verify an OTP challenge token and 6-digit OTP code atomically.

        Enforces:
        - Valid OTP_CHALLENGE token signature, expiry, and purpose
        - Active challengeId match (invalidates older challenges)
        - Not expired, not used, attempts < 5
        - Constant-time OTP hash check
        - Atomic single-use consumption (prevents concurrent replay)
        """
        if not challenge_token or not isinstance(challenge_token, str):
            raise AuthError("OTP challenge token is required.")

        if (
            not otp_code
            or not isinstance(otp_code, str)
            or not otp_code.strip().isdigit()
            or len(otp_code.strip()) != 6
        ):
            raise AuthError("A valid 6-digit OTP is required.")

        otp_clean = otp_code.strip()
        claims = verify_token(
            challenge_token,
            expected_purpose=TOKEN_PURPOSE_OTP_CHALLENGE,
        )

        user_id = claims["sub"]
        challenge_id = claims["challengeId"]

        user = self.user_repository.get_by_id(user_id)
        if not user or user.get("role") != "RESOURCE_OPERATOR":
            raise AuthError("Invalid OTP challenge.")

        if user.get("otpChallengeId") != challenge_id:
            raise AuthError("OTP challenge has been superseded or is invalid.")

        if user.get("otpUsed"):
            raise AuthError("OTP challenge has already been used or invalidated.")

        expires_dt = _parse_utc_iso(user.get("otpExpiresAt"))
        if expires_dt is None or datetime.now(timezone.utc) >= expires_dt:
            self.user_repository.invalidate_otp_challenge(user_id, challenge_id)
            raise AuthError("OTP has expired. Please request a new code.")

        attempts = int(user.get("otpAttempts", 0))
        max_attempts = int(user.get("otpMaxAttempts", OTP_MAX_ATTEMPTS))
        if attempts >= max_attempts:
            self.user_repository.invalidate_otp_challenge(user_id, challenge_id)
            raise AuthError("Maximum OTP verification attempts exceeded.")

        stored_hash = user.get("otpHash") or ""
        candidate_hash = hash_otp(otp_clean, challenge_id)

        if not stored_hash or not hmac.compare_digest(stored_hash, candidate_hash):
            updated = self.user_repository.increment_otp_attempts(user_id, challenge_id)
            new_attempts = int(updated.get("otpAttempts", attempts + 1)) if updated else max_attempts
            if new_attempts >= max_attempts:
                self.user_repository.invalidate_otp_challenge(user_id, challenge_id)
                raise AuthError(
                    "Maximum OTP verification attempts exceeded. Challenge invalidated."
                )
            remaining = max(0, max_attempts - new_attempts)
            raise AuthError(
                f"Invalid OTP code. {remaining} attempt(s) remaining."
            )

        consumed = self.user_repository.consume_otp_challenge(
            user_id=user_id,
            challenge_id=challenge_id,
            expected_otp_hash=candidate_hash,
        )
        if consumed is None:
            raise AuthError("OTP challenge has already been used or invalidated.")

        return {
            "userId": user["userId"],
            "username": user["username"],
            "role": user["role"],
        }

    def get_user(self, user_id):
        return self.user_repository.get_by_id(user_id)

    def get_all_users(self):
        return self.user_repository.get_all()

    def find_by_username(self, username):
        if not username:
            raise ValueError("Username is required.")

        return self.user_repository.find_by_username(username)
