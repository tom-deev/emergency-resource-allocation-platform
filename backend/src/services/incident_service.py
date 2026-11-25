from datetime import datetime, timedelta, timezone

from constants import (
    INCIDENT_STATUSES,
    PRIORITY_RANK,
    derive_priority,
    get_waiting_thresholds_minutes,
)
from validation.incident import validate_incident_data


IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

ACTIVE_WAITING_STATUSES = {
    "CREATED",
    "UNDER_REVIEW",
    "VERIFIED",
    "AMBULANCE_ASSIGNED",
    "HOSPITAL_REQUESTED",
    "HOSPITAL_REJECTED",
    "PENDING",
}


def parse_utc_timestamp(ts: str | None) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp string into an aware UTC datetime."""
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


class IncidentService:
    """
    Service layer for incident-related business logic.
    """

    def __init__(self, incident_repository):
        self.incident_repository = incident_repository

    def create_incident(self, incident):
        """
        Validate and create an incident.

        Priority is always derived from severity on the backend.
        """
        if isinstance(incident, dict):
            validation_data = incident
        else:
            incident.priority = derive_priority(incident.severity)
            validation_data = vars(incident)

        validate_incident_data(validation_data)

        return self.incident_repository.create(incident)

    def get_incident(self, incident_id):
        """
        Retrieve an incident by ID.
        """
        return self.incident_repository.get_by_id(incident_id)

    def get_all_incidents(self):
        """
        Retrieve all incidents.
        """
        return self.incident_repository.get_all()

    @staticmethod
    def enrich_incident(incident_dict: dict, now_dt: datetime | None = None, thresholds: dict | None = None) -> dict:
        """
        Enrich an incident dictionary with derived priority, elapsed waiting time,
        time since last update, and overdue waiting indicator.
        """
        now_dt = now_dt or datetime.now(timezone.utc)
        thresholds = thresholds or get_waiting_thresholds_minutes()

        enriched = dict(incident_dict)
        priority = derive_priority(enriched.get("severity"))
        enriched["priority"] = priority

        created_dt = parse_utc_timestamp(enriched.get("createdAt"))
        updated_dt = parse_utc_timestamp(enriched.get("updatedAt")) or created_dt

        if created_dt is not None:
            elapsed_seconds = max(0, int((now_dt - created_dt).total_seconds()))
        else:
            elapsed_seconds = 0

        if updated_dt is not None:
            since_update_seconds = max(0, int((now_dt - updated_dt).total_seconds()))
        else:
            since_update_seconds = 0

        elapsed_minutes = elapsed_seconds // 60
        threshold_minutes = thresholds.get(priority, 60)
        is_overdue = (
            enriched.get("status") in ACTIVE_WAITING_STATUSES
            and elapsed_minutes >= threshold_minutes
        )

        enriched["elapsedWaitingSeconds"] = elapsed_seconds
        enriched["elapsedWaitingMinutes"] = elapsed_minutes
        enriched["sinceLastUpdateSeconds"] = since_update_seconds
        enriched["waitingThresholdMinutes"] = threshold_minutes
        enriched["isOverdue"] = is_overdue

        return enriched

    @classmethod
    def sort_incidents_by_priority(cls, incidents: list[dict], now_dt: datetime | None = None) -> list[dict]:
        """
        Deterministically sort incidents by:
        1. Severity priority (P1 -> P2 -> P3 -> P4)
        2. Reporting time (oldest createdAt first within the same priority)
        3. incidentId ascending as deterministic tie-breaker
        """
        now_dt = now_dt or datetime.now(timezone.utc)
        thresholds = get_waiting_thresholds_minutes()

        enriched_list = [
            cls.enrich_incident(item, now_dt=now_dt, thresholds=thresholds)
            for item in incidents
        ]

        def sort_key(item):
            rank = PRIORITY_RANK.get(item.get("priority"), 99)
            created_dt = parse_utc_timestamp(item.get("createdAt"))
            created_epoch = created_dt.timestamp() if created_dt is not None else float("inf")
            return (rank, created_epoch, str(item.get("incidentId", "")))

        return sorted(enriched_list, key=sort_key)

    def get_priority_queue(
        self,
        priority_filter: str | None = None,
        severity_filter: str | None = None,
        status_filter: str | None = None,
        date_ist: str | None = None,
        search: str | None = None,
        now_dt: datetime | None = None,
    ) -> dict:
        """
        Retrieve incidents sorted deterministically by priority and waiting time,
        with optional filtering.
        """
        now_dt = now_dt or datetime.now(timezone.utc)
        thresholds = get_waiting_thresholds_minutes()
        raw_incidents = self.incident_repository.get_all()
        active_incidents = [
            inc for inc in raw_incidents
            if not inc.get("isArchived")
        ]
        sorted_incidents = self.sort_incidents_by_priority(active_incidents, now_dt=now_dt)

        filtered = []
        search_q = (search or "").strip().lower()

        for inc in sorted_incidents:
            if priority_filter and priority_filter != "ALL" and inc.get("priority") != priority_filter:
                continue
            if severity_filter and severity_filter != "ALL" and inc.get("severity") != severity_filter:
                continue
            if status_filter and status_filter != "ALL" and inc.get("status") != status_filter:
                continue
            if date_ist:
                created_dt = parse_utc_timestamp(inc.get("createdAt"))
                if created_dt is None:
                    continue
                ist_date_str = created_dt.astimezone(IST_TIMEZONE).strftime("%Y-%m-%d")
                if ist_date_str != date_ist:
                    continue
            if search_q:
                haystack = " ".join([
                    str(inc.get("incidentId", "")),
                    str(inc.get("type", "")),
                    str(inc.get("description", "")),
                ]).lower()
                if search_q not in haystack:
                    continue
            filtered.append(inc)

        return {
            "incidents": filtered,
            "thresholdsMinutes": thresholds,
            "generatedAt": now_dt.isoformat(),
        }

    PROTECTED_WORKFLOW_STATUSES = {
        "UNDER_REVIEW",
        "VERIFIED",
        "REJECTED",
        "AMBULANCE_ASSIGNED",
        "HOSPITAL_REQUESTED",
        "HOSPITAL_ACCEPTED",
        "HOSPITAL_REJECTED",
        "PATIENT_TRANSPORTED",
        "COMPLETED",
    }

    def update_status(self, incident_id, status):
        """
        Validate and update an incident status.

        Protected workflow statuses must use their dedicated
        conditional workflow methods so verification and resource
        coordination steps cannot be bypassed.
        """
        if status not in INCIDENT_STATUSES:
            raise ValueError(
                f"Invalid incident status: {status}"
            )

        if status in self.PROTECTED_WORKFLOW_STATUSES:
            raise ValueError(
                f"Status '{status}' cannot be set directly. "
                "Use the dedicated incident workflow action."
            )

        return self.incident_repository.update(
            incident_id,
            {"status": status},
        )

    def start_review(self, incident_id):
        """
        Move an incident from CREATED to UNDER_REVIEW.
        """

        now = datetime.now(timezone.utc).isoformat()

        return self.incident_repository.conditional_update(
            incident_id,
            "CREATED",
            {
                "status": "UNDER_REVIEW",
                "updatedAt": now,
            },
        )

    def verify_incident(
        self,
        incident_id,
        decision,
        reviewed_by,
        remarks=None,
    ):
        """
        Finalize incident review as VERIFIED or REJECTED.
        """

        if decision not in ("VERIFIED", "REJECTED"):
            raise ValueError(
                "Decision must be VERIFIED or REJECTED."
            )

        if not isinstance(reviewed_by, str) or not reviewed_by.strip():
            raise ValueError("Reviewer ID is required.")

        if remarks is not None and not isinstance(remarks, str):
            raise ValueError("Verification remarks must be a string.")

        now = datetime.now(timezone.utc).isoformat()

        update_payload = {
            "status": decision,
            "reviewedBy": reviewed_by.strip(),
            "reviewedAt": now,
            "verificationRemarks": remarks.strip() if remarks else None,
            "updatedAt": now,
        }
        if decision == "VERIFIED":
            update_payload["verifiedAt"] = now

        return self.incident_repository.conditional_update(
            incident_id,
            "UNDER_REVIEW",
            update_payload,
        )

    def archive_incident(self, incident_id: str, archived_by: str):
        """
        Archive a COMPLETED incident without changing its status.
        Generates archivedAt on the backend and enforces conditional atomicity.
        """
        from utils.auth import NotFoundError

        if not isinstance(archived_by, str) or not archived_by.strip():
            raise ValueError("archivedBy user ID is required.")

        existing = self.incident_repository.get_by_id(incident_id)
        if existing is None:
            raise NotFoundError("Incident not found.")

        now = datetime.now(timezone.utc).isoformat()
        return self.incident_repository.archive_conditional_update(
            incident_id=incident_id,
            archived_by=archived_by.strip(),
            archived_at=now,
        )

    def get_archived_incidents(self, now_dt: datetime | None = None) -> list[dict]:
        """
        Return all archived incidents sorted by archivedAt descending (newest first).
        """
        now_dt = now_dt or datetime.now(timezone.utc)
        thresholds = get_waiting_thresholds_minutes()
        raw_incidents = self.incident_repository.get_all()
        archived = [
            self.enrich_incident(inc, now_dt=now_dt, thresholds=thresholds)
            for inc in raw_incidents
            if inc.get("isArchived")
        ]
        archived.sort(
            key=lambda item: (item.get("archivedAt") or "", str(item.get("incidentId", ""))),
            reverse=True,
        )
        return archived
