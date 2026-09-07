import sys

sys.path.insert(0, r"backend\src")

from repositories.incident_repository import IncidentRepository
from repositories.ambulance_repository import AmbulanceRepository
from repositories.hospital_repository import HospitalRepository
from repositories.user_repository import UserRepository


class FakeTable:
    def __init__(self, items):
        self.items = items
        self.scan_called = False

    def scan(self):
        self.scan_called = True
        return {"Items": self.items}


incident_table = FakeTable([
    {"incidentId": "inc_1"},
    {"incidentId": "inc_2"},
])

ambulance_table = FakeTable([
    {"ambulanceId": "amb_1"},
    {"ambulanceId": "amb_2"},
])

hospital_table = FakeTable([
    {"hospitalId": "hosp_1"},
    {"hospitalId": "hosp_2"},
])

user_table = FakeTable([
    {"userId": "user_1"},
    {"userId": "user_2"},
])


incident_repository = IncidentRepository(incident_table)
ambulance_repository = AmbulanceRepository(ambulance_table)
hospital_repository = HospitalRepository(hospital_table)
user_repository = UserRepository(user_table)


incidents = incident_repository.get_all()
ambulances = ambulance_repository.get_all()
hospitals = hospital_repository.get_all()
users = user_repository.get_all()


assert len(incidents) == 2
assert len(ambulances) == 2
assert len(hospitals) == 2
assert len(users) == 2

assert incident_table.scan_called
assert ambulance_table.scan_called
assert hospital_table.scan_called
assert user_table.scan_called

print("Incident get_all: PASSED")
print("Ambulance get_all: PASSED")
print("Hospital get_all: PASSED")
print("User get_all: PASSED")
print("ALL REPOSITORY GET_ALL OPERATIONS VERIFIED")
