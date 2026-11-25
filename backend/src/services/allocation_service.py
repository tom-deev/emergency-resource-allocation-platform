import logging
from types import SimpleNamespace
from decimal import Decimal

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from allocation.engine import select_allocation
from constants import INCIDENT_STATUSES


logger = logging.getLogger(__name__)

class AllocationService:
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
    def _to_object(data):
        if isinstance(data, dict):
            return SimpleNamespace(**data)

        return data

    def _serialize_values(self, values):
        return {
            key: self.serializer.serialize(
                Decimal(str(value)) if isinstance(value, float) else value
            )
            for key, value in values.items()
        }

    def _build_transaction(self, incident_id, ambulance_id, hospital_id):
        ambulance_update = {
            "TableName": self.table_names["ambulances"],
            "Key": {
                "ambulanceId": {"S": ambulance_id}
            },
            "UpdateExpression": (
                "SET #status = :busy, "
                "#assignedIncidentId = :incidentId"
            ),
            "ConditionExpression": (
                "attribute_exists(#ambulanceId) "
                "AND #status = :available"
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
            }),
        }

        hospital_update = {
            "TableName": self.table_names["hospitals"],
            "Key": {
                "hospitalId": {"S": hospital_id}
            },
            "UpdateExpression": (
                "SET #availableBeds = #availableBeds - :one"
            ),
            "ConditionExpression": (
                "attribute_exists(#hospitalId) "
                "AND #status = :active "
                "AND #availableBeds > :zero"
            ),
            "ExpressionAttributeNames": {
                "#hospitalId": "hospitalId",
                "#status": "status",
                "#availableBeds": "availableBeds",
            },
            "ExpressionAttributeValues": self._serialize_values({
                ":active": "ACTIVE",
                ":one": Decimal("1"),
                ":zero": Decimal("0"),
            }),
        }
        incident_update = {
            "TableName": self.table_names["incidents"],
            "Key": {
                "incidentId": {"S": incident_id}
            },
            "UpdateExpression": (
                "SET #status = :allocated, "
                "#assignedAmbulanceId = :ambulanceId, "
                "#assignedHospitalId = :hospitalId"
            ),
            "ConditionExpression": (
                "attribute_exists(#incidentId) "
                "AND (#status = :created OR #status = :pending)"
            ),
            "ExpressionAttributeNames": {
                "#incidentId": "incidentId",
                "#status": "status",
                "#assignedAmbulanceId": "assignedAmbulanceId",
                "#assignedHospitalId": "assignedHospitalId",
            },
            "ExpressionAttributeValues": self._serialize_values({
                ":allocated": "ALLOCATED",
                ":ambulanceId": ambulance_id,
                ":hospitalId": hospital_id,
                ":created": "CREATED",
                ":pending": "PENDING",
            }),
        }

        return [
            {"Update": ambulance_update},
            {"Update": hospital_update},
            {"Update": incident_update},
        ]

    def allocate_incident(
        self,
        incident_id,
        required_hospital_facilities,
    ):
        incident = self.incident_repository.get_by_id(incident_id)

        if incident is None:
            raise ValueError("Incident not found.")

        incident = self._to_object(incident)

        if incident.status not in ("CREATED", "PENDING"):
            raise ValueError(
                "Incident must be in CREATED or PENDING status to be allocated."
            )

        ambulances = self.ambulance_repository.get_all()
        hospitals = self.hospital_repository.get_all()

        ambulances = [
            self._to_object(ambulance)
            for ambulance in ambulances
        ]

        hospitals = [
            self._to_object(hospital)
            for hospital in hospitals
        ]

        for hospital in hospitals:
            logger.info(
                "ALLOCATION_DIAGNOSTIC hospital_id=%s availableBeds=%r availableBeds_type=%s",
                getattr(hospital, "hospitalId", None),
                getattr(hospital, "availableBeds", None),
                type(getattr(hospital, "availableBeds", None)).__name__,
            )

        allocation = select_allocation(
            incident,
            ambulances,
            hospitals,
            required_hospital_facilities,
        )

        if allocation is None:
            raise ValueError(
                "No suitable ambulance and hospital are available."
            )

        ambulance_id = allocation["ambulanceId"]
        hospital_id = allocation["hospitalId"]

        logger.info(
            "ALLOCATION_DIAGNOSTIC selected_hospital_id=%s selected_ambulance_id=%s",
            hospital_id,
            ambulance_id,
        )

        transaction_items = self._build_transaction(
            incident_id,
            ambulance_id,
            hospital_id,
        )

        try:
            self.transaction_client.transact_write_items(
                TransactItems=transaction_items
            )

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")

            if error_code == "TransactionCanceledException":
                logger.error(
                    "ALLOCATION_TRANSACTION_CANCELLED reasons=%s",
                    exc.response.get("CancellationReasons"),
                )

                raise ValueError(
                    "Allocation failed because one or more resources "
                    "changed or are no longer eligible. Please refresh "
                    "and try again."
                ) from exc

            raise

        updated_incident = self.incident_repository.get_by_id(
            incident_id
        )

        return {
            "incident": updated_incident,
            "allocation": allocation,
        }








