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
        validate_hospital_data(hospital)
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
        Update hospital information.
        """
        if not data:
            raise ValueError("Update data cannot be empty.")

        return self.hospital_repository.update(
            hospital_id,
            data,
        )
