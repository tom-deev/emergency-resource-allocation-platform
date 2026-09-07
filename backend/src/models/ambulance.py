from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Ambulance:
    """
    Represents an ambulance resource in the application.
    """

    ambulanceId: str
    registrationNumber: str
    latitude: float
    longitude: float
    status: str
    equipment: list[str] = field(default_factory=list)
    assignedIncidentId: Optional[str] = None