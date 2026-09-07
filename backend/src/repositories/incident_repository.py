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
            "peopleAffected": incident.peopleAffected,
            "status": incident.status,
            "createdAt": incident.createdAt,
            "updatedAt": incident.updatedAt,
            "requiredResources": incident.requiredResources,
            "requiredEquipment": incident.requiredEquipment,
            "assignedAmbulanceId": incident.assignedAmbulanceId,
            "assignedHospitalId": incident.assignedHospitalId,
        }

        self.table.put_item(Item=item)

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
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        return response.get("Attributes")
