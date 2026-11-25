from botocore.exceptions import ClientError


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

    def set_otp_challenge(
        self,
        user_id,
        challenge_id,
        otp_hash,
        expires_at,
        max_attempts=5,
    ):
        """
        Store a fresh OTP challenge on the user's EmergencyUsers item,
        automatically invalidating any previous OTP challenge.
        """
        response = self.table.update_item(
            Key={"userId": user_id},
            UpdateExpression=(
                "SET #otpChallengeId = :cid, "
                "#otpHash = :otpHash, "
                "#otpExpiresAt = :exp, "
                "#otpAttempts = :zero, "
                "#otpMaxAttempts = :maxAttempts, "
                "#otpUsed = :falseVal"
            ),
            ConditionExpression="attribute_exists(#userId)",
            ExpressionAttributeNames={
                "#userId": "userId",
                "#otpChallengeId": "otpChallengeId",
                "#otpHash": "otpHash",
                "#otpExpiresAt": "otpExpiresAt",
                "#otpAttempts": "otpAttempts",
                "#otpMaxAttempts": "otpMaxAttempts",
                "#otpUsed": "otpUsed",
            },
            ExpressionAttributeValues={
                ":cid": challenge_id,
                ":otpHash": otp_hash,
                ":exp": expires_at,
                ":zero": 0,
                ":maxAttempts": max_attempts,
                ":falseVal": False,
            },
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def consume_otp_challenge(self, user_id, challenge_id, expected_otp_hash):
        """
        Atomically verify and consume an active OTP challenge.
        Returns updated user attributes on success, or None if the condition
        failed (already used, concurrent winner, expired/replaced, or hash mismatch).
        """
        try:
            response = self.table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET #otpUsed = :trueVal, #otpHash = :nullVal",
                ConditionExpression=(
                    "attribute_exists(#userId) "
                    "AND #otpChallengeId = :cid "
                    "AND #otpUsed = :falseVal "
                    "AND #otpHash = :expectedHash "
                    "AND #otpAttempts < #otpMaxAttempts"
                ),
                ExpressionAttributeNames={
                    "#userId": "userId",
                    "#otpChallengeId": "otpChallengeId",
                    "#otpUsed": "otpUsed",
                    "#otpHash": "otpHash",
                    "#otpAttempts": "otpAttempts",
                    "#otpMaxAttempts": "otpMaxAttempts",
                },
                ExpressionAttributeValues={
                    ":trueVal": True,
                    ":nullVal": None,
                    ":cid": challenge_id,
                    ":falseVal": False,
                    ":expectedHash": expected_otp_hash,
                },
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return None
            raise

    def increment_otp_attempts(self, user_id, challenge_id):
        """
        Atomically increment failed OTP verification attempts for the active challenge.
        Returns updated attributes or None if the challenge is no longer active.
        """
        try:
            response = self.table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET #otpAttempts = #otpAttempts + :one",
                ConditionExpression=(
                    "attribute_exists(#userId) "
                    "AND #otpChallengeId = :cid "
                    "AND #otpUsed = :falseVal "
                    "AND #otpAttempts < #otpMaxAttempts"
                ),
                ExpressionAttributeNames={
                    "#userId": "userId",
                    "#otpChallengeId": "otpChallengeId",
                    "#otpUsed": "otpUsed",
                    "#otpAttempts": "otpAttempts",
                    "#otpMaxAttempts": "otpMaxAttempts",
                },
                ExpressionAttributeValues={
                    ":one": 1,
                    ":cid": challenge_id,
                    ":falseVal": False,
                },
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return None
            raise

    def invalidate_otp_challenge(self, user_id, challenge_id):
        """Mark the specified OTP challenge as used and clear its hash."""
        try:
            self.table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET #otpUsed = :trueVal, #otpHash = :nullVal",
                ConditionExpression=(
                    "attribute_exists(#userId) AND #otpChallengeId = :cid"
                ),
                ExpressionAttributeNames={
                    "#userId": "userId",
                    "#otpChallengeId": "otpChallengeId",
                    "#otpUsed": "otpUsed",
                    "#otpHash": "otpHash",
                },
                ExpressionAttributeValues={
                    ":trueVal": True,
                    ":nullVal": None,
                    ":cid": challenge_id,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return
            raise
