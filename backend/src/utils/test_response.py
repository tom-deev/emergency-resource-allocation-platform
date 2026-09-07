from response import success_response, error_response


# Success response
result = success_response(
    {"message": "Incident created"},
    201,
)

assert result["statusCode"] == 201
assert result["headers"]["Content-Type"] == "application/json"
assert '"message": "Incident created"' in result["body"]

print("Success response: PASSED")


# Default success status
result = success_response(
    {"message": "OK"},
)

assert result["statusCode"] == 200

print("Default success status: PASSED")


# Error response
result = error_response(
    "Invalid incident data",
    400,
)

assert result["statusCode"] == 400
assert result["headers"]["Content-Type"] == "application/json"
assert '"error": "Invalid incident data"' in result["body"]

print("Error response: PASSED")


# Default error status
result = error_response(
    "Something went wrong",
)

assert result["statusCode"] == 400

print("Default error status: PASSED")


print("ALL RESPONSE UTILITY TESTS PASSED")
