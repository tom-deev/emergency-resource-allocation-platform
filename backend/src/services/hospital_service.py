from dataclasses import asdict, is_dataclass
from validation.hospital import validate_hospital_data
from constants import HOSPITAL_STATUSES


class HospitalService:
    """
    Service layer for hospital-related business logic.
    """

    def __init__(self, hospital_repository):
        self.hospital_repository = hospital_repository

    def create_hospital(self, hospital):
        """
        Validate and create a hospital.
        """
        hospital_data = asdict(hospital) if is_dataclass(hospital) else hospital
        validate_hospital_data(hospital_data)
        return self.hospital_repository.create(hospital)

    def get_hospital(self, hospital_id):
        """
        Retrieve a hospital by ID.
        """
        return self.hospital_repository.get_by_id(hospital_id)

    def get_all_hospitals(self):
        """
        Retrieve all hospitals.
        """
        return self.hospital_repository.get_all()

    def update_status(self, hospital_id, status):
        """
        Validate and update hospital status.
        """
        if status not in HOSPITAL_STATUSES:
            raise ValueError(
                f"Invalid hospital status: {status}"
            )

        return self.hospital_repository.update(
            hospital_id,
            {"status": status},
        )

    def update_hospital(self, hospital_id, data):
        """
        Validate and update hospital information.
        """
        if not data or not isinstance(data, dict):
            raise ValueError("Update data cannot be empty.")

        if "hospitalId" in data:
            raise ValueError("hospitalId cannot be modified.")

        if "name" in data:
            name = data["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name must be a non-empty string")

        if "status" in data and data["status"] not in HOSPITAL_STATUSES:
            raise ValueError(f"Invalid hospital status: {data['status']}")

        if "latitude" in data:
            lat = data["latitude"]
            if isinstance(lat, bool) or not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
                raise ValueError("latitude must be between -90 and 90")

        if "longitude" in data:
            lon = data["longitude"]
            if isinstance(lon, bool) or not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                raise ValueError("longitude must be between -180 and 180")

        if "facilities" in data and not isinstance(data["facilities"], list):
            raise ValueError("facilities must be a list")

        if "totalBeds" in data:
            tb = data["totalBeds"]
            if isinstance(tb, bool) or not isinstance(tb, int) or tb < 0:
                raise ValueError("totalBeds must be a non-negative integer")

        if "availableBeds" in data:
            ab = data["availableBeds"]
            if isinstance(ab, bool) or not isinstance(ab, int) or ab < 0:
                raise ValueError("availableBeds must be a non-negative integer")

        if "totalBeds" in data or "availableBeds" in data:
            total_beds = data.get("totalBeds")
            available_beds = data.get("availableBeds")

            if total_beds is None or available_beds is None:
                existing = self.hospital_repository.get_by_id(hospital_id) or {}
                if total_beds is None:
                    total_beds = existing.get("totalBeds")
                if available_beds is None:
                    available_beds = existing.get("availableBeds")

            if total_beds is not None and available_beds is not None:
                if int(available_beds) > int(total_beds):
                    raise ValueError("availableBeds cannot exceed totalBeds")

        return self.hospital_repository.update(
            hospital_id,
            data,
        )
