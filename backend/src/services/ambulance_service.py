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
        validate_ambulance_data(ambulance)
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
        Update ambulance information.
        """
        if not data:
            raise ValueError("Update data cannot be empty.")

        return self.ambulance_repository.update(
            ambulance_id,
            data,
        )
