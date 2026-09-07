import sys

sys.path.insert(0, r"backend\src")

from models.incident import Incident
from repositories.incident_repository import IncidentRepository


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


table = FakeTable()
repository = IncidentRepository(table)

incident = Incident(
    "inc_test",
    "FIRE",
    "Test incident",
    18.5204,
    73.8567,
    "HIGH",
    10,
    "CREATED",
    "2026-09-07T12:00:00Z",
    "2026-09-07T12:00:00Z",
    ["AMBULANCE"],
    ["OXYGEN"],
)

result = repository.create(incident)

assert result["incidentId"] == "inc_test"
assert result["type"] == "FIRE"
assert result["severity"] == "HIGH"
assert len(table.items) == 1
assert table.items[0]["incidentId"] == "inc_test"

print("Stored incident ID:", result["incidentId"])
print("Fake table item count:", len(table.items))
print("INCIDENT CREATE PERSISTENCE VERIFIED")
