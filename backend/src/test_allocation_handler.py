import json

import handler


class FakeAllocationService:
    def allocate_incident(
        self,
        incident_id,
        required_hospital_facilities,
    ):
        assert incident_id == "INC001"
        assert required_hospital_facilities == ["ICU", "TRAUMA"]

        return {
            "allocation": {
                "incidentId": "INC001",
                "ambulanceId": "AMB001",
                "hospitalId": "HOS001",
                "ambulanceDistanceKm": 0.2,
                "hospitalDistanceKm": 0.4,
            },
            "incident": {
                "incidentId": "INC001",
                "status": "ALLOCATED",
                "assignedAmbulanceId": "AMB001",
                "assignedHospitalId": "HOS001",
            },
        }


def test_allocate_route():
    original_get_allocation_service = handler.get_allocation_service

    try:
        handler.get_allocation_service = (
            lambda: FakeAllocationService()
        )

        event = {
            "httpMethod": "POST",
            "path": "/incidents/INC001/allocate",
            "body": json.dumps(
                {
                    "requiredHospitalFacilities": [
                        "ICU",
                        "TRAUMA",
                    ]
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 200

        body = json.loads(response["body"])

        assert body["message"] == "Incident allocated successfully."

        assert body["allocation"]["incidentId"] == "INC001"
        assert body["allocation"]["ambulanceId"] == "AMB001"
        assert body["allocation"]["hospitalId"] == "HOS001"

        assert body["incident"]["status"] == "ALLOCATED"

        print("POST /incidents/{id}/allocate: PASSED")

    finally:
        handler.get_allocation_service = (
            original_get_allocation_service
        )


def test_invalid_facilities_body():
    original_get_allocation_service = handler.get_allocation_service

    try:
        handler.get_allocation_service = (
            lambda: FakeAllocationService()
        )

        event = {
            "httpMethod": "POST",
            "path": "/incidents/INC001/allocate",
            "body": json.dumps(
                {
                    "requiredHospitalFacilities": "ICU"
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400

        body = json.loads(response["body"])

        assert (
            body["error"]
            == "requiredHospitalFacilities must be a list."
        )

        print("Invalid allocation request validation: PASSED")

    finally:
        handler.get_allocation_service = (
            original_get_allocation_service
        )


def test_missing_incident():
    class MissingIncidentService:
        def allocate_incident(
            self,
            incident_id,
            required_hospital_facilities,
        ):
            raise ValueError("Incident not found.")

    original_get_allocation_service = handler.get_allocation_service

    try:
        handler.get_allocation_service = (
            lambda: MissingIncidentService()
        )

        event = {
            "httpMethod": "POST",
            "path": "/incidents/UNKNOWN/allocate",
            "body": json.dumps(
                {
                    "requiredHospitalFacilities": []
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400

        body = json.loads(response["body"])

        assert body["error"] == "Incident not found."

        print("Missing incident allocation handling: PASSED")

    finally:
        handler.get_allocation_service = (
            original_get_allocation_service
        )


if __name__ == "__main__":
    test_allocate_route()
    test_invalid_facilities_body()
    test_missing_incident()

    print("ALL ALLOCATION HANDLER TESTS PASSED")
