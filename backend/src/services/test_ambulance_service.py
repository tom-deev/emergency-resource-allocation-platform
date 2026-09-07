from ambulance_service import AmbulanceService


class FakeAmbulanceRepository:
    def __init__(self):
        self.created_ambulance = None
        self.updated_data = None

    def create(self, ambulance):
        self.created_ambulance = ambulance
        return ambulance

    def get_by_id(self, ambulance_id):
        return {"ambulanceId": ambulance_id}

    def get_all(self):
        return [{"ambulanceId": "AMB001"}]

    def update(self, ambulance_id, data):
        self.updated_data = {
            "ambulanceId": ambulance_id,
            "data": data,
        }
        return self.updated_data


repository = FakeAmbulanceRepository()
service = AmbulanceService(repository)

ambulance = {
    "ambulanceId": "AMB001",
    "registrationNumber": "MH12AB1234",
    "latitude": 16.8524,
    "longitude": 74.5815,
    "status": "AVAILABLE",
    "equipment": ["OXYGEN"],
    "assignedIncidentId": None,
}


# Create
result = service.create_ambulance(ambulance)

assert result == ambulance
assert repository.created_ambulance == ambulance
print("Ambulance create service: PASSED")


# Get by ID
result = service.get_ambulance("AMB001")

assert result["ambulanceId"] == "AMB001"
print("Ambulance get service: PASSED")


# Get all
result = service.get_all_ambulances()

assert len(result) == 1
assert result[0]["ambulanceId"] == "AMB001"
print("Ambulance get_all service: PASSED")


# Valid status update
result = service.update_status("AMB001", "BUSY")

assert result["ambulanceId"] == "AMB001"
assert repository.updated_data["data"] == {
    "status": "BUSY"
}
print("Ambulance status update service: PASSED")


# General update
result = service.update_ambulance(
    "AMB001",
    {"assignedIncidentId": "INC001"},
)

assert result["ambulanceId"] == "AMB001"
assert repository.updated_data["data"] == {
    "assignedIncidentId": "INC001"
}
print("Ambulance general update service: PASSED")


# Invalid status
try:
    service.update_status("AMB001", "INVALID_STATUS")
    raise AssertionError("Invalid status was accepted")
except ValueError:
    pass

print("Invalid status handling: PASSED")


# Empty update
try:
    service.update_ambulance("AMB001", {})
    raise AssertionError("Empty update was accepted")
except ValueError:
    pass

print("Empty update handling: PASSED")


print("ALL AMBULANCE SERVICE TESTS PASSED")
