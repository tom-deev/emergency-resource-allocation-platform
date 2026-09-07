from validation.ambulance import validate_ambulance_data
from validation.common import validate_coordinates
from validation.hospital import validate_hospital_data
from validation.incident import validate_incident_data


def main() -> None:
    validate_incident_data(
        {
            "incidentId": "inc_test",
            "type": "FIRE",
            "description": "Test incident",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "severity": "HIGH",
            "peopleAffected": 10,
            "status": "CREATED",
        }
    )

    validate_ambulance_data(
        {
            "ambulanceId": "amb_test",
            "registrationNumber": "MH12AB1234",
            "latitude": 18.5250,
            "longitude": 73.8500,
            "status": "AVAILABLE",
            "equipment": ["OXYGEN", "FIRST_AID"],
        }
    )

    validate_hospital_data(
        {
            "hospitalId": "hosp_test",
            "name": "Test General Hospital",
            "latitude": 18.5304,
            "longitude": 73.8467,
            "totalBeds": 200,
            "availableBeds": 75,
            "facilities": ["ICU", "TRAUMA_CARE", "OXYGEN"],
            "status": "ACTIVE",
        }
    )

    validate_coordinates(18.5204, 73.8567)

    print("Incident validation: PASSED")
    print("Ambulance validation: PASSED")
    print("Hospital validation: PASSED")
    print("Coordinate validation: PASSED")
    print("ALL VALIDATION TESTS PASSED")


if __name__ == "__main__":
    main()