from incident_repository import IncidentRepository
from ambulance_repository import AmbulanceRepository
from hospital_repository import HospitalRepository


class FakeTable:
    def __init__(self):
        self.updated = None

    def update_item(
        self,
        Key,
        UpdateExpression,
        ExpressionAttributeNames,
        ExpressionAttributeValues,
        ReturnValues,
    ):
        self.updated = {
            "Key": Key,
            "UpdateExpression": UpdateExpression,
            "ExpressionAttributeNames": ExpressionAttributeNames,
            "ExpressionAttributeValues": ExpressionAttributeValues,
            "ReturnValues": ReturnValues,
        }

        return {
            "Attributes": {
                **Key,
                **ExpressionAttributeValues,
            }
        }


# Incident update test
incident_table = FakeTable()
incident_repository = IncidentRepository(incident_table)

incident_result = incident_repository.update(
    "INC001",
    {
        "status": "PENDING",
        "severity": "HIGH",
    },
)

assert incident_table.updated["Key"] == {"incidentId": "INC001"}
assert incident_table.updated["UpdateExpression"] == "SET #status = :status, #severity = :severity"
assert incident_table.updated["ExpressionAttributeNames"] == {
    "#status": "status",
    "#severity": "severity",
}
assert incident_table.updated["ExpressionAttributeValues"] == {
    ":status": "PENDING",
    ":severity": "HIGH",
}
assert incident_result["incidentId"] == "INC001"

print("Incident update: PASSED")


# Ambulance update test
ambulance_table = FakeTable()
ambulance_repository = AmbulanceRepository(ambulance_table)

ambulance_result = ambulance_repository.update(
    "AMB001",
    {
        "status": "BUSY",
    },
)

assert ambulance_table.updated["Key"] == {"ambulanceId": "AMB001"}
assert ambulance_table.updated["UpdateExpression"] == "SET #status = :status"
assert ambulance_table.updated["ExpressionAttributeNames"] == {
    "#status": "status",
}
assert ambulance_table.updated["ExpressionAttributeValues"] == {
    ":status": "BUSY",
}
assert ambulance_result["ambulanceId"] == "AMB001"

print("Ambulance update: PASSED")


# Hospital update test
hospital_table = FakeTable()
hospital_repository = HospitalRepository(hospital_table)

hospital_result = hospital_repository.update(
    "HOS001",
    {
        "availableBeds": 8,
        "status": "ACTIVE",
    },
)

assert hospital_table.updated["Key"] == {"hospitalId": "HOS001"}
assert hospital_table.updated["UpdateExpression"] == "SET #availableBeds = :availableBeds, #status = :status"
assert hospital_table.updated["ExpressionAttributeNames"] == {
    "#availableBeds": "availableBeds",
    "#status": "status",
}
assert hospital_table.updated["ExpressionAttributeValues"] == {
    ":availableBeds": 8,
    ":status": "ACTIVE",
}
assert hospital_result["hospitalId"] == "HOS001"

print("Hospital update: PASSED")


print("ALL UPDATE REPOSITORY TESTS PASSED")