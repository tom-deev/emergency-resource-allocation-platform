from botocore.exceptions import ClientError
from utils.dynamodb import to_dynamodb_compatible

class ConditionalUpdateError(Exception):
    """Raised when a conditional database update cannot be completed."""


class IncidentRepository:
    """
    Repository for incident persistence.
    """

    def __init__(self, table):
        self.table = table

    def create(self, incident):
        item = {
            "incidentId": incident.incidentId,
            "type": incident.type,
            "description": incident.description,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "severity": incident.severity,
            "priority": getattr(incident, "priority", None),
            "createdBy": getattr(incident, "createdBy", None),
            "createdByUsername": getattr(incident, "createdByUsername", None),
            "peopleAffected": incident.peopleAffected,
            "status": incident.status,
            "createdAt": incident.createdAt,
            "updatedAt": incident.updatedAt,
            "requiredResources": incident.requiredResources,
            "requiredEquipment": incident.requiredEquipment,
            "assignedAmbulanceId": incident.assignedAmbulanceId,
            "assignedHospitalId": incident.assignedHospitalId,
            "hospitalRequestStatus": incident.hospitalRequestStatus,
            "hospitalRequestedAt": incident.hospitalRequestedAt,
            "hospitalAcceptedAt": getattr(incident, "hospitalAcceptedAt", None),
            "hospitalDecisionAt": incident.hospitalDecisionAt,
            "hospitalRejectionReason": incident.hospitalRejectionReason,
            "reviewedBy": incident.reviewedBy,
            "reviewedAt": incident.reviewedAt,
            "verifiedAt": getattr(incident, "verifiedAt", None),
            "verificationRemarks": incident.verificationRemarks,
            "ambulanceAssignedAt": getattr(incident, "ambulanceAssignedAt", None),
            "transportedAt": getattr(incident, "transportedAt", None),
            "completedAt": getattr(incident, "completedAt", None),
            "bedReservation": getattr(incident, "bedReservation", None),
            "reservationHistory": getattr(incident, "reservationHistory", []),
            "isArchived": bool(getattr(incident, "isArchived", False)),
            "archivedAt": getattr(incident, "archivedAt", None),
            "archivedBy": getattr(incident, "archivedBy", None),
        }

        self.table.put_item(Item=to_dynamodb_compatible(item))

        return item

    def get_by_id(self, incident_id):
        response = self.table.get_item(
            Key={"incidentId": incident_id}
        )
        return response.get("Item")

    def get_all(self):
        response = self.table.scan()
        return response.get("Items", [])

    def update(self, incident_id, data):
        if not data:
            raise ValueError("Update data cannot be empty.")

        update_parts = []
        expression_names = {}
        expression_values = {}

        for field, value in data.items():
            update_parts.append(f"#{field} = :{field}")
            expression_names[f"#{field}"] = field
            expression_values[f":{field}"] = value

        response = self.table.update_item(
            Key={"incidentId": incident_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=to_dynamodb_compatible(expression_values),
            ReturnValues="ALL_NEW",
        )

        return response.get("Attributes")



    def conditional_update(self, incident_id, expected_status, data):
        """
        Update an incident only if it exists and its current status
        matches the expected status.

        DynamoDB evaluates the condition atomically with the update.
        """

        if not data:
            raise ValueError("Update data cannot be empty.")

        if not expected_status:
            raise ValueError("Expected status is required.")

        if "incidentId" in data:
            raise ValueError("Incident ID cannot be modified.")

        update_parts = []
        expression_names = {
            "#condition_key": "incidentId",
            "#condition_status": "status",
        }
        expression_values = {
            ":expected_status": expected_status,
        }

        for index, (field, value) in enumerate(data.items()):
            name_token = f"#field_{index}"
            value_token = f":value_{index}"

            update_parts.append(f"{name_token} = {value_token}")
            expression_names[name_token] = field
            expression_values[value_token] = value

        try:
            response = self.table.update_item(
                Key={"incidentId": incident_id},
                UpdateExpression="SET " + ", ".join(update_parts),
                ConditionExpression=(
                    "attribute_exists(#condition_key) "
                    "AND #condition_status = :expected_status"
                ),
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=to_dynamodb_compatible(
                    expression_values
                ),
                ReturnValues="ALL_NEW",
            )

            return response.get("Attributes")

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")

            if error_code == "ConditionalCheckFailedException":
                raise ConditionalUpdateError(
                    "Incident does not exist or its status has changed."
                ) from exc

            raise

    def archive_conditional_update(self, incident_id, archived_by, archived_at):
        """
        Atomically archive a COMPLETED, non-archived incident without changing
        its workflow status or overwriting historical fields.
        """
        try:
            response = self.table.update_item(
                Key={"incidentId": incident_id},
                UpdateExpression=(
                    "SET #isArchived = :trueVal, "
                    "#archivedAt = :archivedAt, "
                    "#archivedBy = :archivedBy, "
                    "#updatedAt = :updatedAt"
                ),
                ConditionExpression=(
                    "attribute_exists(#incidentId) "
                    "AND #status = :completed "
                    "AND (attribute_not_exists(#isArchived) OR #isArchived = :falseVal)"
                ),
                ExpressionAttributeNames={
                    "#incidentId": "incidentId",
                    "#status": "status",
                    "#isArchived": "isArchived",
                    "#archivedAt": "archivedAt",
                    "#archivedBy": "archivedBy",
                    "#updatedAt": "updatedAt",
                },
                ExpressionAttributeValues=to_dynamodb_compatible({
                    ":trueVal": True,
                    ":falseVal": False,
                    ":completed": "COMPLETED",
                    ":archivedAt": archived_at,
                    ":archivedBy": archived_by,
                    ":updatedAt": archived_at,
                }),
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "ConditionalCheckFailedException":
                raise ConditionalUpdateError(
                    "Only non-archived COMPLETED incidents can be archived."
                ) from exc
            raise
