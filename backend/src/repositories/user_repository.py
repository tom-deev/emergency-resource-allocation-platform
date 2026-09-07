class UserRepository:
    def __init__(self, table):
        self.table = table

    @staticmethod
    def _to_dict(user):
        if isinstance(user, dict):
            return user

        if hasattr(user, "to_dict"):
            return user.to_dict()

        return vars(user)

    def create(self, user):
        user_data = self._to_dict(user)

        item = {
            "userId": user_data["userId"],
            "username": user_data["username"],
            "role": user_data["role"],
        }

        if user_data.get("passwordHash"):
            item["passwordHash"] = user_data["passwordHash"]

        self.table.put_item(Item=item)

        return item

    def get_by_id(self, user_id):
        response = self.table.get_item(
            Key={"userId": user_id}
        )

        return response.get("Item")

    def get_all(self):
        response = self.table.scan()

        return response.get("Items", [])

    def find_by_username(self, username):
        response = self.table.scan(
            FilterExpression="#username = :username",
            ExpressionAttributeNames={
                "#username": "username"
            },
            ExpressionAttributeValues={
                ":username": username
            },
        )

        items = response.get("Items", [])

        return items[0] if items else None
