import sys

sys.path.insert(0, r"backend\src")

from repositories.incident_repository import IncidentRepository
from repositories.ambulance_repository import AmbulanceRepository
from repositories.hospital_repository import HospitalRepository
from repositories.user_repository import UserRepository


class FakeTable:
    def __init__(self, items):
        self.items = items

    def get_item(self, Key):
        key_name, key_value = next(iter(Key.items()))

        for item in self.items:
            if item.get(key_name) == key_value:
                return {"Item": item}

        return {}


incident_table = FakeTable([
    {
        "incidentId": "inc_test",
        "type": "FIRE",
        "severity": "HIGH",
    }
])

ambulance_table = FakeTable([
    {
        "ambulanceId": "amb_test",
        "status": "AVAILABLE",
    }
])

hospital_table = FakeTable([
    {
        "hospitalId": "hosp_test",
        "name": "Test General Hospital",
    }
])

user_table = FakeTable([
    {
        "userId": "user_test",
        "username": "test_dispatcher",
        "role": "DISPATCHER",
    }
])


incident = IncidentRepository(incident_table)
ambulance = AmbulanceRepository(ambulance_table)
hospital = HospitalRepository(hospital_table)
user = UserRepository(user_table)


assert incident.get_by_id("inc_test")["incidentId"] == "inc_test"
assert ambulance.get_by_id("amb_test")["ambulanceId"] == "amb_test"
assert hospital.get_by_id("hosp_test")["hospitalId"] == "hosp_test"
assert user.get_by_id("user_test")["userId"] == "user_test"

assert incident.get_by_id("missing") is None

print("Incident get_by_id: PASSED")
print("Ambulance get_by_id: PASSED")
print("Hospital get_by_id: PASSED")
print("User get_by_id: PASSED")
print("Missing record handling: PASSED")
print("ALL REPOSITORY GET_BY_ID OPERATIONS VERIFIED")
