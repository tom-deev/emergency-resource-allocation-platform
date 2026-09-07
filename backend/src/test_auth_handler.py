import json

import handler


class FakeUserService:
    def create_user(self, user):
        return {
            "userId": user.userId,
            "username": user.username,
            "role": user.role,
            "passwordHash": user.passwordHash,
        }

    def authenticate_user(self, username, password_hash):
        return {
            "userId": "USER001",
            "username": username,
            "role": "DISPATCHER",
            "passwordHash": password_hash,
        }


def test_register():
    original = handler.get_user_service

    try:
        handler.get_user_service = lambda: FakeUserService()

        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps(
                {
                    "username": "dispatcher1",
                    "password": "test123",
                    "role": "DISPATCHER",
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 201

        body = json.loads(response["body"])

        assert body["username"] == "dispatcher1"
        assert body["role"] == "DISPATCHER"
        assert "passwordHash" not in body

        print("POST /auth/register: PASSED")

    finally:
        handler.get_user_service = original


def test_login():
    original = handler.get_user_service

    try:
        handler.get_user_service = lambda: FakeUserService()

        event = {
            "httpMethod": "POST",
            "path": "/auth/login",
            "body": json.dumps(
                {
                    "username": "dispatcher1",
                    "password": "test123",
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 200

        body = json.loads(response["body"])

        assert body["message"] == "Login successful."
        assert body["user"]["username"] == "dispatcher1"
        assert body["user"]["role"] == "DISPATCHER"
        assert "passwordHash" not in body["user"]

        print("POST /auth/login: PASSED")

    finally:
        handler.get_user_service = original


def test_missing_password():
    original = handler.get_user_service

    try:
        handler.get_user_service = lambda: FakeUserService()

        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps(
                {
                    "username": "dispatcher1",
                    "role": "DISPATCHER",
                }
            ),
        }

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400

        body = json.loads(response["body"])

        assert body["error"] == "Password is required."

        print("Registration password validation: PASSED")

    finally:
        handler.get_user_service = original


if __name__ == "__main__":
    test_register()
    test_login()
    test_missing_password()

    print("ALL AUTHENTICATION API TESTS PASSED")
