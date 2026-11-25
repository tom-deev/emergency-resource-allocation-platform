"""
Local Development HTTP Server (SIMULATED IN-MEMORY DYNAMODB).

WARNING:
This server is for LOCAL DEVELOPMENT and LOCAL DEMONSTRATION ONLY.
It uses an in-memory mock DynamoDB implementation and does NOT connect
to live AWS DynamoDB. It invokes the exact same `handler.lambda_handler`,
services, validators, and repositories used in AWS Lambda.

Usage (from repository root in PowerShell):
    .\\backend\\.venv\\Scripts\\python.exe backend\\local_server.py
"""

from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import sys
import threading
from urllib.parse import parse_qs, urlparse

from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

# Ensure backend/src is importable
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_SRC = os.path.join(BACKEND_DIR, "src")
if BACKEND_SRC not in sys.path:
    sys.path.insert(0, BACKEND_SRC)


def _load_local_env_file():
    """
    Load local environment variables from backend/.env if present.
    Existing process environment variables take precedence.
    """
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val


# Load backend/.env BEFORE configuring OTP delivery or importing handler
_load_local_env_file()

# Configure an ephemeral local signing secret if not provided via env var
if not os.environ.get("AUTH_TOKEN_SECRET"):
    os.environ["AUTH_TOKEN_SECRET"] = secrets.token_hex(32)

# Default to Gmail SMTP OTP delivery; never default to terminal OTP printing
os.environ.setdefault("OTP_DELIVERY_MODE", "gmail")
os.environ.setdefault("LOCAL_OTP_CONSOLE", "false")

import config.dynamodb as dynamodb_config
import handler
from models.ambulance import Ambulance
from models.hospital import Hospital
from models.incident import Incident
from models.user import User


_DESERIALIZER = TypeDeserializer()


def _deserialize_attr_map(attr_map):
    return {k: _DESERIALIZER.deserialize(v) for k, v in attr_map.items()}


def _normalize_value(val):
    if isinstance(val, Decimal):
        return int(val) if val % 1 == 0 else float(val)
    if isinstance(val, dict):
        return {k: _normalize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_normalize_value(v) for v in val]
    return val


class InMemoryDynamoClient:
    """Simulates boto3 DynamoDB client.transact_write_items atomically in memory."""

    def __init__(self, tables_by_name, lock):
        self.tables_by_name = tables_by_name
        self.lock = lock

    @staticmethod
    def _resolve_field_value(item, expr_path, names):
        if item is None:
            return None
        current = item
        for part in expr_path.split("."):
            key = names.get(part, part)
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def _evaluate_condition(self, item, condition, names, values):
        if not condition:
            return True

        # Split simple AND conditions used by our repositories/services
        clauses = [c.strip() for c in condition.split(" AND ")]
        for clause in clauses:
            if clause.startswith("attribute_exists("):
                if item is None:
                    return False
            elif " >= " in clause:
                lhs, rhs = [p.strip() for p in clause.split(" >= ", 1)]
                threshold = _normalize_value(values[rhs])
                current = _normalize_value(self._resolve_field_value(item, lhs, names))
                if current is None or not (current >= threshold):
                    return False
            elif " < " in clause:
                lhs, rhs = [p.strip() for p in clause.split(" < ", 1)]
                left_val = _normalize_value(self._resolve_field_value(item, lhs, names))
                right_val = (
                    _normalize_value(values[rhs])
                    if rhs in values
                    else _normalize_value(self._resolve_field_value(item, rhs, names))
                )
                if left_val is None or right_val is None or not (left_val < right_val):
                    return False
            elif " > " in clause:
                lhs, rhs = [p.strip() for p in clause.split(" > ", 1)]
                threshold = _normalize_value(values[rhs])
                current = _normalize_value(self._resolve_field_value(item, lhs, names))
                if current is None or not (current > threshold):
                    return False
            elif " = " in clause:
                # Handle parenthesized OR clauses like (#status = :created OR #status = :pending)
                if clause.startswith("(") and clause.endswith(")") and " OR " in clause:
                    subclauses = [s.strip() for s in clause[1:-1].split(" OR ")]
                    matched = False
                    for sub in subclauses:
                        if sub.startswith("attribute_not_exists(") and sub.endswith(")"):
                            raw_attr = sub[len("attribute_not_exists("):-1].strip()
                            if self._resolve_field_value(item, raw_attr, names) is None:
                                matched = True
                                break
                        elif " = " in sub:
                            lhs, rhs = [p.strip() for p in sub.split(" = ", 1)]
                            expected = _normalize_value(values[rhs])
                            if item and _normalize_value(self._resolve_field_value(item, lhs, names)) == expected:
                                matched = True
                                break
                    if not matched:
                        return False
                else:
                    lhs, rhs = [p.strip() for p in clause.split(" = ", 1)]
                    expected = _normalize_value(values[rhs])
                    if not item or _normalize_value(self._resolve_field_value(item, lhs, names)) != expected:
                        return False
        return True

    def _apply_update(self, item, update_expr, names, values):
        expr = update_expr.strip()
        if expr.upper().startswith("SET "):
            expr = expr[4:]
        assignments = [a.strip() for a in expr.split(",")]
        for assignment in assignments:
            lhs, rhs = [p.strip() for p in assignment.split("=", 1)]
            field = names.get(lhs, lhs)
            if " - " in rhs:
                left_op, right_op = [p.strip() for p in rhs.split(" - ", 1)]
                left_val = _normalize_value(self._resolve_field_value(item, left_op, names)) or 0
                delta = _normalize_value(values[right_op])
                item[field] = left_val - delta
            elif " + " in rhs:
                left_op, right_op = [p.strip() for p in rhs.split(" + ", 1)]
                left_val = _normalize_value(self._resolve_field_value(item, left_op, names)) or 0
                delta = _normalize_value(values[right_op])
                item[field] = left_val + delta
            else:
                item[field] = _normalize_value(values[rhs])

    def transact_write_items(self, TransactItems):
        with self.lock:
            # Phase 1: Validate all conditions before mutating anything
            prepared = []
            for entry in TransactItems:
                upd = entry["Update"]
                table = self.tables_by_name[upd["TableName"]]
                key_dict = _deserialize_attr_map(upd["Key"])
                pk_val = key_dict[table.pk_name]
                item = table.items.get(pk_val)
                names = upd.get("ExpressionAttributeNames", {})
                values = _deserialize_attr_map(upd.get("ExpressionAttributeValues", {}))
                condition = upd.get("ConditionExpression")

                if not self._evaluate_condition(item, condition, names, values):
                    raise ClientError(
                        {
                            "Error": {
                                "Code": "TransactionCanceledException",
                                "Message": "ConditionalCheckFailed in local mock transaction",
                            }
                        },
                        "TransactWriteItems",
                    )
                prepared.append((table, pk_val, upd["UpdateExpression"], names, values))

            # Phase 2: Apply all mutations atomically
            for table, pk_val, update_expr, names, values in prepared:
                item = table.items[pk_val]
                self._apply_update(item, update_expr, names, values)


class InMemoryTable:
    """Simulates a boto3 DynamoDB Table resource in memory."""

    def __init__(self, name, pk_name, client, lock):
        self.name = name
        self.pk_name = pk_name
        self.items = {}
        self.lock = lock
        self.meta = type("Meta", (), {"client": client})()

    def put_item(self, Item):
        with self.lock:
            normalized = _normalize_value(Item)
            self.items[normalized[self.pk_name]] = normalized

    def get_item(self, Key, **kwargs):
        with self.lock:
            pk_val = Key[self.pk_name]
            item = self.items.get(pk_val)
            return {"Item": dict(item)} if item is not None else {}

    def scan(self, FilterExpression=None, ExpressionAttributeNames=None, ExpressionAttributeValues=None):
        with self.lock:
            results = [dict(item) for item in self.items.values()]
            if FilterExpression and ExpressionAttributeNames and ExpressionAttributeValues:
                # Supports simple equality filter like "#username = :username"
                lhs, rhs = [p.strip() for p in FilterExpression.split(" = ", 1)]
                field = ExpressionAttributeNames.get(lhs, lhs)
                expected = _normalize_value(ExpressionAttributeValues[rhs])
                results = [i for i in results if _normalize_value(i.get(field)) == expected]
            return {"Items": results}

    def update_item(
        self,
        Key,
        UpdateExpression,
        ExpressionAttributeNames,
        ExpressionAttributeValues,
        ConditionExpression=None,
        ReturnValues=None,
    ):
        with self.lock:
            pk_val = Key[self.pk_name]
            item = self.items.get(pk_val)

            if ConditionExpression:
                if not self.meta.client._evaluate_condition(
                    item,
                    ConditionExpression,
                    ExpressionAttributeNames,
                    ExpressionAttributeValues,
                ):
                    raise ClientError(
                        {
                            "Error": {
                                "Code": "ConditionalCheckFailedException",
                                "Message": "The conditional request failed",
                            }
                        },
                        "UpdateItem",
                    )

            if item is None:
                item = {self.pk_name: pk_val}
                self.items[pk_val] = item

            self.meta.client._apply_update(
                item,
                UpdateExpression,
                ExpressionAttributeNames,
                ExpressionAttributeValues,
            )
            return {"Attributes": dict(item)}


def create_in_memory_store():
    lock = threading.RLock()
    tables = {}
    client = InMemoryDynamoClient(tables, lock)

    tables["EmergencyUsers"] = InMemoryTable("EmergencyUsers", "userId", client, lock)
    tables["EmergencyIncidents"] = InMemoryTable("EmergencyIncidents", "incidentId", client, lock)
    tables["EmergencyAmbulances"] = InMemoryTable("EmergencyAmbulances", "ambulanceId", client, lock)
    tables["EmergencyHospitals"] = InMemoryTable("EmergencyHospitals", "hospitalId", client, lock)

    return tables


def seed_demo_data():
    """Seed realistic local demo users and resources (in-memory only)."""
    user_service = handler.get_user_service()
    user_service.create_user(
        User(
            userId="USR-DISP-001",
            username="dispatcher1",
            role="DISPATCHER",
            passwordHash=User.hash_password("dispatcher123"),
        )
    )
    user_service.create_user(
        User(
            userId="USR-OPER-001",
            username="operator1",
            role="RESOURCE_OPERATOR",
            passwordHash=User.hash_password("operator123"),
        )
    )

    amb_service = handler.get_ambulance_service()
    for amb in [
        Ambulance("AMB-101", "MH12EM1001", 18.5204, 73.8567, "AVAILABLE", ["OXYGEN", "DEFIBRILLATOR", "TRAUMA_KIT"]),
        Ambulance("AMB-102", "MH12EM1002", 18.5314, 73.8446, "AVAILABLE", ["OXYGEN", "FIRST_AID", "STRETCHER"]),
        Ambulance("AMB-103", "MH12EM1003", 18.5074, 73.8077, "AVAILABLE", ["OXYGEN", "VENTILATOR", "DEFIBRILLATOR", "TRAUMA_KIT"]),
    ]:
        amb_service.create_ambulance(amb)

    hosp_service = handler.get_hospital_service()
    for hosp in [
        Hospital("HSP-201", "Pune Trauma & Emergency Center", 18.5240, 73.8520, 80, 14, ["EMERGENCY", "ICU", "TRAUMA_CENTER", "BLOOD_BANK"], "ACTIVE"),
        Hospital("HSP-202", "Sahyadri General Hospital", 18.5150, 73.8410, 120, 28, ["EMERGENCY", "ICU", "OPERATION_THEATRE"], "ACTIVE"),
        Hospital("HSP-203", "Deenanath Care Hospital", 18.5018, 73.8330, 150, 5, ["EMERGENCY", "VENTILATOR_SUPPORT", "ICU"], "ACTIVE"),
    ]:
        hosp_service.create_hospital(hosp)

    now = datetime.now(timezone.utc).isoformat()
    inc_service = handler.get_incident_service()
    inc_service.create_incident(
        Incident(
            incidentId="INC-DEMO-001",
            type="ROAD_ACCIDENT",
            description="Multi-vehicle collision near Shivajinagar junction; 2 injured.",
            latitude=18.5308,
            longitude=73.8475,
            severity="CRITICAL",
            peopleAffected=2,
            status="CREATED",
            createdAt=now,
            updatedAt=now,
            createdBy="USR-DISP-001",
            createdByUsername="dispatcher1",
            requiredResources=["AMBULANCE"],
            requiredEquipment=["OXYGEN", "TRAUMA_KIT"],
        )
    )


def install_in_memory_backend():
    tables = create_in_memory_store()
    dynamodb_config.get_table = lambda table_name: tables[table_name]
    return tables


class LambdaBridgeHandler(BaseHTTPRequestHandler):
    def _handle_request(self):
        parsed = urlparse(self.path)
        query_params = {
            k: v[0] if isinstance(v, list) and v else ""
            for k, v in parse_qs(parsed.query).items()
        }

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else None

        event = {
            "httpMethod": self.command,
            "path": parsed.path,
            "headers": {k: v for k, v in self.headers.items()},
            "queryStringParameters": query_params or None,
            "body": raw_body,
        }

        response = handler.lambda_handler(event, None)
        status_code = response.get("statusCode", 200)
        headers = response.get("headers") or {}
        body = response.get("body", "")

        self.send_response(status_code)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self._handle_request()

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def log_message(self, fmt, *args):
        print(f"[LOCAL-API] {self.address_string()} - {fmt % args}")


def main():
    install_in_memory_backend()
    seed_demo_data()

    host = os.environ.get("LOCAL_API_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCAL_API_PORT", "8000"))

    server = ThreadingHTTPServer((host, port), LambdaBridgeHandler)
    print("=" * 70)
    print("EMERGENCY RESPONSE PLATFORM — LOCAL SIMULATED API SERVER")
    print("=" * 70)
    print(f"Listening on: http://{host}:{port}")
    print("Persistence:  IN-MEMORY MOCK DynamoDB (NOT live AWS DynamoDB)")
    print(f"OTP Delivery: {os.environ.get('OTP_DELIVERY_MODE', 'gmail')} (LOCAL_OTP_CONSOLE={os.environ.get('LOCAL_OTP_CONSOLE', 'false')})")
    print("Demo logins:")
    print("  DISPATCHER        -> dispatcher1 / dispatcher123")
    print("  RESOURCE_OPERATOR -> operator1   / operator123")
    print("=" * 70)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down local API server...")
        server.server_close()


if __name__ == "__main__":
    main()
