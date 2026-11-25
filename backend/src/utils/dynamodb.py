from decimal import Decimal


def to_dynamodb_compatible(value):
    """Convert Python floats recursively into DynamoDB-compatible Decimals."""

    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {
            key: to_dynamodb_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [to_dynamodb_compatible(item) for item in value]

    if isinstance(value, tuple):
        return tuple(to_dynamodb_compatible(item) for item in value)

    return value
