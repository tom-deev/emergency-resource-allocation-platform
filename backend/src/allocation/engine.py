from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS_KM = 6371.0


def calculate_distance_km(
    latitude1,
    longitude1,
    latitude2,
    longitude2,
):
    """
    Calculate the approximate distance between two coordinates
    using the Haversine formula.
    """

    lat1 = radians(latitude1)
    lon1 = radians(longitude1)
    lat2 = radians(latitude2)
    lon2 = radians(longitude2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def has_required_equipment(
    ambulance_equipment,
    required_equipment,
):
    """
    Return True when the ambulance contains every piece
    of equipment required by the incident.
    """

    available_equipment = set(ambulance_equipment or [])
    required_equipment = set(required_equipment or [])

    return required_equipment.issubset(available_equipment)


def is_eligible_ambulance(
    ambulance,
    required_equipment,
):
    """
    Determine whether an ambulance is eligible for allocation.
    """

    if ambulance.status != "AVAILABLE":
        return False

    return has_required_equipment(
        ambulance.equipment,
        required_equipment,
    )


def find_eligible_ambulances(
    incident,
    ambulances,
):
    """
    Return available and equipment-compatible ambulances.

    Each result contains the ambulance and its approximate
    distance from the incident.
    """

    eligible = []

    for ambulance in ambulances:
        if not is_eligible_ambulance(
            ambulance,
            incident.requiredEquipment,
        ):
            continue

        distance = calculate_distance_km(
            incident.latitude,
            incident.longitude,
            ambulance.latitude,
            ambulance.longitude,
        )

        eligible.append(
            {
                "ambulance": ambulance,
                "distanceKm": distance,
            }
        )

    return eligible


def rank_ambulances(eligible_ambulances):
    """
    Rank eligible ambulances from closest to farthest.
    """

    return sorted(
        eligible_ambulances,
        key=lambda item: item["distanceKm"],
    )


def has_required_facilities(
    hospital_facilities,
    required_facilities,
):
    """
    Return True when the hospital contains every facility
    required by the allocation request.
    """

    available_facilities = set(hospital_facilities or [])
    required_facilities = set(required_facilities or [])

    return required_facilities.issubset(available_facilities)


def is_suitable_hospital(
    hospital,
    required_facilities,
):
    """
    Determine whether a hospital is suitable for allocation.
    """

    if hospital.status != "ACTIVE":
        return False

    if hospital.availableBeds <= 0:
        return False

    return has_required_facilities(
        hospital.facilities,
        required_facilities,
    )


def find_suitable_hospitals(
    incident,
    hospitals,
    required_facilities,
):
    """
    Return active hospitals with available beds and
    the required facilities.

    Each result contains the hospital and its approximate
    distance from the incident.
    """

    suitable = []

    for hospital in hospitals:
        if not is_suitable_hospital(
            hospital,
            required_facilities,
        ):
            continue

        distance = calculate_distance_km(
            incident.latitude,
            incident.longitude,
            hospital.latitude,
            hospital.longitude,
        )

        suitable.append(
            {
                "hospital": hospital,
                "distanceKm": distance,
            }
        )

    return suitable


def rank_hospitals(suitable_hospitals):
    """
    Rank suitable hospitals from closest to farthest.
    """

    return sorted(
        suitable_hospitals,
        key=lambda item: item["distanceKm"],
    )


def select_allocation(
    incident,
    ambulances,
    hospitals,
    required_hospital_facilities,
):
    """
    Select the best currently eligible ambulance and
    suitable hospital for an incident.

    The current selection strategy is intentionally simple
    and explainable: choose the closest eligible ambulance
    and closest suitable hospital.

    Return None when no valid ambulance or hospital exists.
    """

    eligible_ambulances = find_eligible_ambulances(
        incident,
        ambulances,
    )

    ranked_ambulances = rank_ambulances(
        eligible_ambulances,
    )

    if not ranked_ambulances:
        return None

    suitable_hospitals = find_suitable_hospitals(
        incident,
        hospitals,
        required_hospital_facilities,
    )

    ranked_hospitals = rank_hospitals(
        suitable_hospitals,
    )

    if not ranked_hospitals:
        return None

    selected_ambulance = ranked_ambulances[0]
    selected_hospital = ranked_hospitals[0]

    return {
        "incidentId": incident.incidentId,
        "ambulanceId": selected_ambulance["ambulance"].ambulanceId,
        "hospitalId": selected_hospital["hospital"].hospitalId,
        "ambulanceDistanceKm": selected_ambulance["distanceKm"],
        "hospitalDistanceKm": selected_hospital["distanceKm"],
    }
