import json
from datetime import datetime, timezone
from uuid import uuid4

from models.incident import Incident
from models.ambulance import Ambulance
from models.hospital import Hospital
from models.user import User
from models.user import User

from repositories.incident_repository import IncidentRepository
from repositories.ambulance_repository import AmbulanceRepository
from repositories.hospital_repository import HospitalRepository

from services.incident_service import IncidentService
from services.ambulance_service import AmbulanceService
from services.hospital_service import HospitalService
from services.allocation_service import AllocationService
from services.user_service import UserService
from services.user_service import UserService
from services.allocation_service import AllocationService
from services.user_service import UserService
from services.user_service import UserService

from utils.response import success_response, error_response


def get_incident_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyIncidents")
    repository = IncidentRepository(table)

    return IncidentService(repository)


def get_ambulance_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyAmbulances")
    repository = AmbulanceRepository(table)

    return AmbulanceService(repository)


def get_hospital_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyHospitals")
    repository = HospitalRepository(table)

    return HospitalService(repository)


def get_user_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyUsers")
    repository = __import__(
        "repositories.user_repository",
        fromlist=["UserRepository"],
    ).UserRepository(table)

    return UserService(repository)


def get_user_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyUsers")
    repository = __import__(
        "repositories.user_repository",
        fromlist=["UserRepository"],
    ).UserRepository(table)

    return UserService(repository)


def get_allocation_service():
    from config.dynamodb import get_table

    incident_table = get_table("EmergencyIncidents")
    ambulance_table = get_table("EmergencyAmbulances")
    hospital_table = get_table("EmergencyHospitals")

    incident_repository = IncidentRepository(incident_table)
    ambulance_repository = AmbulanceRepository(ambulance_table)
    hospital_repository = HospitalRepository(hospital_table)

    return AllocationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
    )


def get_user_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyUsers")
    repository = __import__(
        "repositories.user_repository",
        fromlist=["UserRepository"],
    ).UserRepository(table)

    return UserService(repository)


def get_user_service():
    from config.dynamodb import get_table

    table = get_table("EmergencyUsers")
    repository = __import__(
        "repositories.user_repository",
        fromlist=["UserRepository"],
    ).UserRepository(table)

    return UserService(repository)


def get_allocation_service():
    from config.dynamodb import get_table

    incident_table = get_table("EmergencyIncidents")
    ambulance_table = get_table("EmergencyAmbulances")
    hospital_table = get_table("EmergencyHospitals")

    incident_repository = IncidentRepository(incident_table)
    ambulance_repository = AmbulanceRepository(ambulance_table)
    hospital_repository = HospitalRepository(hospital_table)

    return AllocationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
    )


def create_user_from_body(body):
    password = body.get("password")

    if not password:
        raise ValueError("Password is required.")

    return User(
        userId=body.get("userId", str(uuid4())),
        username=body.get("username"),
        role=body.get("role"),
        passwordHash=User.hash_password(password),
    )


def create_user_from_body(body):
    password = body.get("password")

    if not password:
        raise ValueError("Password is required.")

    return User(
        userId=body.get("userId", str(uuid4())),
        username=body.get("username"),
        role=body.get("role"),
        passwordHash=User.hash_password(password),
    )


def create_incident_from_body(body):
    now = datetime.now(timezone.utc).isoformat()

    return Incident(
        incidentId=body.get("incidentId", str(uuid4())),
        type=body.get("type"),
        description=body.get("description"),
        latitude=body.get("latitude"),
        longitude=body.get("longitude"),
        severity=body.get("severity"),
        peopleAffected=body.get("peopleAffected"),
        status=body.get("status", "CREATED"),
        createdAt=body.get("createdAt", now),
        updatedAt=body.get("updatedAt", now),
        requiredResources=body.get("requiredResources", []),
        requiredEquipment=body.get("requiredEquipment", []),
        assignedAmbulanceId=body.get("assignedAmbulanceId"),
        assignedHospitalId=body.get("assignedHospitalId"),
    )


def create_ambulance_from_body(body):
    return Ambulance(
        ambulanceId=body.get("ambulanceId", str(uuid4())),
        registrationNumber=body.get("registrationNumber"),
        latitude=body.get("latitude"),
        longitude=body.get("longitude"),
        status=body.get("status", "AVAILABLE"),
        equipment=body.get("equipment", []),
        assignedIncidentId=body.get("assignedIncidentId"),
    )


def create_hospital_from_body(body):
    return Hospital(
        hospitalId=body.get("hospitalId", str(uuid4())),
        name=body.get("name"),
        latitude=body.get("latitude"),
        longitude=body.get("longitude"),
        totalBeds=body.get("totalBeds"),
        availableBeds=body.get("availableBeds"),
        facilities=body.get("facilities", []),
        status=body.get("status", "ACTIVE"),
    )


def serialize_data(data):
    if isinstance(data, dict):
        return data

    if hasattr(data, "to_dict"):
        return data.to_dict()

    return vars(data)


def lambda_handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    try:
        # Root
        if method == "GET" and path == "/":
            return success_response({
                "message": "Emergency Response & Resource Allocation Platform API",
                "status": "running",
            })

        # -------------------------
        # AUTH ROUTES
        if method == "POST" and path == "/auth/register":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            user = create_user_from_body(body)

            service = get_user_service()
            created_user = service.create_user(user)

            response_user = serialize_data(created_user)

            response_user.pop("passwordHash", None)

            return success_response(
                response_user,
                201,
            )

        if method == "POST" and path == "/auth/login":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            username = body.get("username")
            password = body.get("password")

            if not username:
                return error_response(
                    "Username is required.",
                    400,
                )

            if not password:
                return error_response(
                    "Password is required.",
                    400,
                )

            password_hash = User.hash_password(password)

            service = get_user_service()

            authenticated_user = service.authenticate_user(
                username,
                password_hash,
            )

            response_user = serialize_data(authenticated_user)

            response_user.pop("passwordHash", None)

            return success_response(
                {
                    "message": "Login successful.",
                    "user": response_user,
                }
            )

        # AUTH ROUTES
        if method == "POST" and path == "/auth/register":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            user = create_user_from_body(body)

            service = get_user_service()
            created_user = service.create_user(user)

            response_user = serialize_data(created_user)

            response_user.pop("passwordHash", None)

            return success_response(
                response_user,
                201,
            )

        if method == "POST" and path == "/auth/login":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            username = body.get("username")
            password = body.get("password")

            if not username:
                return error_response(
                    "Username is required.",
                    400,
                )

            if not password:
                return error_response(
                    "Password is required.",
                    400,
                )

            password_hash = User.hash_password(password)

            service = get_user_service()

            authenticated_user = service.authenticate_user(
                username,
                password_hash,
            )

            response_user = serialize_data(authenticated_user)

            response_user.pop("passwordHash", None)

            return success_response(
                {
                    "message": "Login successful.",
                    "user": response_user,
                }
            )

        # INCIDENT ROUTES
        # -------------------------

        if method == "GET" and path == "/incidents":
            service = get_incident_service()
            incidents = service.get_all_incidents()

            return success_response(
                [serialize_data(incident) for incident in incidents]
            )

        if method == "GET" and path.startswith("/incidents/"):
            path_parts = path.strip("/").split("/")

            if len(path_parts) == 2:
                incident_id = path_parts[1]

                service = get_incident_service()
                incident = service.get_incident(incident_id)

                if incident is None:
                    return error_response(
                        "Incident not found.",
                        404,
                    )

                return success_response(
                    serialize_data(incident)
                )

        if method == "POST" and path == "/incidents":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            incident = create_incident_from_body(body)

            service = get_incident_service()
            created_incident = service.create_incident(incident)

            return success_response(
                serialize_data(created_incident),
                201,
            )

        if (
            method == "PUT"
            and path.startswith("/incidents/")
            and path.endswith("/status")
        ):
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 3:
                return error_response(
                    "Invalid incident status path.",
                    400,
                )

            incident_id = path_parts[1]

            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            status = body.get("status")

            if not status:
                return error_response(
                    "Status is required.",
                    400,
                )

            service = get_incident_service()

            updated_incident = service.update_status(
                incident_id,
                status,
            )

            return success_response(
                serialize_data(updated_incident)
            )

        # -------------------------
        # ALLOCATION ROUTE
        if (
            method == "POST"
            and path.startswith("/incidents/")
            and path.endswith("/allocate")
        ):
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 3:
                return error_response("Invalid allocation path.", 400)

            incident_id = path_parts[1]

            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            required_hospital_facilities = body.get(
                "requiredHospitalFacilities",
                [],
            )

            if not isinstance(required_hospital_facilities, list):
                return error_response(
                    "requiredHospitalFacilities must be a list.",
                    400,
                )

            service = get_allocation_service()

            result = service.allocate_incident(
                incident_id,
                required_hospital_facilities,
            )

            return success_response(
                {
                    "message": "Incident allocated successfully.",
                    "allocation": serialize_data(result["allocation"]),
                    "incident": serialize_data(result["incident"]),
                }
            )

        # ALLOCATION ROUTE
        if (
            method == "POST"
            and path.startswith("/incidents/")
            and path.endswith("/allocate")
        ):
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 3:
                return error_response("Invalid allocation path.", 400)

            incident_id = path_parts[1]

            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not isinstance(body, dict):
                return error_response(
                    "Request body must be a JSON object.",
                    400,
                )

            required_hospital_facilities = body.get(
                "requiredHospitalFacilities",
                [],
            )

            if not isinstance(required_hospital_facilities, list):
                return error_response(
                    "requiredHospitalFacilities must be a list.",
                    400,
                )

            service = get_allocation_service()

            result = service.allocate_incident(
                incident_id,
                required_hospital_facilities,
            )

            return success_response(
                {
                    "message": "Incident allocated successfully.",
                    "allocation": serialize_data(result["allocation"]),
                    "incident": serialize_data(result["incident"]),
                }
            )

        # AMBULANCE ROUTES
        # -------------------------

        if method == "GET" and path == "/ambulances":
            service = get_ambulance_service()
            ambulances = service.get_all_ambulances()

            return success_response(
                [serialize_data(ambulance) for ambulance in ambulances]
            )

        if method == "POST" and path == "/ambulances":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            ambulance = create_ambulance_from_body(body)

            service = get_ambulance_service()
            created_ambulance = service.create_ambulance(ambulance)

            return success_response(
                serialize_data(created_ambulance),
                201,
            )

        if method == "PUT" and path.startswith("/ambulances/"):
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 2:
                return error_response(
                    "Invalid ambulance path.",
                    400,
                )

            ambulance_id = path_parts[1]

            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not body:
                return error_response(
                    "Update data cannot be empty.",
                    400,
                )

            service = get_ambulance_service()

            if set(body.keys()) == {"status"}:
                updated_ambulance = service.update_status(
                    ambulance_id,
                    body["status"],
                )
            else:
                updated_ambulance = service.update_ambulance(
                    ambulance_id,
                    body,
                )

            return success_response(
                serialize_data(updated_ambulance)
            )

        # -------------------------
        # HOSPITAL ROUTES
        # -------------------------

        if method == "GET" and path == "/hospitals":
            service = get_hospital_service()
            hospitals = service.get_all_hospitals()

            return success_response(
                [serialize_data(hospital) for hospital in hospitals]
            )

        if method == "POST" and path == "/hospitals":
            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            hospital = create_hospital_from_body(body)

            service = get_hospital_service()
            created_hospital = service.create_hospital(hospital)

            return success_response(
                serialize_data(created_hospital),
                201,
            )

        if method == "PUT" and path.startswith("/hospitals/"):
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 2:
                return error_response(
                    "Invalid hospital path.",
                    400,
                )

            hospital_id = path_parts[1]

            raw_body = event.get("body") or "{}"
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not body:
                return error_response(
                    "Update data cannot be empty.",
                    400,
                )

            service = get_hospital_service()

            if set(body.keys()) == {"status"}:
                updated_hospital = service.update_status(
                    hospital_id,
                    body["status"],
                )
            else:
                updated_hospital = service.update_hospital(
                    hospital_id,
                    body,
                )

            return success_response(
                serialize_data(updated_hospital)
            )

        return error_response(
            "Route not found.",
            404,
        )

    except json.JSONDecodeError:
        return error_response(
            "Request body must contain valid JSON.",
            400,
        )

    except ValueError as exc:
        return error_response(
            str(exc),
            400,
        )

    except Exception as exc:
        return error_response(
            str(exc),
            500,
        )




