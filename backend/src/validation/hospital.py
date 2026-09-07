from constants import HOSPITAL_STATUSES
from validation.common import validate_coordinates


def validate_hospital_data(data: dict) -> None:
    """
    Validate the basic fields required for a hospital.
    """

    required_fields = (
        "hospitalId",
        "name",
        "latitude",
        "longitude",
        "totalBeds",
        "availableBeds",
    )

    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Missing required field: {field_name}")

    if not isinstance(data["hospitalId"], str) or not data["hospitalId"].strip():
        raise ValueError("hospitalId must be a non-empty string")

    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("name must be a non-empty string")

    validate_coordinates(data["latitude"], data["longitude"])

    if not isinstance(data["totalBeds"], int) or data["totalBeds"] < 0:
        raise ValueError("totalBeds must be a non-negative integer")

    if not isinstance(data["availableBeds"], int) or data["availableBeds"] < 0:
        raise ValueError("availableBeds must be a non-negative integer")

    if data["availableBeds"] > data["totalBeds"]:
        raise ValueError("availableBeds cannot exceed totalBeds")

    if not isinstance(data.get("facilities", []), list):
        raise ValueError("facilities must be a list")

    if data.get("status", "ACTIVE") not in HOSPITAL_STATUSES:
        raise ValueError(f"Invalid hospital status: {data.get('status')}")