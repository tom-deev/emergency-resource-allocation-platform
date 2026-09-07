import hashlib


class User:
    def __init__(
        self,
        userId,
        username,
        role,
        passwordHash=None,
    ):
        self.userId = userId
        self.username = username
        self.role = role
        self.passwordHash = passwordHash

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

    def to_dict(self):
        return {
            "userId": self.userId,
            "username": self.username,
            "role": self.role,
            "passwordHash": self.passwordHash,
        }
