import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.incident_service import IncidentService
from repositories.incident_repository import ConditionalUpdateError


class FakeIncidentRepository:
    def __init__(self):
        self.incidents = {
            "INC001": {
                "incidentId": "INC001",
                "status": "CREATED",
            },
            "INC002": {
                "incidentId": "INC002",
                "status": "CREATED",
            },
        }

    def conditional_update(self, incident_id, expected_status, data):
        incident = self.incidents.get(incident_id)

        if incident is None or incident["status"] != expected_status:
            raise ConditionalUpdateError(
                "Incident does not exist or its status has changed."
            )

        incident.update(data)
        return incident.copy()


repository = FakeIncidentRepository()
service = IncidentService(repository)


# Test 1: Start review
result = service.start_review("INC001")

assert result["status"] == "UNDER_REVIEW"
assert result["updatedAt"]

print("Start incident review: PASSED")


# Test 2: Verify incident
result = service.verify_incident(
    "INC001",
    "VERIFIED",
    "DISPATCHER001",
    "Incident details confirmed.",
)

assert result["status"] == "VERIFIED"
assert result["reviewedBy"] == "DISPATCHER001"
assert result["reviewedAt"]
assert result["verificationRemarks"] == "Incident details confirmed."

print("Incident verification: PASSED")


# Test 3: Reject another incident
service.start_review("INC002")

result = service.verify_incident(
    "INC002",
    "REJECTED",
    "DISPATCHER002",
    "Insufficient evidence.",
)

assert result["status"] == "REJECTED"
assert result["reviewedBy"] == "DISPATCHER002"

print("Incident rejection: PASSED")


# Test 4: Invalid decision
try:
    service.verify_incident(
        "INC002",
        "CANCELLED",
        "DISPATCHER001",
    )
    raise AssertionError("Invalid decision was accepted")

except ValueError:
    print("Invalid decision prevention: PASSED")


# Test 5: Missing reviewer
try:
    service.verify_incident(
        "INC001",
        "VERIFIED",
        "   ",
    )
    raise AssertionError("Empty reviewer was accepted")

except ValueError:
    print("Reviewer validation: PASSED")


# Test 6: Invalid remarks
try:
    service.verify_incident(
        "INC001",
        "VERIFIED",
        "DISPATCHER001",
        123,
    )
    raise AssertionError("Invalid remarks were accepted")

except ValueError:
    print("Remarks validation: PASSED")


# Test 7: Cannot verify before review
try:
    service.verify_incident(
        "INC001",
        "VERIFIED",
        "DISPATCHER001",
    )
    raise AssertionError("Incident was verified twice")

except ConditionalUpdateError:
    print("Duplicate verification prevention: PASSED")


# Test 8: Cannot start review twice
try:
    service.start_review("INC001")
    raise AssertionError("Review was started twice")

except ConditionalUpdateError:
    print("Duplicate review prevention: PASSED")


print("\nALL INCIDENT VERIFICATION SERVICE TESTS PASSED")
