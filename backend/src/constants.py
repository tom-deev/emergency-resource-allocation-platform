import os


USER_ROLES = (
    "DISPATCHER",
    "RESOURCE_OPERATOR",
)

INCIDENT_STATUSES = (
    "CREATED",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED",
    "AMBULANCE_ASSIGNED",
    "HOSPITAL_REQUESTED",
    "HOSPITAL_ACCEPTED",
    "HOSPITAL_REJECTED",
    "PATIENT_TRANSPORTED",
    "COMPLETED",
    "CANCELLED",
    "PENDING",
    "ALLOCATED",
    "IN_PROGRESS",
    "RESOLVED",
)

AMBULANCE_STATUSES = (
    "AVAILABLE",
    "BUSY",
    "OFFLINE",
)

HOSPITAL_STATUSES = (
    "ACTIVE",
    "INACTIVE",
)

INCIDENT_SEVERITIES = (
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
)

SEVERITY_TO_PRIORITY = {
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "LOW": "P4",
}

PRIORITY_RANK = {
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}

DEFAULT_WAITING_THRESHOLDS_MINUTES = {
    "P1": 5,
    "P2": 15,
    "P3": 30,
    "P4": 60,
}

RESERVATION_STATUSES = (
    "RESERVED",
    "CONFIRMED",
    "REJECTED",
    "RELEASED",
)

# Bound reservation history stored on an Incident item to stay well under DynamoDB's 400 KB limit.
MAX_RESERVATION_HISTORY = 20


def derive_priority(severity: str) -> str:
    """Derive deterministic queue priority (P1-P4) from incident severity."""
    return SEVERITY_TO_PRIORITY.get(severity, "P4")


def get_waiting_thresholds_minutes() -> dict:
    """
    Return configurable waiting-time thresholds (in minutes) per priority.

    Can be overridden via environment variables:
    WAIT_THRESHOLD_P1_MIN, WAIT_THRESHOLD_P2_MIN,
    WAIT_THRESHOLD_P3_MIN, WAIT_THRESHOLD_P4_MIN.
    """
    thresholds = {}
    for priority, default_val in DEFAULT_WAITING_THRESHOLDS_MINUTES.items():
        env_key = f"WAIT_THRESHOLD_{priority}_MIN"
        raw = os.environ.get(env_key)
        try:
            parsed = int(raw) if raw is not None else default_val
            thresholds[priority] = parsed if parsed > 0 else default_val
        except ValueError:
            thresholds[priority] = default_val
    return thresholds
