from constants import USER_ROLES


class UserService:
    def __init__(self, user_repository):
        self.user_repository = user_repository

    @staticmethod
    def _get_value(user, field):
        if isinstance(user, dict):
            return user.get(field)

        return getattr(user, field, None)

    def create_user(self, user):
        username = self._get_value(user, "username")
        role = self._get_value(user, "role")

        if not username:
            raise ValueError("Username is required.")

        if role not in USER_ROLES:
            raise ValueError(f"Invalid user role: {role}")

        existing_user = self.user_repository.find_by_username(
            username
        )

        if existing_user:
            raise ValueError("Username already exists.")

        return self.user_repository.create(user)

    def authenticate_user(self, username, password_hash):
        if not username:
            raise ValueError("Username is required.")

        if not password_hash:
            raise ValueError("Password is required.")

        user = self.user_repository.find_by_username(username)

        if user is None:
            raise ValueError("Invalid username or password.")

        if user.get("passwordHash") != password_hash:
            raise ValueError("Invalid username or password.")

        return user

    def get_user(self, user_id):
        return self.user_repository.get_by_id(user_id)

    def get_all_users(self):
        return self.user_repository.get_all()

    def find_by_username(self, username):
        if not username:
            raise ValueError("Username is required.")

        return self.user_repository.find_by_username(username)
