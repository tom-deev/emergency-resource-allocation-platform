import json


CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def success_response(data, status_code=200):
    """
    Create a successful API response.
    """
    return {
        "statusCode": status_code,
        "headers": dict(CORS_HEADERS),
        "body": json.dumps(data),
    }


def error_response(message, status_code=400):
    """
    Create an error API response.
    """
    return {
        "statusCode": status_code,
        "headers": dict(CORS_HEADERS),
        "body": json.dumps({
            "error": message,
        }),
    }


def preflight_response():
    """
    Create a CORS preflight OPTIONS response.
    """
    return {
        "statusCode": 200,
        "headers": dict(CORS_HEADERS),
        "body": "",
    }
