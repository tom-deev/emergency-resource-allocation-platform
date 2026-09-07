from constants import INCIDENT_SEVERITIES, INCIDENT_STATUSES
from validation.common import validate_coordinates


def validate_incident_data(data: dict) -> None:
    """
    Validate the basic fields required for an incident.
    """

    required_fields = (
        "incidentId",
        "type",
        "description",
        "latitude",
        "longitude",
        "severity",
        "peopleAffected",
    )

    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Missing required field: {field_name}")

    if not isinstance(data["incidentId"], str) or not data["incidentId"].strip():
        raise ValueError("incidentId must be a non-empty string")

    if not isinstance(data["type"], str) or not data["type"].strip():
        raise ValueError("type must be a non-empty string")

    if not isinstance(data["description"], str) or not data["description"].strip():
        raise ValueError("description must be a non-empty string")

    validate_coordinates(data["latitude"], data["longitude"])

    if data["severity"] not in INCIDENT_SEVERITIES:
        raise ValueError(f"Invalid incident severity: {data['severity']}")

    if data.get("status", "CREATED") not in INCIDENT_STATUSES:
        raise ValueError(f"Invalid incident status: {data.get('status')}")

    if not isinstance(data["peopleAffected"], int) or data["peopleAffected"] < 0:
        raise ValueError("peopleAffected must be a non-negative integer")