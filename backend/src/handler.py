import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from models.ambulance import Ambulance
from models.hospital import Hospital
from models.incident import Incident
from models.user import User

from repositories.ambulance_repository import AmbulanceRepository
from repositories.hospital_repository import HospitalRepository
from repositories.incident_repository import (
    ConditionalUpdateError,
    IncidentRepository,
)
from repositories.user_repository import UserRepository

from services.allocation_service import AllocationService
from services.ambulance_service import AmbulanceService
from services.coordination_service import CoordinationService
from services.hospital_service import HospitalService
from services.incident_service import IncidentService
from services.user_service import UserService

from utils.auth import (
    AuthError,
    ForbiddenError,
    NotFoundError,
    authenticate_request,
    create_token,
)
from utils.response import (
    error_response,
    preflight_response,
    success_response,
)


logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALL_ROLES = ("DISPATCHER", "RESOURCE_OPERATOR")


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
    repository = UserRepository(table)
    return UserService(repository)


def get_allocation_service():
    from config.dynamodb import get_table

    incident_table = get_table("EmergencyIncidents")
    ambulance_table = get_table("EmergencyAmbulances")
    hospital_table = get_table("EmergencyHospitals")

    incident_repository = IncidentRepository(incident_table)
    ambulance_repository = AmbulanceRepository(ambulance_table)
    hospital_repository = HospitalRepository(hospital_table)

    transaction_client = incident_table.meta.client

    return AllocationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client=transaction_client,
    )


def get_coordination_service():
    from config.dynamodb import get_table

    incident_table = get_table("EmergencyIncidents")
    ambulance_table = get_table("EmergencyAmbulances")
    hospital_table = get_table("EmergencyHospitals")

    incident_repository = IncidentRepository(incident_table)
    ambulance_repository = AmbulanceRepository(ambulance_table)
    hospital_repository = HospitalRepository(hospital_table)

    transaction_client = incident_table.meta.client

    return CoordinationService(
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client=transaction_client,
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


def create_incident_from_body(body, created_by=None, created_by_username=None):
    now = datetime.now(timezone.utc).isoformat()

    # Authoritative timestamps, priority, and ownership are always generated
    # on the backend; client-supplied values are intentionally ignored.
    return Incident(
        incidentId=body.get("incidentId", str(uuid4())),
        type=body.get("type"),
        description=body.get("description"),
        latitude=body.get("latitude"),
        longitude=body.get("longitude"),
        severity=body.get("severity"),
        peopleAffected=body.get("peopleAffected"),
        status="CREATED",
        createdAt=now,
        updatedAt=now,
        createdBy=created_by,
        createdByUsername=created_by_username,
        requiredResources=body.get("requiredResources", []),
        requiredEquipment=body.get("requiredEquipment", []),
        assignedAmbulanceId=None,
        assignedHospitalId=None,
    )


def _sanitize_incident_for_dispatcher(incident_dict):
    """
    Expose only basic incident details and status to a Dispatcher.
    Never expose internal ambulance assignments, hospital reservations,
    reviewer remarks, or operational workflow history.
    """
    return {
        "incidentId": incident_dict.get("incidentId"),
        "type": incident_dict.get("type"),
        "emergencyType": incident_dict.get("type"),
        "description": incident_dict.get("description"),
        "severity": incident_dict.get("severity"),
        "priority": incident_dict.get("priority"),
        "status": incident_dict.get("status"),
        "createdAt": incident_dict.get("createdAt"),
        "updatedAt": incident_dict.get("updatedAt"),
        "latitude": incident_dict.get("latitude"),
        "longitude": incident_dict.get("longitude"),
        "peopleAffected": incident_dict.get("peopleAffected"),
        "isArchived": bool(incident_dict.get("isArchived", False)),
    }


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
    """Convert Python objects and DynamoDB Decimal values into JSON-compatible data."""

    if isinstance(data, Decimal):
        if data % 1 == 0:
            return int(data)
        return float(data)

    if isinstance(data, dict):
        return {
            key: serialize_data(value)
            for key, value in data.items()
        }

    if isinstance(data, (list, tuple)):
        return [serialize_data(item) for item in data]

    if hasattr(data, "to_dict"):
        return serialize_data(data.to_dict())

    if hasattr(data, "__dict__"):
        return serialize_data(vars(data))

    return data


def _parse_json_body(event):
    raw_body = event.get("body") or "{}"
    body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object.")

    return body


def _extract_method_and_path(event):
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "GET"
    ).upper()

    raw_path = event.get("path") or event.get("rawPath") or "/"
    if len(raw_path) > 1 and raw_path.endswith("/"):
        raw_path = raw_path.rstrip("/")

    return method, raw_path


def lambda_handler(event, context):
    method, path = _extract_method_and_path(event)

    if method == "OPTIONS":
        return preflight_response()

    try:
        # Root health check
        if method == "GET" and path == "/":
            return success_response({
                "message": "Emergency Response & Resource Allocation Platform API",
                "status": "running",
            })

        # -------------------------
        # AUTH ROUTES
        # -------------------------
        if method == "POST" and path == "/auth/register":
            body = _parse_json_body(event)

            # Registration lockdown: public signup is strictly DISPATCHER-only.
            # Missing role defaults to DISPATCHER; RESOURCE_OPERATOR or any other role -> 403.
            requested_role = body.get("role")
            if requested_role is None or (isinstance(requested_role, str) and not requested_role.strip()):
                body = {**body, "role": "DISPATCHER"}
            elif requested_role != "DISPATCHER":
                return error_response(
                    "Public registration is restricted to DISPATCHER accounts only.",
                    403,
                )

            user = create_user_from_body(body)

            service = get_user_service()
            created_user = service.create_user(user)

            response_user = serialize_data(created_user)
            response_user.pop("passwordHash", None)

            return success_response(response_user, 201)

        if method == "POST" and path == "/auth/login":
            body = _parse_json_body(event)
            username = body.get("username")
            password = body.get("password")

            if not username:
                return error_response("Username is required.", 400)

            if not password:
                return error_response("Password is required.", 400)

            password_hash = User.hash_password(password)
            service = get_user_service()
            try:
                authenticated_user = service.authenticate_user(
                    username,
                    password_hash,
                )
            except ValueError as exc:
                if "Invalid username or password" in str(exc):
                    return error_response(str(exc), 401)
                raise

            response_user = {
                "userId": authenticated_user.get("userId"),
                "username": authenticated_user.get("username"),
                "role": authenticated_user.get("role"),
            }

            # RESOURCE_OPERATOR requires two-step OTP verification; never issue ACCESS token yet.
            if response_user["role"] == "RESOURCE_OPERATOR":
                try:
                    challenge = service.issue_operator_otp(authenticated_user)
                except RuntimeError as exc:
                    return error_response(str(exc), 503)

                return success_response({
                    "message": "OTP verification required.",
                    "otpRequired": True,
                    "challengeToken": challenge["challengeToken"],
                    "expiresInSeconds": challenge["expiresInSeconds"],
                    "user": response_user,
                })

            # DISPATCHER login remains one-step username/password.
            token = create_token(response_user)
            return success_response({
                "message": "Login successful.",
                "user": response_user,
                "token": token,
            })

        if method == "POST" and path == "/auth/verify-otp":
            body = _parse_json_body(event)
            challenge_token = body.get("challengeToken")
            otp_code = body.get("otp")

            service = get_user_service()
            verified_user = service.verify_operator_otp(
                challenge_token,
                otp_code,
            )
            token = create_token(verified_user)

            return success_response({
                "message": "OTP verified. Login successful.",
                "user": serialize_data(verified_user),
                "token": token,
            })

        if method == "GET" and path == "/auth/me":
            claims = authenticate_request(event, allowed_roles=ALL_ROLES)
            return success_response({
                "user": {
                    "userId": claims["sub"],
                    "username": claims["username"],
                    "role": claims["role"],
                }
            })

        # -------------------------
        # DASHBOARD SUMMARY ROUTE
        # -------------------------
        if method == "GET" and path == "/dashboard/summary":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            service = get_coordination_service()
            summary = service.get_dashboard_summary()
            return success_response(serialize_data(summary))

        # -------------------------
        # INCIDENT ROUTES
        # -------------------------
        if method == "GET" and path == "/incidents":
            claims = authenticate_request(event, allowed_roles=ALL_ROLES)
            service = get_incident_service()
            incidents = service.get_all_incidents()
            serialized = [serialize_data(incident) for incident in incidents]

            if claims.get("role") == "DISPATCHER":
                own_incidents = [
                    inc for inc in serialized
                    if inc.get("createdBy") and inc.get("createdBy") == claims.get("sub")
                ]
                sorted_own = service.sort_incidents_by_priority(own_incidents)
                return success_response([
                    _sanitize_incident_for_dispatcher(inc)
                    for inc in sorted_own
                ])

            active_incidents = [
                inc for inc in serialized
                if not inc.get("isArchived")
            ]
            sorted_incidents = service.sort_incidents_by_priority(active_incidents)
            return success_response(sorted_incidents)

        if method == "GET" and path == "/incidents/queue":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            query = event.get("queryStringParameters") or {}
            service = get_incident_service()
            queue_data = service.get_priority_queue(
                priority_filter=query.get("priority"),
                severity_filter=query.get("severity"),
                status_filter=query.get("status"),
                date_ist=query.get("date"),
                search=query.get("search"),
            )

            return success_response(serialize_data(queue_data))

        if method == "GET" and path == "/incidents/archived":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            service = get_incident_service()
            archived_incidents = service.get_archived_incidents()
            return success_response(serialize_data(archived_incidents))

        if method == "POST" and path == "/incidents":
            claims = authenticate_request(event, allowed_roles=("DISPATCHER",))
            body = _parse_json_body(event)
            incident = create_incident_from_body(
                body,
                created_by=claims.get("sub"),
                created_by_username=claims.get("username"),
            )

            service = get_incident_service()
            created_incident = service.create_incident(incident)

            return success_response(
                _sanitize_incident_for_dispatcher(serialize_data(created_incident)),
                201,
            )

        if path.startswith("/incidents/"):
            path_parts = path.strip("/").split("/")

            # GET /incidents/{id}
            if method == "GET" and len(path_parts) == 2:
                claims = authenticate_request(event, allowed_roles=ALL_ROLES)
                incident_id = path_parts[1]
                service = get_incident_service()
                incident = service.get_incident(incident_id)

                if incident is None:
                    return error_response("Incident not found.", 404)

                enriched = service.enrich_incident(serialize_data(incident))

                if claims.get("role") == "DISPATCHER":
                    if (
                        not enriched.get("createdBy")
                        or enriched.get("createdBy") != claims.get("sub")
                    ):
                        # Return 404 to avoid revealing existence of other/legacy incidents
                        return error_response("Incident not found.", 404)
                    return success_response(
                        _sanitize_incident_for_dispatcher(enriched)
                    )

                return success_response(enriched)

            if len(path_parts) == 3:
                incident_id = path_parts[1]
                action = path_parts[2]

                # PUT /incidents/{id}/status
                if method == "PUT" and action == "status":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    status = body.get("status")

                    if not status:
                        return error_response("Status is required.", 400)

                    service = get_incident_service()
                    updated_incident = service.update_status(incident_id, status)
                    return success_response(serialize_data(updated_incident))

                # POST /incidents/{id}/review
                if method == "POST" and action == "review":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    service = get_incident_service()
                    updated_incident = service.start_review(incident_id)
                    return success_response({
                        "message": "Incident review started.",
                        "incident": serialize_data(updated_incident),
                    })

                # POST /incidents/{id}/verify
                if method == "POST" and action == "verify":
                    claims = authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    decision = body.get("decision")
                    remarks = body.get("remarks")
                    reviewer = claims.get("username") or claims.get("sub")

                    service = get_incident_service()
                    updated_incident = service.verify_incident(
                        incident_id,
                        decision,
                        reviewer,
                        remarks,
                    )
                    return success_response({
                        "message": f"Incident {decision.lower()} successfully.",
                        "incident": serialize_data(updated_incident),
                    })

                # GET /incidents/{id}/candidates
                if method == "GET" and action == "candidates":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    query = event.get("queryStringParameters") or {}
                    raw_facilities = query.get("facilities") or ""
                    required_facilities = [
                        item.strip()
                        for item in raw_facilities.split(",")
                        if item.strip()
                    ]
                    raw_beds = query.get("beds")
                    required_beds = None
                    if raw_beds is not None and str(raw_beds).strip() != "":
                        try:
                            required_beds = int(raw_beds)
                        except ValueError:
                            return error_response(
                                "beds query parameter must be an integer.",
                                400,
                            )

                    service = get_coordination_service()
                    candidates = service.get_candidates(
                        incident_id,
                        required_facilities,
                        required_beds=required_beds,
                    )
                    return success_response(serialize_data(candidates))

                # POST /incidents/{id}/assign-ambulance
                if method == "POST" and action == "assign-ambulance":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    ambulance_id = body.get("ambulanceId")

                    service = get_coordination_service()
                    result = service.assign_ambulance(incident_id, ambulance_id)
                    return success_response({
                        "message": "Ambulance assigned successfully.",
                        "incident": serialize_data(result["incident"]),
                        "ambulance": serialize_data(result["ambulance"]),
                    })

                # POST /incidents/{id}/request-hospital
                if method == "POST" and action == "request-hospital":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    hospital_id = body.get("hospitalId")
                    beds_requested = body.get("bedsRequested")

                    service = get_coordination_service()
                    result = service.request_hospital(
                        incident_id,
                        hospital_id,
                        beds_requested=beds_requested,
                    )
                    return success_response({
                        "message": "Hospital beds reserved and admission requested.",
                        "incident": serialize_data(result["incident"]),
                        "hospital": serialize_data(result["hospital"]),
                        "reservation": serialize_data(result["reservation"]),
                    })

                # POST /incidents/{id}/cancel-reservation
                if method == "POST" and action == "cancel-reservation":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    reason = body.get("reason")

                    service = get_coordination_service()
                    result = service.cancel_hospital_reservation(
                        incident_id,
                        reason=reason,
                    )
                    return success_response({
                        "message": "Hospital bed reservation cancelled and beds released.",
                        "incident": serialize_data(result["incident"]),
                        "hospital": serialize_data(result["hospital"]),
                        "reservation": serialize_data(result["reservation"]),
                    })

                # POST /incidents/{id}/hospital-decision
                if method == "POST" and action == "hospital-decision":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
                    decision = body.get("decision")
                    reason = body.get("reason")

                    service = get_coordination_service()
                    result = service.record_hospital_decision(
                        incident_id,
                        decision,
                        reason,
                    )
                    return success_response({
                        "message": f"Hospital decision recorded: {decision}.",
                        "incident": serialize_data(result["incident"]),
                        "hospital": serialize_data(result["hospital"]),
                        "reservation": serialize_data(result["reservation"]),
                    })

                # POST /incidents/{id}/transport
                if method == "POST" and action == "transport":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    service = get_coordination_service()
                    updated_incident = service.mark_patient_transported(
                        incident_id
                    )
                    return success_response({
                        "message": "Patient transport recorded.",
                        "incident": serialize_data(updated_incident),
                    })

                # POST /incidents/{id}/complete
                if method == "POST" and action == "complete":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    service = get_coordination_service()
                    result = service.complete_incident(incident_id)
                    return success_response({
                        "message": "Incident completed.",
                        "incident": serialize_data(result["incident"]),
                        "ambulance": serialize_data(result["ambulance"]),
                    })

                # POST /incidents/{id}/archive
                if method == "POST" and action == "archive":
                    claims = authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    service = get_incident_service()
                    archived_incident = service.archive_incident(
                        incident_id,
                        archived_by=claims.get("sub"),
                    )
                    return success_response({
                        "message": "Incident archived successfully.",
                        "incident": serialize_data(archived_incident),
                    })

                # POST /incidents/{id}/allocate (legacy compatibility)
                if method == "POST" and action == "allocate":
                    authenticate_request(
                        event,
                        allowed_roles=("RESOURCE_OPERATOR",),
                    )
                    body = _parse_json_body(event)
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
                    return success_response({
                        "message": "Incident allocated successfully.",
                        "allocation": serialize_data(result["allocation"]),
                        "incident": serialize_data(result["incident"]),
                    })

        # -------------------------
        # AMBULANCE ROUTES
        # -------------------------
        if method == "GET" and path == "/ambulances":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            service = get_ambulance_service()
            ambulances = service.get_all_ambulances()

            return success_response(
                [serialize_data(ambulance) for ambulance in ambulances]
            )

        if method == "POST" and path == "/ambulances":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            body = _parse_json_body(event)
            ambulance = create_ambulance_from_body(body)

            service = get_ambulance_service()
            created_ambulance = service.create_ambulance(ambulance)

            return success_response(serialize_data(created_ambulance), 201)

        if method == "PUT" and path.startswith("/ambulances/"):
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 2:
                return error_response("Invalid ambulance path.", 400)

            ambulance_id = path_parts[1]
            body = _parse_json_body(event)

            if not body:
                return error_response("Update data cannot be empty.", 400)

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

            return success_response(serialize_data(updated_ambulance))

        # -------------------------
        # HOSPITAL ROUTES
        # -------------------------
        if method == "GET" and path == "/hospitals":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            service = get_hospital_service()
            hospitals = service.get_all_hospitals()

            return success_response(
                [serialize_data(hospital) for hospital in hospitals]
            )

        if method == "POST" and path == "/hospitals":
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            body = _parse_json_body(event)
            hospital = create_hospital_from_body(body)

            service = get_hospital_service()
            created_hospital = service.create_hospital(hospital)

            return success_response(serialize_data(created_hospital), 201)

        if method == "PUT" and path.startswith("/hospitals/"):
            authenticate_request(event, allowed_roles=("RESOURCE_OPERATOR",))
            path_parts = path.strip("/").split("/")

            if len(path_parts) != 2:
                return error_response("Invalid hospital path.", 400)

            hospital_id = path_parts[1]
            body = _parse_json_body(event)

            if not body:
                return error_response("Update data cannot be empty.", 400)

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

            return success_response(serialize_data(updated_hospital))

        return error_response("Route not found.", 404)

    except json.JSONDecodeError:
        return error_response("Request body must contain valid JSON.", 400)

    except AuthError as exc:
        return error_response(str(exc), 401)

    except ForbiddenError as exc:
        return error_response(str(exc), 403)

    except NotFoundError as exc:
        return error_response(str(exc), 404)

    except ConditionalUpdateError as exc:
        return error_response(str(exc), 409)

    except ValueError as exc:
        return error_response(str(exc), 400)

    except Exception:
        logger.exception("Unhandled error in lambda_handler")
        return error_response("Internal server error.", 500)
