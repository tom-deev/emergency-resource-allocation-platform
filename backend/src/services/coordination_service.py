from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from allocation.engine import (
    calculate_distance_km,
    has_required_equipment,
    has_required_facilities,
)
from constants import MAX_RESERVATION_HISTORY
from repositories.incident_repository import ConditionalUpdateError
from services.incident_service import parse_utc_timestamp
from utils.auth import NotFoundError
from validation.common import validate_coordinates


class CoordinationService:
    """
    Human-controlled manual resource coordination workflow for incidents.

    Enforces:
    - Incident verification before ambulance assignment.
    - Atomic conditional ambulance assignment (prevents double-booking).
    - Explicit hospital admission request without premature bed reservation.
    - Explicit hospital decision (atomic bed decrement only on ACCEPTED).
    - Patient transport and completion (releases ambulance back to AVAILABLE).
    """

    def __init__(
        self,
        incident_repository,
        ambulance_repository,
        hospital_repository,
        transaction_client,
        table_names=None,
    ):
        self.incident_repository = incident_repository
        self.ambulance_repository = ambulance_repository
        self.hospital_repository = hospital_repository
        self.transaction_client = transaction_client

        self.table_names = table_names or {
            "incidents": "EmergencyIncidents",
            "ambulances": "EmergencyAmbulances",
            "hospitals": "EmergencyHospitals",
        }
        self.serializer = TypeSerializer()

    @staticmethod
    def _to_float(value):
        return float(value)

    def _serialize_values(self, values):
        return {
            key: self.serializer.serialize(
                Decimal(str(value)) if isinstance(value, float) else value
            )
            for key, value in values.items()
        }

    def get_candidates(
        self,
        incident_id,
        required_hospital_facilities=None,
        required_beds=None,
    ):
        """
        Return decision-support candidate lists (ambulances and hospitals)
        with Haversine distance and suitability indicators for a Resource Operator.

        Does NOT modify any database state.
        """
        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        inc_lat = self._to_float(incident["latitude"])
        inc_lon = self._to_float(incident["longitude"])
        req_equipment = incident.get("requiredEquipment") or []
        req_facilities = required_hospital_facilities or []

        default_required_beds = int(incident.get("peopleAffected") or 0)
        if required_beds is not None:
            effective_beds = max(1, int(required_beds))
        else:
            effective_beds = max(1, default_required_beds)

        ambulances = self.ambulance_repository.get_all()
        ambulance_candidates = []
        req_equip_set = set(req_equipment)
        for amb in ambulances:
            amb_equip = amb.get("equipment") or []
            dist = round(
                calculate_distance_km(
                    inc_lat,
                    inc_lon,
                    self._to_float(amb["latitude"]),
                    self._to_float(amb["longitude"]),
                ),
                2,
            )
            equip_match = has_required_equipment(
                amb_equip,
                req_equipment,
            )
            missing_equipment = sorted(req_equip_set - set(amb_equip))
            is_unassigned = not amb.get("assignedIncidentId")
            eligible = (
                amb.get("status") == "AVAILABLE"
                and equip_match
                and is_unassigned
            )

            reasons = []
            if amb.get("status") != "AVAILABLE":
                reasons.append(f"Status is {amb.get('status')}")
            if not is_unassigned:
                reasons.append(f"Assigned to {amb.get('assignedIncidentId')}")
            if missing_equipment:
                reasons.append(
                    f"Missing equipment: {', '.join(missing_equipment)}"
                )

            ambulance_candidates.append({
                "ambulance": amb,
                "distanceKm": dist,
                "equipmentMatch": equip_match,
                "missingEquipment": missing_equipment,
                "eligible": eligible,
                "unsuitabilityReason": "; ".join(reasons) if reasons else None,
            })

        ambulance_candidates.sort(
            key=lambda item: (
                not item["eligible"],
                item["distanceKm"],
                str(item["ambulance"].get("ambulanceId", "")),
            )
        )

        hospitals = self.hospital_repository.get_all()
        hospital_candidates = []
        req_fac_set = set(req_facilities)
        for hosp in hospitals:
            hosp_facilities = hosp.get("facilities") or []
            dist = round(
                calculate_distance_km(
                    inc_lat,
                    inc_lon,
                    self._to_float(hosp["latitude"]),
                    self._to_float(hosp["longitude"]),
                ),
                2,
            )
            fac_match = has_required_facilities(
                hosp_facilities,
                req_facilities,
            )
            missing_facilities = sorted(req_fac_set - set(hosp_facilities))
            avail_beds = int(hosp.get("availableBeds", 0))
            has_capacity = avail_beds >= effective_beds
            suitable = (
                hosp.get("status") == "ACTIVE"
                and has_capacity
                and fac_match
            )
            h_reasons = []
            if hosp.get("status") != "ACTIVE":
                h_reasons.append(f"Status is {hosp.get('status')}")
            if not has_capacity:
                h_reasons.append(
                    f"Insufficient beds ({avail_beds} available, {effective_beds} required)"
                )
            if missing_facilities:
                h_reasons.append(
                    f"Missing facilities: {', '.join(missing_facilities)}"
                )

            hospital_candidates.append({
                "hospital": hosp,
                "distanceKm": dist,
                "facilityMatch": fac_match,
                "missingFacilities": missing_facilities,
                "hasCapacity": has_capacity,
                "suitable": suitable,
                "unsuitabilityReason": "; ".join(h_reasons) if h_reasons else None,
            })

        hospital_candidates.sort(
            key=lambda item: (
                not item["suitable"],
                item["distanceKm"],
                str(item["hospital"].get("hospitalId", "")),
            )
        )

        return {
            "incidentId": incident_id,
            "incidentStatus": incident.get("status"),
            "defaultRequiredBeds": default_required_beds,
            "requiredBeds": effective_beds,
            "ambulances": ambulance_candidates,
            "hospitals": hospital_candidates,
        }

    def assign_ambulance(self, incident_id, ambulance_id):
        """
        Manually assign a suitable, AVAILABLE, unassigned ambulance
        to a VERIFIED, unassigned incident atomically.
        """
        if not ambulance_id or not isinstance(ambulance_id, str) or not ambulance_id.strip():
            raise ValueError("ambulanceId is required.")

        ambulance_id = ambulance_id.strip()

        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        if incident.get("status") != "VERIFIED" or incident.get("assignedAmbulanceId"):
            raise ConditionalUpdateError(
                "Only VERIFIED and unassigned incidents can be assigned an ambulance."
            )

        ambulance = self.ambulance_repository.get_by_id(ambulance_id)
        if ambulance is None:
            raise NotFoundError("Ambulance not found.")

        # Validate ambulance required fields & coordinates
        reg_number = ambulance.get("registrationNumber")
        if not isinstance(reg_number, str) or not reg_number.strip():
            raise ValueError("Ambulance has an invalid registrationNumber.")

        try:
            validate_coordinates(
                self._to_float(ambulance.get("latitude")),
                self._to_float(ambulance.get("longitude")),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Ambulance has invalid coordinates.") from exc

        if ambulance.get("status") != "AVAILABLE" or ambulance.get("assignedIncidentId"):
            raise ConditionalUpdateError(
                "Selected ambulance is not AVAILABLE or is already assigned."
            )

        req_equipment = incident.get("requiredEquipment") or []
        amb_equipment = ambulance.get("equipment") or []
        if not has_required_equipment(amb_equipment, req_equipment):
            missing = sorted(set(req_equipment) - set(amb_equipment))
            raise ValueError(
                f"Selected ambulance lacks required equipment: {', '.join(missing)}."
            )

        now = datetime.now(timezone.utc).isoformat()

        transaction_items = [
            {
                "Update": {
                    "TableName": self.table_names["ambulances"],
                    "Key": {"ambulanceId": {"S": ambulance_id}},
                    "UpdateExpression": (
                        "SET #status = :busy, "
                        "#assignedIncidentId = :incidentId"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#ambulanceId) "
                        "AND #status = :available "
                        "AND (attribute_not_exists(#assignedIncidentId) OR #assignedIncidentId = :nullVal)"
                    ),
                    "ExpressionAttributeNames": {
                        "#ambulanceId": "ambulanceId",
                        "#status": "status",
                        "#assignedIncidentId": "assignedIncidentId",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":busy": "BUSY",
                        ":incidentId": incident_id,
                        ":available": "AVAILABLE",
                        ":nullVal": None,
                    }),
                }
            },
            {
                "Update": {
                    "TableName": self.table_names["incidents"],
                    "Key": {"incidentId": {"S": incident_id}},
                    "UpdateExpression": (
                        "SET #status = :assigned, "
                        "#assignedAmbulanceId = :ambulanceId, "
                        "#ambulanceAssignedAt = :assignedAt, "
                        "#updatedAt = :updatedAt"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#incidentId) "
                        "AND #status = :verified "
                        "AND (attribute_not_exists(#assignedAmbulanceId) OR #assignedAmbulanceId = :nullVal)"
                    ),
                    "ExpressionAttributeNames": {
                        "#incidentId": "incidentId",
                        "#status": "status",
                        "#assignedAmbulanceId": "assignedAmbulanceId",
                        "#ambulanceAssignedAt": "ambulanceAssignedAt",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":assigned": "AMBULANCE_ASSIGNED",
                        ":ambulanceId": ambulance_id,
                        ":assignedAt": now,
                        ":updatedAt": now,
                        ":verified": "VERIFIED",
                        ":nullVal": None,
                    }),
                }
            },
        ]

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "TransactionCanceledException":
                raise ConditionalUpdateError(
                    "Ambulance assignment failed because the incident or "
                    "ambulance state has changed. Please refresh and try again."
                ) from exc
            raise

        return {
            "incident": self.incident_repository.get_by_id(incident_id),
            "ambulance": self.ambulance_repository.get_by_id(ambulance_id),
        }

    @staticmethod
    def _append_bounded_history(existing_history, entry):
        history = list(existing_history) if isinstance(existing_history, list) else []
        history.append(entry)
        return history[-MAX_RESERVATION_HISTORY:]

    def request_hospital(self, incident_id, hospital_id, beds_requested=None):
        """
        Atomically reserve beds at an ACTIVE hospital and request admission.

        - Default required beds = incident.peopleAffected (operator-adjustable).
        - Validates positive integer bed count.
        - Atomically verifies hospital ACTIVE + availableBeds >= bedsRequested,
          decrements availableBeds, creates embedded bedReservation (RESERVED),
          and transitions incident to HOSPITAL_REQUESTED.
        """
        if not hospital_id or not isinstance(hospital_id, str) or not hospital_id.strip():
            raise ValueError("hospitalId is required.")

        hospital_id = hospital_id.strip()

        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        current_status = incident.get("status")
        if current_status not in ("AMBULANCE_ASSIGNED", "HOSPITAL_REJECTED"):
            raise ConditionalUpdateError(
                "Hospital bed reservation can only be requested when the incident "
                "is in AMBULANCE_ASSIGNED or HOSPITAL_REJECTED status."
            )

        existing_res = incident.get("bedReservation")
        if isinstance(existing_res, dict) and existing_res.get("status") in ("RESERVED", "CONFIRMED"):
            raise ConditionalUpdateError(
                "Incident already has an active hospital bed reservation."
            )

        if beds_requested is None:
            beds = incident.get("peopleAffected")
        else:
            beds = beds_requested

        if isinstance(beds, bool) or not isinstance(beds, int) or beds <= 0:
            raise ValueError("bedsRequested must be a positive integer.")

        hospital = self.hospital_repository.get_by_id(hospital_id)
        if hospital is None:
            raise NotFoundError("Hospital not found.")

        if hospital.get("status") != "ACTIVE":
            raise ValueError("Selected hospital is not ACTIVE.")

        if int(hospital.get("availableBeds", 0)) < beds:
            raise ConditionalUpdateError(
                f"Selected hospital has insufficient available beds "
                f"({hospital.get('availableBeds', 0)} available, {beds} requested)."
            )

        now = datetime.now(timezone.utc).isoformat()
        reservation = {
            "reservationId": f"RES-{uuid4().hex[:10].upper()}",
            "incidentId": incident_id,
            "hospitalId": hospital_id,
            "bedsReserved": beds,
            "status": "RESERVED",
            "createdAt": now,
            "updatedAt": now,
            "reason": None,
        }

        transaction_items = [
            {
                "Update": {
                    "TableName": self.table_names["hospitals"],
                    "Key": {"hospitalId": {"S": hospital_id}},
                    "UpdateExpression": "SET #availableBeds = #availableBeds - :beds",
                    "ConditionExpression": (
                        "attribute_exists(#hospitalId) "
                        "AND #status = :active "
                        "AND #availableBeds >= :beds"
                    ),
                    "ExpressionAttributeNames": {
                        "#hospitalId": "hospitalId",
                        "#status": "status",
                        "#availableBeds": "availableBeds",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":active": "ACTIVE",
                        ":beds": Decimal(str(beds)),
                    }),
                }
            },
            {
                "Update": {
                    "TableName": self.table_names["incidents"],
                    "Key": {"incidentId": {"S": incident_id}},
                    "UpdateExpression": (
                        "SET #status = :requested, "
                        "#assignedHospitalId = :hospitalId, "
                        "#hospitalRequestStatus = :pending, "
                        "#hospitalRequestedAt = :requestedAt, "
                        "#hospitalDecisionAt = :nullVal, "
                        "#hospitalRejectionReason = :nullVal, "
                        "#bedReservation = :reservation, "
                        "#updatedAt = :updatedAt"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#incidentId) "
                        "AND #status = :expectedStatus"
                    ),
                    "ExpressionAttributeNames": {
                        "#incidentId": "incidentId",
                        "#status": "status",
                        "#assignedHospitalId": "assignedHospitalId",
                        "#hospitalRequestStatus": "hospitalRequestStatus",
                        "#hospitalRequestedAt": "hospitalRequestedAt",
                        "#hospitalDecisionAt": "hospitalDecisionAt",
                        "#hospitalRejectionReason": "hospitalRejectionReason",
                        "#bedReservation": "bedReservation",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":requested": "HOSPITAL_REQUESTED",
                        ":hospitalId": hospital_id,
                        ":pending": "PENDING",
                        ":requestedAt": now,
                        ":nullVal": None,
                        ":reservation": reservation,
                        ":updatedAt": now,
                        ":expectedStatus": current_status,
                    }),
                }
            },
        ]

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "TransactionCanceledException":
                raise ConditionalUpdateError(
                    "Hospital bed reservation failed due to insufficient capacity "
                    "or concurrent update. Please refresh and try again."
                ) from exc
            raise

        return {
            "incident": self.incident_repository.get_by_id(incident_id),
            "hospital": self.hospital_repository.get_by_id(hospital_id),
            "reservation": reservation,
        }

    def record_hospital_decision(self, incident_id, decision, reason=None):
        """
        Record hospital admission decision (ACCEPTED or REJECTED) for an active
        RESERVED bed reservation.

        - On ACCEPTED: transitions reservation RESERVED -> CONFIRMED and incident
          to HOSPITAL_ACCEPTED + records hospitalAcceptedAt. Does NOT decrement
          hospital beds again (already decremented atomically at reservation).
        - On REJECTED: atomically returns reserved beds to the hospital,
          transitions reservation RESERVED -> REJECTED, appends to bounded
          reservationHistory, and moves incident to HOSPITAL_REJECTED.
          Conditional check on bedReservation.status == RESERVED prevents
          duplicate bed releases.
        """
        if decision not in ("ACCEPTED", "REJECTED"):
            raise ValueError("Decision must be ACCEPTED or REJECTED.")

        if reason is not None and not isinstance(reason, str):
            raise ValueError("Rejection reason must be a string.")

        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        if incident.get("status") != "HOSPITAL_REQUESTED":
            raise ConditionalUpdateError(
                "Hospital decision can only be recorded for incidents in "
                "HOSPITAL_REQUESTED status."
            )

        reservation = incident.get("bedReservation")
        if not isinstance(reservation, dict) or reservation.get("status") != "RESERVED":
            raise ConditionalUpdateError(
                "An active RESERVED bed reservation is required."
            )

        hospital_id = reservation.get("hospitalId") or incident.get("assignedHospitalId")
        if not hospital_id:
            raise ValueError("Incident has no requested hospital.")

        beds_reserved = int(reservation.get("bedsReserved", 0))
        if beds_reserved <= 0:
            raise ValueError("Invalid reserved bed count.")

        now = datetime.now(timezone.utc).isoformat()

        if decision == "ACCEPTED":
            confirmed_reservation = {
                **reservation,
                "status": "CONFIRMED",
                "updatedAt": now,
            }
            history = self._append_bounded_history(
                incident.get("reservationHistory"),
                confirmed_reservation,
            )

            transaction_items = [
                {
                    "Update": {
                        "TableName": self.table_names["incidents"],
                        "Key": {"incidentId": {"S": incident_id}},
                        "UpdateExpression": (
                            "SET #status = :accepted, "
                            "#hospitalRequestStatus = :acceptedReq, "
                            "#hospitalAcceptedAt = :acceptedAt, "
                            "#hospitalDecisionAt = :decisionAt, "
                            "#bedReservation = :confirmedReservation, "
                            "#reservationHistory = :history, "
                            "#updatedAt = :updatedAt"
                        ),
                        "ConditionExpression": (
                            "attribute_exists(#incidentId) "
                            "AND #status = :requested "
                            "AND #bedReservation.#status = :reserved"
                        ),
                        "ExpressionAttributeNames": {
                            "#incidentId": "incidentId",
                            "#status": "status",
                            "#hospitalRequestStatus": "hospitalRequestStatus",
                            "#hospitalAcceptedAt": "hospitalAcceptedAt",
                            "#hospitalDecisionAt": "hospitalDecisionAt",
                            "#bedReservation": "bedReservation",
                            "#reservationHistory": "reservationHistory",
                            "#updatedAt": "updatedAt",
                        },
                        "ExpressionAttributeValues": self._serialize_values({
                            ":accepted": "HOSPITAL_ACCEPTED",
                            ":acceptedReq": "ACCEPTED",
                            ":acceptedAt": now,
                            ":decisionAt": now,
                            ":confirmedReservation": confirmed_reservation,
                            ":history": history,
                            ":updatedAt": now,
                            ":requested": "HOSPITAL_REQUESTED",
                            ":reserved": "RESERVED",
                        }),
                    }
                }
            ]

            try:
                self.transaction_client.transact_write_items(
                    TransactItems=transaction_items
                )
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code == "TransactionCanceledException":
                    raise ConditionalUpdateError(
                        "Hospital acceptance failed because the reservation state changed."
                    ) from exc
                raise

            return {
                "incident": self.incident_repository.get_by_id(incident_id),
                "hospital": self.hospital_repository.get_by_id(hospital_id),
                "reservation": confirmed_reservation,
            }

        # decision == "REJECTED": atomically release beds back to hospital
        cleaned_reason = reason.strip() if reason else None
        rejected_reservation = {
            **reservation,
            "status": "REJECTED",
            "reason": cleaned_reason,
            "updatedAt": now,
        }
        history = self._append_bounded_history(
            incident.get("reservationHistory"),
            rejected_reservation,
        )

        transaction_items = [
            {
                "Update": {
                    "TableName": self.table_names["hospitals"],
                    "Key": {"hospitalId": {"S": hospital_id}},
                    "UpdateExpression": "SET #availableBeds = #availableBeds + :beds",
                    "ConditionExpression": "attribute_exists(#hospitalId)",
                    "ExpressionAttributeNames": {
                        "#hospitalId": "hospitalId",
                        "#availableBeds": "availableBeds",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":beds": Decimal(str(beds_reserved)),
                    }),
                }
            },
            {
                "Update": {
                    "TableName": self.table_names["incidents"],
                    "Key": {"incidentId": {"S": incident_id}},
                    "UpdateExpression": (
                        "SET #status = :rejected, "
                        "#hospitalRequestStatus = :rejectedReq, "
                        "#hospitalDecisionAt = :decisionAt, "
                        "#hospitalRejectionReason = :reason, "
                        "#bedReservation = :rejectedReservation, "
                        "#reservationHistory = :history, "
                        "#updatedAt = :updatedAt"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#incidentId) "
                        "AND #status = :requested "
                        "AND #bedReservation.#status = :reserved"
                    ),
                    "ExpressionAttributeNames": {
                        "#incidentId": "incidentId",
                        "#status": "status",
                        "#hospitalRequestStatus": "hospitalRequestStatus",
                        "#hospitalDecisionAt": "hospitalDecisionAt",
                        "#hospitalRejectionReason": "hospitalRejectionReason",
                        "#bedReservation": "bedReservation",
                        "#reservationHistory": "reservationHistory",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":rejected": "HOSPITAL_REJECTED",
                        ":rejectedReq": "REJECTED",
                        ":decisionAt": now,
                        ":reason": cleaned_reason,
                        ":rejectedReservation": rejected_reservation,
                        ":history": history,
                        ":updatedAt": now,
                        ":requested": "HOSPITAL_REQUESTED",
                        ":reserved": "RESERVED",
                    }),
                }
            },
        ]

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "TransactionCanceledException":
                raise ConditionalUpdateError(
                    "Hospital rejection failed because the reservation was already processed."
                ) from exc
            raise

        return {
            "incident": self.incident_repository.get_by_id(incident_id),
            "hospital": self.hospital_repository.get_by_id(hospital_id),
            "reservation": rejected_reservation,
        }

    def cancel_hospital_reservation(self, incident_id, reason=None):
        """
        Safely cancel an active RESERVED hospital bed reservation.

        Atomically releases reserved beds back to the hospital exactly once,
        marks reservation RELEASED, records bounded history, and moves incident
        back to AMBULANCE_ASSIGNED so another hospital can be chosen without
        re-assigning the ambulance.
        """
        if reason is not None and not isinstance(reason, str):
            raise ValueError("Cancellation reason must be a string.")

        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        if incident.get("status") != "HOSPITAL_REQUESTED":
            raise ConditionalUpdateError(
                "Only an active HOSPITAL_REQUESTED reservation can be cancelled."
            )

        reservation = incident.get("bedReservation")
        if not isinstance(reservation, dict) or reservation.get("status") != "RESERVED":
            raise ConditionalUpdateError(
                "No active RESERVED bed reservation to cancel."
            )

        hospital_id = reservation.get("hospitalId")
        beds_reserved = int(reservation.get("bedsReserved", 0))
        if not hospital_id or beds_reserved <= 0:
            raise ValueError("Invalid reservation metadata.")

        now = datetime.now(timezone.utc).isoformat()
        cleaned_reason = (
            reason.strip() if reason and reason.strip() else "Cancelled by Resource Operator"
        )
        released_reservation = {
            **reservation,
            "status": "RELEASED",
            "reason": cleaned_reason,
            "updatedAt": now,
        }
        history = self._append_bounded_history(
            incident.get("reservationHistory"),
            released_reservation,
        )

        transaction_items = [
            {
                "Update": {
                    "TableName": self.table_names["hospitals"],
                    "Key": {"hospitalId": {"S": hospital_id}},
                    "UpdateExpression": "SET #availableBeds = #availableBeds + :beds",
                    "ConditionExpression": "attribute_exists(#hospitalId)",
                    "ExpressionAttributeNames": {
                        "#hospitalId": "hospitalId",
                        "#availableBeds": "availableBeds",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":beds": Decimal(str(beds_reserved)),
                    }),
                }
            },
            {
                "Update": {
                    "TableName": self.table_names["incidents"],
                    "Key": {"incidentId": {"S": incident_id}},
                    "UpdateExpression": (
                        "SET #status = :assigned, "
                        "#assignedHospitalId = :nullVal, "
                        "#hospitalRequestStatus = :cancelledReq, "
                        "#hospitalDecisionAt = :decisionAt, "
                        "#bedReservation = :releasedReservation, "
                        "#reservationHistory = :history, "
                        "#updatedAt = :updatedAt"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#incidentId) "
                        "AND #status = :requested "
                        "AND #bedReservation.#status = :reserved"
                    ),
                    "ExpressionAttributeNames": {
                        "#incidentId": "incidentId",
                        "#status": "status",
                        "#assignedHospitalId": "assignedHospitalId",
                        "#hospitalRequestStatus": "hospitalRequestStatus",
                        "#hospitalDecisionAt": "hospitalDecisionAt",
                        "#bedReservation": "bedReservation",
                        "#reservationHistory": "reservationHistory",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":assigned": "AMBULANCE_ASSIGNED",
                        ":nullVal": None,
                        ":cancelledReq": "CANCELLED",
                        ":decisionAt": now,
                        ":releasedReservation": released_reservation,
                        ":history": history,
                        ":updatedAt": now,
                        ":requested": "HOSPITAL_REQUESTED",
                        ":reserved": "RESERVED",
                    }),
                }
            },
        ]

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "TransactionCanceledException":
                raise ConditionalUpdateError(
                    "Reservation cancellation failed because it was already processed."
                ) from exc
            raise

        return {
            "incident": self.incident_repository.get_by_id(incident_id),
            "hospital": self.hospital_repository.get_by_id(hospital_id),
            "reservation": released_reservation,
        }

    def mark_patient_transported(self, incident_id):
        """Transition incident from HOSPITAL_ACCEPTED to PATIENT_TRANSPORTED."""
        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        now = datetime.now(timezone.utc).isoformat()
        return self.incident_repository.conditional_update(
            incident_id,
            "HOSPITAL_ACCEPTED",
            {
                "status": "PATIENT_TRANSPORTED",
                "transportedAt": now,
                "updatedAt": now,
            },
        )

    def complete_incident(self, incident_id):
        """
        Complete a PATIENT_TRANSPORTED incident and release the assigned ambulance
        back to AVAILABLE atomically.

        Preserves hospital reservation and history without modifying hospital bed counts.
        """
        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found.")

        if incident.get("status") != "PATIENT_TRANSPORTED":
            raise ConditionalUpdateError(
                "Only PATIENT_TRANSPORTED incidents can be completed."
            )

        now = datetime.now(timezone.utc).isoformat()
        ambulance_id = incident.get("assignedAmbulanceId")

        if not ambulance_id:
            updated_incident = self.incident_repository.conditional_update(
                incident_id,
                "PATIENT_TRANSPORTED",
                {
                    "status": "COMPLETED",
                    "completedAt": now,
                    "updatedAt": now,
                },
            )
            return {
                "incident": updated_incident,
                "ambulance": None,
            }

        transaction_items = [
            {
                "Update": {
                    "TableName": self.table_names["incidents"],
                    "Key": {"incidentId": {"S": incident_id}},
                    "UpdateExpression": (
                        "SET #status = :completed, "
                        "#completedAt = :completedAt, "
                        "#updatedAt = :updatedAt"
                    ),
                    "ConditionExpression": (
                        "attribute_exists(#incidentId) "
                        "AND #status = :transported"
                    ),
                    "ExpressionAttributeNames": {
                        "#incidentId": "incidentId",
                        "#status": "status",
                        "#completedAt": "completedAt",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":completed": "COMPLETED",
                        ":completedAt": now,
                        ":updatedAt": now,
                        ":transported": "PATIENT_TRANSPORTED",
                    }),
                }
            },
            {
                "Update": {
                    "TableName": self.table_names["ambulances"],
                    "Key": {"ambulanceId": {"S": ambulance_id}},
                    "UpdateExpression": (
                        "SET #status = :available, "
                        "#assignedIncidentId = :noneVal"
                    ),
                    "ConditionExpression": "attribute_exists(#ambulanceId)",
                    "ExpressionAttributeNames": {
                        "#ambulanceId": "ambulanceId",
                        "#status": "status",
                        "#assignedIncidentId": "assignedIncidentId",
                    },
                    "ExpressionAttributeValues": self._serialize_values({
                        ":available": "AVAILABLE",
                        ":noneVal": None,
                    }),
                }
            },
        ]

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "TransactionCanceledException":
                raise ConditionalUpdateError(
                    "Incident completion failed because state changed."
                ) from exc
            raise

        return {
            "incident": self.incident_repository.get_by_id(incident_id),
            "ambulance": self.ambulance_repository.get_by_id(ambulance_id),
        }

    def get_dashboard_summary(self):
        """
        Compute live operational dashboard metrics and recent activity timeline
        strictly from persisted records.
        """
        incidents = self.incident_repository.get_all()
        ambulances = self.ambulance_repository.get_all()
        hospitals = self.hospital_repository.get_all()

        total_incidents = len(incidents)
        critical_incidents = sum(1 for i in incidents if i.get("severity") == "CRITICAL")
        high_priority_incidents = sum(1 for i in incidents if i.get("severity") == "HIGH")
        pending_verification = sum(
            1 for i in incidents if i.get("status") in ("CREATED", "UNDER_REVIEW")
        )
        awaiting_ambulance = sum(1 for i in incidents if i.get("status") == "VERIFIED")
        pending_hospital = sum(
            1 for i in incidents if i.get("status") == "HOSPITAL_REQUESTED"
        )
        completed_incidents = sum(1 for i in incidents if i.get("status") == "COMPLETED")
        archived_incidents = sum(1 for i in incidents if i.get("isArchived"))

        available_ambulances = sum(1 for a in ambulances if a.get("status") == "AVAILABLE")
        busy_ambulances = sum(1 for a in ambulances if a.get("status") == "BUSY")

        total_beds = sum(int(h.get("totalBeds") or 0) for h in hospitals)
        total_available_beds = sum(int(h.get("availableBeds") or 0) for h in hospitals)

        total_reserved_beds = 0
        response_durations = []
        activity_events = []

        for inc in incidents:
            res = inc.get("bedReservation")
            if isinstance(res, dict) and res.get("status") in ("RESERVED", "CONFIRMED"):
                total_reserved_beds += int(res.get("bedsReserved") or 0)

            created_dt = parse_utc_timestamp(inc.get("createdAt"))
            assigned_dt = parse_utc_timestamp(inc.get("ambulanceAssignedAt"))
            if created_dt is not None and assigned_dt is not None:
                delta_sec = (assigned_dt - created_dt).total_seconds()
                if delta_sec >= 0:
                    response_durations.append(delta_sec)

            inc_id = inc.get("incidentId")
            inc_type = inc.get("type")
            inc_sev = inc.get("severity")

            milestone_fields = [
                ("createdAt", "Incident Reported"),
                ("verifiedAt", "Incident Verified"),
                ("ambulanceAssignedAt", "Ambulance Dispatched"),
                ("hospitalRequestedAt", "Hospital Beds Reserved"),
                ("hospitalAcceptedAt", "Hospital Admission Confirmed"),
                ("transportedAt", "Patient Transported"),
                ("completedAt", "Incident Completed"),
            ]
            for field_name, label in milestone_fields:
                ts = inc.get(field_name)
                if ts:
                    activity_events.append({
                        "incidentId": inc_id,
                        "type": inc_type,
                        "severity": inc_sev,
                        "status": inc.get("status"),
                        "event": label,
                        "timestamp": ts,
                    })

        avg_response_seconds = (
            round(sum(response_durations) / len(response_durations), 1)
            if response_durations
            else None
        )

        activity_events.sort(
            key=lambda item: item.get("timestamp") or "",
            reverse=True,
        )

        return {
            "totalIncidents": total_incidents,
            "criticalIncidents": critical_incidents,
            "highPriorityIncidents": high_priority_incidents,
            "pendingVerification": pending_verification,
            "awaitingAmbulance": awaiting_ambulance,
            "pendingHospitalAdmission": pending_hospital,
            "completedIncidents": completed_incidents,
            "archivedIncidents": archived_incidents,
            "totalAmbulances": len(ambulances),
            "availableAmbulances": available_ambulances,
            "busyAmbulances": busy_ambulances,
            "totalHospitals": len(hospitals),
            "totalBeds": total_beds,
            "totalAvailableBeds": total_available_beds,
            "totalReservedBeds": total_reserved_beds,
            "averageResponseTimeSeconds": avg_response_seconds,
            "responseTimeSampleCount": len(response_durations),
            "recentActivity": activity_events[:12],
        }
