from user_service import UserService


class FakeUserRepository:
    def __init__(self):
        self.created_user = None

    def create(self, user):
        self.created_user = user
        return user

    def get_by_id(self, user_id):
        return {"userId": user_id}

    def get_all(self):
        return [{"userId": "USR001"}]

    def find_by_username(self, username):
        if self.created_user is not None:
            created_username = (
                self.created_user.get("username")
                if isinstance(self.created_user, dict)
                else getattr(self.created_user, "username", None)
            )

            if created_username == username:
                return self.created_user

        return None


repository = FakeUserRepository()
service = UserService(repository)


user = {
    "userId": "USR001",
    "username": "dispatcher1",
    "role": "DISPATCHER",
}


# Create
result = service.create_user(user)

assert result == user
assert repository.created_user == user
print("User create service: PASSED")


# Get by ID
result = service.get_user("USR001")

assert result["userId"] == "USR001"
print("User get service: PASSED")


# Get all
result = service.get_all_users()

assert len(result) == 1
assert result[0]["userId"] == "USR001"
print("User get_all service: PASSED")


# Find by username
result = service.find_by_username("dispatcher1")

assert result["username"] == "dispatcher1"
assert result["role"] == "DISPATCHER"
print("Username lookup service: PASSED")


# Invalid role
invalid_user = {
    "userId": "USR002",
    "username": "testuser",
    "role": "ADMIN",
}

try:
    service.create_user(invalid_user)
    raise AssertionError("Invalid role was accepted")
except ValueError:
    pass

print("Invalid role handling: PASSED")


# Empty user
try:
    service.create_user({})
    raise AssertionError("Empty user was accepted")
except ValueError:
    pass

print("Empty user handling: PASSED")


# Empty username
try:
    service.find_by_username("")
    raise AssertionError("Empty username was accepted")
except ValueError:
    pass

print("Empty username handling: PASSED")


print("ALL USER SERVICE TESTS PASSED")
