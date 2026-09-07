from validation.incident import validate_incident_data
from constants import INCIDENT_STATUSES


class IncidentService:
    """
    Service layer for incident-related business logic.
    """

    def __init__(self, incident_repository):
        self.incident_repository = incident_repository

    def create_incident(self, incident):
        """
        Validate and create an incident.

        The validation layer works with dictionaries,
        while the repository works with the Incident model.
        """
        if isinstance(incident, dict):
            validation_data = incident
        else:
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

    def update_status(self, incident_id, status):
        """
        Validate and update an incident status.
        """
        if status not in INCIDENT_STATUSES:
            raise ValueError(
                f"Invalid incident status: {status}"
            )

        return self.incident_repository.update(
            incident_id,
            {"status": status},
        )
