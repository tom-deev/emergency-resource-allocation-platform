import sys

sys.path.insert(0, r"backend\src")

from models.user import User
from models.incident import Incident
from models.ambulance import Ambulance
from models.hospital import Hospital

from repositories.incident_repository import IncidentRepository
from repositories.ambulance_repository import AmbulanceRepository
from repositories.hospital_repository import HospitalRepository
from repositories.user_repository import UserRepository


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


def verify_repository(repository, model, expected_id, id_field):
    result = repository.create(model)

    assert result[id_field] == expected_id
    assert len(repository.table.items) == 1
    assert repository.table.items[0][id_field] == expected_id


user = User(
    "user_test",
    "test_dispatcher",
    "DISPATCHER",
)

incident = Incident(
    "inc_test",
    "FIRE",
    "Test incident",
    18.5204,
    73.8567,
    "HIGH",
    10,
    "CREATED",
    "2026-09-07T12:00:00Z",
    "2026-09-07T12:00:00Z",
    ["AMBULANCE"],
    ["OXYGEN"],
)

ambulance = Ambulance(
    "amb_test",
    "MH12AB1234",
    18.5250,
    73.8500,
    "AVAILABLE",
    ["OXYGEN", "FIRST_AID"],
)

hospital = Hospital(
    "hosp_test",
    "Test General Hospital",
    18.5304,
    73.8467,
    200,
    75,
    ["ICU", "TRAUMA_CARE", "OXYGEN"],
)


user_table = FakeTable()
incident_table = FakeTable()
ambulance_table = FakeTable()
hospital_table = FakeTable()

verify_repository(
    UserRepository(user_table),
    user,
    "user_test",
    "userId",
)

verify_repository(
    IncidentRepository(incident_table),
    incident,
    "inc_test",
    "incidentId",
)

verify_repository(
    AmbulanceRepository(ambulance_table),
    ambulance,
    "amb_test",
    "ambulanceId",
)

verify_repository(
    HospitalRepository(hospital_table),
    hospital,
    "hosp_test",
    "hospitalId",
)

print("User create: PASSED")
print("Incident create: PASSED")
print("Ambulance create: PASSED")
print("Hospital create: PASSED")
print("ALL REPOSITORY CREATE OPERATIONS VERIFIED")
