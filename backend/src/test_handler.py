import json

import handler


class FakeHospitalService:
    def __init__(self):
        self.created = None
        self.updated = None

    def create_hospital(self, hospital):
        self.created = hospital
        return hospital

    def get_all_hospitals(self):
        return [
            {
                "hospitalId": "HOS001",
                "name": "City General Hospital",
                "availableBeds": 40,
                "status": "ACTIVE",
            }
        ]

    def update_status(self, hospital_id, status):
        self.updated = {
            "hospitalId": hospital_id,
            "status": status,
        }
        return self.updated

    def update_hospital(self, hospital_id, data):
        self.updated = {
            "hospitalId": hospital_id,
            **data,
        }
        return self.updated


service = FakeHospitalService()


def fake_get_hospital_service():
    return service


handler.get_hospital_service = fake_get_hospital_service


# POST /hospitals
event = {
    "httpMethod": "POST",
    "path": "/hospitals",
    "body": json.dumps({
        "name": "City General Hospital",
        "latitude": 16.8524,
        "longitude": 74.5815,
        "totalBeds": 100,
        "availableBeds": 40,
        "facilities": ["TRAUMA", "ICU"],
        "status": "ACTIVE",
    }),
}

response = handler.lambda_handler(event, None)

assert response["statusCode"] == 201

body = json.loads(response["body"])

assert body["name"] == "City General Hospital"
assert body["totalBeds"] == 100
assert body["availableBeds"] == 40
assert body["status"] == "ACTIVE"

print("POST /hospitals: PASSED")


# GET /hospitals
event = {
    "httpMethod": "GET",
    "path": "/hospitals",
}

response = handler.lambda_handler(event, None)

assert response["statusCode"] == 200

body = json.loads(response["body"])

assert len(body) == 1
assert body[0]["hospitalId"] == "HOS001"

print("GET /hospitals: PASSED")


# PUT /hospitals/{id}
event = {
    "httpMethod": "PUT",
    "path": "/hospitals/HOS001",
    "body": json.dumps({
        "availableBeds": 35,
    }),
}

response = handler.lambda_handler(event, None)

assert response["statusCode"] == 200

body = json.loads(response["body"])

assert body["hospitalId"] == "HOS001"
assert body["availableBeds"] == 35

print("PUT /hospitals/{id}: PASSED")


# Hospital status update
event = {
    "httpMethod": "PUT",
    "path": "/hospitals/HOS001",
    "body": json.dumps({
        "status": "INACTIVE",
    }),
}

response = handler.lambda_handler(event, None)

assert response["statusCode"] == 200

body = json.loads(response["body"])

assert body["status"] == "INACTIVE"

print("Hospital status update: PASSED")


print("ALL HOSPITAL API TESTS PASSED")
