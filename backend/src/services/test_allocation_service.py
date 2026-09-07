from types import SimpleNamespace

from services.allocation_service import AllocationService


class FakeIncidentRepository:
    def __init__(self):
        self.incident = {
            "incidentId": "INC001",
            "type": "ACCIDENT",
            "description": "Road accident",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "severity": "CRITICAL",
            "peopleAffected": 2,
            "status": "CREATED",
            "requiredResources": [],
            "requiredEquipment": ["OXYGEN"],
            "assignedAmbulanceId": None,
            "assignedHospitalId": None,
        }

    def get_by_id(self, incident_id):
        if incident_id == self.incident["incidentId"]:
            return self.incident

        return None

    def update(self, incident_id, data):
        self.incident.update(data)
        return self.incident


class FakeAmbulanceRepository:
    def __init__(self):
        self.ambulances = [
            {
                "ambulanceId": "AMB001",
                "registrationNumber": "DL01AB1111",
                "latitude": 28.6140,
                "longitude": 77.2091,
                "status": "AVAILABLE",
                "equipment": ["OXYGEN"],
                "assignedIncidentId": None,
            },
            {
                "ambulanceId": "AMB002",
                "registrationNumber": "DL01AB2222",
                "latitude": 28.7000,
                "longitude": 77.1000,
                "status": "AVAILABLE",
                "equipment": ["OXYGEN"],
                "assignedIncidentId": None,
            },
        ]

    def get_all(self):
        return self.ambulances

    def update(self, ambulance_id, data):
        for ambulance in self.ambulances:
            if ambulance["ambulanceId"] == ambulance_id:
                ambulance.update(data)
                return ambulance

        return None


class FakeHospitalRepository:
    def __init__(self):
        self.hospitals = [
            {
                "hospitalId": "HOS001",
                "name": "Nearest Hospital",
                "latitude": 28.6140,
                "longitude": 77.2091,
                "totalBeds": 100,
                "availableBeds": 20,
                "facilities": ["ICU", "TRAUMA"],
                "status": "ACTIVE",
            },
            {
                "hospitalId": "HOS002",
                "name": "Farther Hospital",
                "latitude": 28.7000,
                "longitude": 77.1000,
                "totalBeds": 100,
                "availableBeds": 30,
                "facilities": ["ICU", "TRAUMA"],
                "status": "ACTIVE",
            },
        ]

    def get_all(self):
        return self.hospitals

    def update(self, hospital_id, data):
        for hospital in self.hospitals:
            if hospital["hospitalId"] == hospital_id:
                hospital.update(data)
                return hospital

        return None


def test_allocation_service():
    incident_repository = FakeIncidentRepository()
    ambulance_repository = FakeAmbulanceRepository()
    hospital_repository = FakeHospitalRepository()

    service = AllocationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
    )

    result = service.allocate_incident(
        "INC001",
        ["ICU", "TRAUMA"],
    )

    assert result is not None

    allocation = result["allocation"]

    assert allocation["incidentId"] == "INC001"
    assert allocation["ambulanceId"] == "AMB001"
    assert allocation["hospitalId"] == "HOS001"

    updated_incident = result["incident"]

    assert updated_incident["status"] == "ALLOCATED"
    assert updated_incident["assignedAmbulanceId"] == "AMB001"
    assert updated_incident["assignedHospitalId"] == "HOS001"

    ambulance = ambulance_repository.ambulances[0]

    assert ambulance["status"] == "BUSY"
    assert ambulance["assignedIncidentId"] == "INC001"

    hospital = hospital_repository.hospitals[0]

    assert hospital["availableBeds"] == 19

    print("Allocation service persistence: PASSED")


def test_missing_incident():
    service = AllocationService(
        FakeIncidentRepository(),
        FakeAmbulanceRepository(),
        FakeHospitalRepository(),
    )

    try:
        service.allocate_incident(
            "UNKNOWN",
            ["ICU"],
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "Incident not found."

    print("Missing incident handling: PASSED")


if __name__ == "__main__":
    test_allocation_service()
    test_missing_incident()

    print("ALL ALLOCATION SERVICE TESTS PASSED")
