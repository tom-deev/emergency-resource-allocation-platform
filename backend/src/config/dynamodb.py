import boto3


USERS_TABLE = "EmergencyUsers"
INCIDENTS_TABLE = "EmergencyIncidents"
AMBULANCES_TABLE = "EmergencyAmbulances"
HOSPITALS_TABLE = "EmergencyHospitals"


def get_dynamodb_resource():
    """
    Return a boto3 DynamoDB resource.

    AWS credentials and region configuration are handled
    by boto3's standard credential/provider chain.
    """
    return boto3.resource("dynamodb")


def get_dynamodb_client():
    """
    Return a low-level boto3 DynamoDB client for TransactWriteItems.

    IMPORTANT: Do NOT use `table.meta.client` from `boto3.resource("dynamodb")`
    for low-level AttributeValue payloads (e.g. `{"S": ...}`), because a
    DynamoDB ServiceResource attaches TransformationInjector to `.meta.client`,
    which double-serializes `{"S": "val"}` into `{"M": {"S": {"S": "val"}}}`
    and triggers DynamoDB ValidationError.
    """
    return boto3.client("dynamodb")


def get_table(table_name):
    """
    Return a DynamoDB table resource by table name.
    """
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)
