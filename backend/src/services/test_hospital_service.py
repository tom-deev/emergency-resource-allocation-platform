from hospital_service import HospitalService


class FakeHospitalRepository:
    def __init__(self):
        self.created_hospital = None
        self.updated_data = None

    def create(self, hospital):
        self.created_hospital = hospital
        return hospital

    def get_by_id(self, hospital_id):
        return {"hospitalId": hospital_id}

    def get_all(self):
        return [{"hospitalId": "HOS001"}]

    def update(self, hospital_id, data):
        self.updated_data = {
            "hospitalId": hospital_id,
            "data": data,
        }
        return self.updated_data


repository = FakeHospitalRepository()
service = HospitalService(repository)

hospital = {
    "hospitalId": "HOS001",
    "name": "City General Hospital",
    "latitude": 16.8524,
    "longitude": 74.5815,
    "totalBeds": 100,
    "availableBeds": 40,
    "facilities": ["TRAUMA", "ICU"],
    "status": "ACTIVE",
}


# Create
result = service.create_hospital(hospital)

assert result == hospital
assert repository.created_hospital == hospital
print("Hospital create service: PASSED")


# Get by ID
result = service.get_hospital("HOS001")

assert result["hospitalId"] == "HOS001"
print("Hospital get service: PASSED")


# Get all
result = service.get_all_hospitals()

assert len(result) == 1
assert result[0]["hospitalId"] == "HOS001"
print("Hospital get_all service: PASSED")


# Valid status update
result = service.update_status("HOS001", "INACTIVE")

assert result["hospitalId"] == "HOS001"
assert repository.updated_data["data"] == {
    "status": "INACTIVE"
}
print("Hospital status update service: PASSED")


# General update
result = service.update_hospital(
    "HOS001",
    {"availableBeds": 35},
)

assert result["hospitalId"] == "HOS001"
assert repository.updated_data["data"] == {
    "availableBeds": 35
}
print("Hospital general update service: PASSED")


# Invalid status
try:
    service.update_status("HOS001", "INVALID_STATUS")
    raise AssertionError("Invalid status was accepted")
except ValueError:
    pass

print("Invalid status handling: PASSED")


# Empty update
try:
    service.update_hospital("HOS001", {})
    raise AssertionError("Empty update was accepted")
except ValueError:
    pass

print("Empty update handling: PASSED")


print("ALL HOSPITAL SERVICE TESTS PASSED")
