import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from botocore.exceptions import ClientError
from repositories.incident_repository import (
    IncidentRepository,
    ConditionalUpdateError,
)


class FakeTable:
    def __init__(self):
        self.last_request = None
        self.should_fail = False

    def update_item(self, **kwargs):
        self.last_request = kwargs

        if self.should_fail:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "Condition failed",
                    }
                },
                "UpdateItem",
            )

        return {
            "Attributes": {
                "incidentId": "INC001",
                "status": "VERIFIED",
                "reviewedBy": "DISPATCHER001",
            }
        }


table = FakeTable()
repository = IncidentRepository(table)


# Test 1: Successful conditional update
result = repository.conditional_update(
    "INC001",
    "UNDER_REVIEW",
    {
        "status": "VERIFIED",
        "reviewedBy": "DISPATCHER001",
    },
)

assert result["status"] == "VERIFIED"
assert result["reviewedBy"] == "DISPATCHER001"

request = table.last_request

assert "ConditionExpression" in request
assert "attribute_exists" in request["ConditionExpression"]
assert "status" in request["ExpressionAttributeNames"].values()
assert request["ExpressionAttributeValues"][":expected_status"] == "UNDER_REVIEW"

print("Conditional update success: PASSED")


# Test 2: Status conflict
table.should_fail = True

try:
    repository.conditional_update(
        "INC001",
        "UNDER_REVIEW",
        {"status": "VERIFIED"},
    )
    raise AssertionError("Expected conditional update failure")

except ConditionalUpdateError:
    print("Conditional update conflict: PASSED")


# Test 3: Empty update prevention
try:
    repository.conditional_update("INC001", "CREATED", {})
    raise AssertionError("Empty update was accepted")

except ValueError:
    print("Empty update prevention: PASSED")


# Test 4: Missing expected status
try:
    repository.conditional_update("INC001", None, {"status": "VERIFIED"})
    raise AssertionError("Missing expected status was accepted")

except ValueError:
    print("Expected status validation: PASSED")


# Test 5: Incident ID protection
try:
    repository.conditional_update(
        "INC001",
        "CREATED",
        {"incidentId": "INC002"},
    )
    raise AssertionError("Incident ID modification was accepted")

except ValueError:
    print("Incident ID protection: PASSED")


print("\nALL CONDITIONAL UPDATE TESTS PASSED")
