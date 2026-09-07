from constants import AMBULANCE_STATUSES
from validation.common import validate_coordinates


def validate_ambulance_data(data: dict) -> None:
    """
    Validate the basic fields required for an ambulance.
    """

    required_fields = (
        "ambulanceId",
        "registrationNumber",
        "latitude",
        "longitude",
        "status",
    )

    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Missing required field: {field_name}")

    if not isinstance(data["ambulanceId"], str) or not data["ambulanceId"].strip():
        raise ValueError("ambulanceId must be a non-empty string")

    if (
        not isinstance(data["registrationNumber"], str)
        or not data["registrationNumber"].strip()
    ):
        raise ValueError("registrationNumber must be a non-empty string")

    validate_coordinates(data["latitude"], data["longitude"])

    if data["status"] not in AMBULANCE_STATUSES:
        raise ValueError(f"Invalid ambulance status: {data['status']}")

    if not isinstance(data.get("equipment", []), list):
        raise ValueError("equipment must be a list")
    