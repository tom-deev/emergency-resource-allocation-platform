from incident_service import IncidentService


class FakeIncidentRepository:
    def __init__(self):
        self.created_incident = None
        self.updated_data = None

    def create(self, incident):
        self.created_incident = incident
        return incident

    def get_by_id(self, incident_id):
        return {"incidentId": incident_id}

    def get_all(self):
        return [{"incidentId": "INC001"}]

    def update(self, incident_id, data):
        self.updated_data = {
            "incidentId": incident_id,
            "data": data,
        }
        return self.updated_data


repository = FakeIncidentRepository()
service = IncidentService(repository)

incident = {
    "incidentId": "INC001",
    "type": "ACCIDENT",
    "description": "Test incident",
    "latitude": 16.8524,
    "longitude": 74.5815,
    "severity": "HIGH",
    "peopleAffected": 2,
    "status": "CREATED",
    "createdAt": "2026-09-08T00:00:00Z",
    "updatedAt": "2026-09-08T00:00:00Z",
    "requiredResources": ["AMBULANCE"],
    "requiredEquipment": [],
    "assignedAmbulanceId": None,
    "assignedHospitalId": None,
}


# Create
result = service.create_incident(incident)

assert result == incident
assert repository.created_incident == incident
print("Incident create service: PASSED")


# Get by ID
result = service.get_incident("INC001")

assert result["incidentId"] == "INC001"
print("Incident get service: PASSED")


# Get all
result = service.get_all_incidents()

assert len(result) == 1
assert result[0]["incidentId"] == "INC001"
print("Incident get_all service: PASSED")


# Valid status update
result = service.update_status("INC001", "PENDING")

assert result["incidentId"] == "INC001"
assert repository.updated_data["data"] == {
    "status": "PENDING"
}
print("Incident status update service: PASSED")


# Invalid status
try:
    service.update_status("INC001", "INVALID_STATUS")
    raise AssertionError("Invalid status was accepted")
except ValueError:
    pass

print("Invalid status handling: PASSED")


print("ALL INCIDENT SERVICE TESTS PASSED")
