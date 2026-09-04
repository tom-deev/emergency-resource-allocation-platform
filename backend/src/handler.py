from config import APP_NAME


def lambda_handler(event, context):
    """
    Minimal AWS Lambda entry point.

    This is the initial backend foundation.
    Application logic will be added incrementally.
    """
    return {
        "statusCode": 200,
        "body": f"{APP_NAME} backend is running."
    }