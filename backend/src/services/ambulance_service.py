from dataclasses import asdict, is_dataclass
from validation.ambulance import validate_ambulance_data
from constants import AMBULANCE_STATUSES


class AmbulanceService:
    """
    Service layer for ambulance-related business logic.
    """

    def __init__(self, ambulance_repository):
        self.ambulance_repository = ambulance_repository

    def create_ambulance(self, ambulance):
        """
        Validate and create an ambulance.
        """
        ambulance_data = asdict(ambulance) if is_dataclass(ambulance) else ambulance
        validate_ambulance_data(ambulance_data)
        return self.ambulance_repository.create(ambulance)

    def get_ambulance(self, ambulance_id):
        """
        Retrieve an ambulance by ID.
        """
        return self.ambulance_repository.get_by_id(ambulance_id)

    def get_all_ambulances(self):
        """
        Retrieve all ambulances.
        """
        return self.ambulance_repository.get_all()

    def update_status(self, ambulance_id, status):
        """
        Validate and update ambulance status.
        """
        if status not in AMBULANCE_STATUSES:
            raise ValueError(
                f"Invalid ambulance status: {status}"
            )

        return self.ambulance_repository.update(
            ambulance_id,
            {"status": status},
        )

    def update_ambulance(self, ambulance_id, data):
        """
        Validate and update ambulance information.
        """
        if not data or not isinstance(data, dict):
            raise ValueError("Update data cannot be empty.")

        if "ambulanceId" in data:
            raise ValueError("ambulanceId cannot be modified.")

        if "registrationNumber" in data:
            reg = data["registrationNumber"]
            if not isinstance(reg, str) or not reg.strip():
                raise ValueError("registrationNumber must be a non-empty string")

        if "status" in data and data["status"] not in AMBULANCE_STATUSES:
            raise ValueError(f"Invalid ambulance status: {data['status']}")

        if "latitude" in data:
            lat = data["latitude"]
            if isinstance(lat, bool) or not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
                raise ValueError("latitude must be between -90 and 90")

        if "longitude" in data:
            lon = data["longitude"]
            if isinstance(lon, bool) or not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                raise ValueError("longitude must be between -180 and 180")

        if "equipment" in data and not isinstance(data["equipment"], list):
            raise ValueError("equipment must be a list")

        return self.ambulance_repository.update(
            ambulance_id,
            data,
        )
