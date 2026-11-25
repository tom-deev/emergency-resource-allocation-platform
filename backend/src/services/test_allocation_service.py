from botocore.exceptions import ClientError

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
            return self.incident.copy()
        return None


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
        return [ambulance.copy() for ambulance in self.ambulances]


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
        return [hospital.copy() for hospital in self.hospitals]


class FakeTransactionClient:
    def __init__(
        self,
        incident_repository,
        ambulance_repository,
        hospital_repository,
        should_fail=False,
    ):
        self.incident_repository = incident_repository
        self.ambulance_repository = ambulance_repository
        self.hospital_repository = hospital_repository
        self.should_fail = should_fail
        self.calls = []

    def transact_write_items(self, TransactItems):
        self.calls.append(TransactItems)

        assert len(TransactItems) == 3
        assert all("Update" in item for item in TransactItems)

        if self.should_fail:
            raise ClientError(
                {
                    "Error": {
                        "Code": "TransactionCanceledException",
                        "Message": "Simulated transaction cancellation",
                    }
                },
                "TransactWriteItems",
            )

        ambulance_update = TransactItems[0]["Update"]
        hospital_update = TransactItems[1]["Update"]
        incident_update = TransactItems[2]["Update"]

        assert ambulance_update["TableName"] == "EmergencyAmbulances"
        assert hospital_update["TableName"] == "EmergencyHospitals"
        assert incident_update["TableName"] == "EmergencyIncidents"

        ambulance_id = ambulance_update["Key"]["ambulanceId"]["S"]
        hospital_id = hospital_update["Key"]["hospitalId"]["S"]
        incident_id = incident_update["Key"]["incidentId"]["S"]

        ambulance = next(
            item for item in self.ambulance_repository.ambulances
            if item["ambulanceId"] == ambulance_id
        )

        hospital = next(
            item for item in self.hospital_repository.hospitals
            if item["hospitalId"] == hospital_id
        )

        incident = self.incident_repository.incident

        # Simulate DynamoDB's conditional checks.
        if (
            ambulance["status"] != "AVAILABLE"
            or hospital["status"] != "ACTIVE"
            or hospital["availableBeds"] <= 0
            or incident["incidentId"] != incident_id
            or incident["status"] not in ("CREATED", "PENDING")
        ):
            raise ClientError(
                {
                    "Error": {
                        "Code": "TransactionCanceledException",
                        "Message": "Conditional check failed",
                    }
                },
                "TransactWriteItems",
            )

        # Apply all changes only after every condition succeeds.
        ambulance["status"] = "BUSY"
        ambulance["assignedIncidentId"] = incident_id

        hospital["availableBeds"] -= 1

        incident["status"] = "ALLOCATED"
        incident["assignedAmbulanceId"] = ambulance_id
        incident["assignedHospitalId"] = hospital_id


def create_test_service(should_fail=False):
    incident_repository = FakeIncidentRepository()
    ambulance_repository = FakeAmbulanceRepository()
    hospital_repository = FakeHospitalRepository()

    transaction_client = FakeTransactionClient(
        incident_repository,
        ambulance_repository,
        hospital_repository,
        should_fail,
    )

    service = AllocationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client,
    )

    return (
        service,
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client,
    )


def test_successful_transactional_allocation():
    (
        service,
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client,
    ) = create_test_service()

    result = service.allocate_incident(
        "INC001",
        ["ICU", "TRAUMA"],
    )

    assert len(transaction_client.calls) == 1
    assert len(transaction_client.calls[0]) == 3

    assert result["allocation"]["ambulanceId"] == "AMB001"
    assert result["allocation"]["hospitalId"] == "HOS001"

    assert result["incident"]["status"] == "ALLOCATED"
    assert result["incident"]["assignedAmbulanceId"] == "AMB001"
    assert result["incident"]["assignedHospitalId"] == "HOS001"

    ambulance = ambulance_repository.ambulances[0]
    assert ambulance["status"] == "BUSY"
    assert ambulance["assignedIncidentId"] == "INC001"

    hospital = hospital_repository.hospitals[0]
    assert hospital["availableBeds"] == 19

    print("Successful transactional allocation: PASSED")


def test_transaction_cancellation_no_partial_updates():
    (
        service,
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client,
    ) = create_test_service(should_fail=True)

    try:
        service.allocate_incident("INC001", ["ICU", "TRAUMA"])
        assert False, "Expected transaction cancellation."

    except ValueError as exc:
        assert "Allocation failed" in str(exc)

    assert len(transaction_client.calls) == 1

    assert incident_repository.incident["status"] == "CREATED"

    assert ambulance_repository.ambulances[0]["status"] == "AVAILABLE"
    assert ambulance_repository.ambulances[0]["assignedIncidentId"] is None

    assert hospital_repository.hospitals[0]["availableBeds"] == 20

    print("Transaction cancellation without partial updates: PASSED")


def test_missing_incident():
    service, _, _, _, transaction_client = create_test_service()

    try:
        service.allocate_incident("UNKNOWN", ["ICU"])
        assert False, "Expected missing incident error."

    except ValueError as exc:
        assert str(exc) == "Incident not found."

    assert len(transaction_client.calls) == 0

    print("Missing incident handling: PASSED")


def test_already_allocated_incident():
    (
        service,
        incident_repository,
        _,
        _,
        transaction_client,
    ) = create_test_service()

    incident_repository.incident["status"] = "ALLOCATED"

    try:
        service.allocate_incident("INC001", ["ICU"])
        assert False, "Expected invalid incident status error."

    except ValueError as exc:
        assert "CREATED or PENDING" in str(exc)

    assert len(transaction_client.calls) == 0

    print("Already allocated incident protection: PASSED")


if __name__ == "__main__":
    test_successful_transactional_allocation()
    test_transaction_cancellation_no_partial_updates()
    test_missing_incident()
    test_already_allocated_incident()

    print("\nALL TRANSACTIONAL ALLOCATION TESTS PASSED")
