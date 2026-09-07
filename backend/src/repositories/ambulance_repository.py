class AmbulanceRepository:
    """
    Repository for ambulance persistence.
    """

    def __init__(self, table):
        self.table = table

    def create(self, ambulance):
        item = {
            "ambulanceId": ambulance.ambulanceId,
            "registrationNumber": ambulance.registrationNumber,
            "latitude": ambulance.latitude,
            "longitude": ambulance.longitude,
            "status": ambulance.status,
            "equipment": ambulance.equipment,
            "assignedIncidentId": ambulance.assignedIncidentId,
        }

        self.table.put_item(Item=item)

        return item

    def get_by_id(self, ambulance_id):
        response = self.table.get_item(
            Key={"ambulanceId": ambulance_id}
        )
        return response.get("Item")

    def get_all(self):
        response = self.table.scan()
        return response.get("Items", [])

    def update(self, ambulance_id, data):
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
            Key={"ambulanceId": ambulance_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        return response.get("Attributes")
