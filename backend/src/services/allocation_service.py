from types import SimpleNamespace

from allocation.engine import select_allocation
from constants import INCIDENT_STATUSES, AMBULANCE_STATUSES


class AllocationService:
    def __init__(
        self,
        incident_repository,
        ambulance_repository,
        hospital_repository,
    ):
        self.incident_repository = incident_repository
        self.ambulance_repository = ambulance_repository
        self.hospital_repository = hospital_repository

    @staticmethod
    def _to_object(data):
        """
        Convert repository dictionaries into objects that the
        allocation engine can read using attribute notation.
        """

        if isinstance(data, dict):
            return SimpleNamespace(**data)

        return data

    def allocate_incident(
        self,
        incident_id,
        required_hospital_facilities,
    ):
        """
        Allocate the best eligible ambulance and suitable hospital
        for an incident, then persist the allocation.
        """

        incident = self.incident_repository.get_by_id(incident_id)

        if incident is None:
            raise ValueError("Incident not found.")

        incident = self._to_object(incident)

        if incident.status == "RESOLVED":
            raise ValueError("Cannot allocate a resolved incident.")

        ambulances = self.ambulance_repository.get_all()
        hospitals = self.hospital_repository.get_all()

        ambulances = [
            self._to_object(ambulance)
            for ambulance in ambulances
        ]

        hospitals = [
            self._to_object(hospital)
            for hospital in hospitals
        ]

        allocation = select_allocation(
            incident,
            ambulances,
            hospitals,
            required_hospital_facilities,
        )

        if allocation is None:
            raise ValueError(
                "No suitable ambulance and hospital are available."
            )

        ambulance_id = allocation["ambulanceId"]
        hospital_id = allocation["hospitalId"]

        hospital = next(
            (
                hospital
                for hospital in hospitals
                if hospital.hospitalId == hospital_id
            ),
            None,
        )

        if hospital is None:
            raise ValueError("Selected hospital not found.")

        if hospital.availableBeds <= 0:
            raise ValueError("Selected hospital has no available beds.")

        self.ambulance_repository.update(
            ambulance_id,
            {
                "status": "BUSY",
                "assignedIncidentId": incident_id,
            },
        )

        self.hospital_repository.update(
            hospital_id,
            {
                "availableBeds": hospital.availableBeds - 1,
            },
        )

        updated_incident = self.incident_repository.update(
            incident_id,
            {
                "status": "ALLOCATED",
                "assignedAmbulanceId": ambulance_id,
                "assignedHospitalId": hospital_id,
            },
        )

        return {
            "incident": updated_incident,
            "allocation": allocation,
        }
