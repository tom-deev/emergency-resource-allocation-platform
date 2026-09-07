from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Incident:
    """
    Represents an emergency incident in the application.
    """

    incidentId: str
    type: str
    description: str
    latitude: float
    longitude: float
    severity: str
    peopleAffected: int
    status: str
    createdAt: str
    updatedAt: str
    requiredResources: list[str] = field(default_factory=list)
    requiredEquipment: list[str] = field(default_factory=list)
    assignedAmbulanceId: Optional[str] = None
    assignedHospitalId: Optional[str] = None