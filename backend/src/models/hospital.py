from dataclasses import dataclass, field


@dataclass
class Hospital:
    """
    Represents a hospital resource in the application.
    """

    hospitalId: str
    name: str
    latitude: float
    longitude: float
    totalBeds: int
    availableBeds: int
    facilities: list[str] = field(default_factory=list)
    status: str = "ACTIVE"