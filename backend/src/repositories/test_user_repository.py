from user_repository import UserRepository


class FakeTable:
    def __init__(self):
        self.scan_result = {
            "Items": [
                {
                    "userId": "USR001",
                    "username": "dispatcher1",
                    "role": "DISPATCHER",
                }
            ]
        }

        self.scan_arguments = None

    def scan(self, **kwargs):
        self.scan_arguments = kwargs
        return self.scan_result


table = FakeTable()
repository = UserRepository(table)


# Existing get_all operation
result = repository.get_all()

assert len(result) == 1
assert result[0]["username"] == "dispatcher1"
print("User get_all: PASSED")


# Username lookup
result = repository.find_by_username("dispatcher1")

assert result is not None
assert result["userId"] == "USR001"
assert result["username"] == "dispatcher1"
assert result["role"] == "DISPATCHER"

assert table.scan_arguments["FilterExpression"] == "#username = :username"
assert table.scan_arguments["ExpressionAttributeNames"] == {
    "#username": "username"
}
assert table.scan_arguments["ExpressionAttributeValues"] == {
    ":username": "dispatcher1"
}

print("User find_by_username: PASSED")


# Missing username
table.scan_result = {"Items": []}

result = repository.find_by_username("unknown")

assert result is None

print("Missing username handling: PASSED")


print("ALL USER REPOSITORY TESTS PASSED")
