from dataclasses import dataclass, field
from typing import Optional

from constants import derive_priority


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

    priority: Optional[str] = None
    createdBy: Optional[str] = None
    createdByUsername: Optional[str] = None

    requiredResources: list[str] = field(default_factory=list)
    requiredEquipment: list[str] = field(default_factory=list)

    assignedAmbulanceId: Optional[str] = None
    assignedHospitalId: Optional[str] = None

    hospitalRequestStatus: str = "NOT_REQUESTED"
    hospitalRequestedAt: Optional[str] = None
    hospitalAcceptedAt: Optional[str] = None
    hospitalDecisionAt: Optional[str] = None
    hospitalRejectionReason: Optional[str] = None

    reviewedBy: Optional[str] = None
    reviewedAt: Optional[str] = None
    verifiedAt: Optional[str] = None
    verificationRemarks: Optional[str] = None

    ambulanceAssignedAt: Optional[str] = None
    transportedAt: Optional[str] = None
    completedAt: Optional[str] = None

    bedReservation: Optional[dict] = None
    reservationHistory: list[dict] = field(default_factory=list)

    isArchived: bool = False
    archivedAt: Optional[str] = None
    archivedBy: Optional[str] = None

    def __post_init__(self):
        self.priority = derive_priority(self.severity)
