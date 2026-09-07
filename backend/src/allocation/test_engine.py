from allocation.engine import (
    calculate_distance_km,
    has_required_equipment,
    is_eligible_ambulance,
    find_eligible_ambulances,
    rank_ambulances,
    has_required_facilities,
    is_suitable_hospital,
    find_suitable_hospitals,
    rank_hospitals,
    select_allocation,
)

from models.incident import Incident
from models.ambulance import Ambulance
from models.hospital import Hospital


def test_distance():
    distance = calculate_distance_km(
        28.6139,
        77.2090,
        28.7041,
        77.1025,
    )

    assert distance > 0
    print("Distance calculation: PASSED")


def test_equipment_matching():
    assert has_required_equipment(
        ["OXYGEN", "DEFIBRILLATOR"],
        ["OXYGEN"],
    )

    assert not has_required_equipment(
        ["OXYGEN"],
        ["OXYGEN", "DEFIBRILLATOR"],
    )

    print("Equipment matching: PASSED")


def test_ambulance_eligibility():
    available_ambulance = Ambulance(
        "AMB001",
        "DL01AB1234",
        28.60,
        77.20,
        "AVAILABLE",
        ["OXYGEN", "DEFIBRILLATOR"],
        None,
    )

    busy_ambulance = Ambulance(
        "AMB002",
        "DL01AB5678",
        28.61,
        77.21,
        "BUSY",
        ["OXYGEN", "DEFIBRILLATOR"],
        None,
    )

    assert is_eligible_ambulance(
        available_ambulance,
        ["OXYGEN"],
    )

    assert not is_eligible_ambulance(
        busy_ambulance,
        ["OXYGEN"],
    )

    print("Ambulance eligibility: PASSED")


def test_find_eligible_ambulances():
    incident = Incident(
        "INC001",
        "ACCIDENT",
        "Road accident",
        28.6139,
        77.2090,
        "HIGH",
        3,
        "CREATED",
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
        [],
        ["OXYGEN"],
        None,
        None,
    )

    ambulance1 = Ambulance(
        "AMB001",
        "DL01AB1234",
        28.6140,
        77.2091,
        "AVAILABLE",
        ["OXYGEN", "DEFIBRILLATOR"],
        None,
    )

    ambulance2 = Ambulance(
        "AMB002",
        "DL01AB5678",
        28.7000,
        77.1000,
        "BUSY",
        ["OXYGEN", "DEFIBRILLATOR"],
        None,
    )

    ambulance3 = Ambulance(
        "AMB003",
        "DL01AB9999",
        28.6150,
        77.2100,
        "AVAILABLE",
        ["OXYGEN"],
        None,
    )

    eligible = find_eligible_ambulances(
        incident,
        [ambulance1, ambulance2, ambulance3],
    )

    assert len(eligible) == 2

    ambulance_ids = [
        item["ambulance"].ambulanceId
        for item in eligible
    ]

    assert "AMB001" in ambulance_ids
    assert "AMB003" in ambulance_ids
    assert "AMB002" not in ambulance_ids

    ranked = rank_ambulances(eligible)

    assert ranked[0]["distanceKm"] <= ranked[1]["distanceKm"]

    print("Ambulance filtering and ranking: PASSED")


def test_hospital_facilities():
    assert has_required_facilities(
        ["ICU", "TRAUMA", "CARDIAC"],
        ["ICU", "TRAUMA"],
    )

    assert not has_required_facilities(
        ["ICU"],
        ["ICU", "TRAUMA"],
    )

    print("Hospital facility matching: PASSED")


def test_hospital_suitability():
    suitable_hospital = Hospital(
        "HOS001",
        "City General Hospital",
        28.6140,
        77.2091,
        100,
        20,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    full_hospital = Hospital(
        "HOS002",
        "Full Hospital",
        28.6150,
        77.2100,
        100,
        0,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    inactive_hospital = Hospital(
        "HOS003",
        "Inactive Hospital",
        28.6160,
        77.2110,
        100,
        20,
        ["ICU", "TRAUMA"],
        "INACTIVE",
    )

    missing_facility_hospital = Hospital(
        "HOS004",
        "Basic Hospital",
        28.6170,
        77.2120,
        100,
        20,
        ["GENERAL"],
        "ACTIVE",
    )

    assert is_suitable_hospital(
        suitable_hospital,
        ["ICU", "TRAUMA"],
    )

    assert not is_suitable_hospital(
        full_hospital,
        ["ICU"],
    )

    assert not is_suitable_hospital(
        inactive_hospital,
        ["ICU"],
    )

    assert not is_suitable_hospital(
        missing_facility_hospital,
        ["ICU"],
    )

    print("Hospital suitability: PASSED")


def test_find_suitable_hospitals():
    incident = Incident(
        "INC002",
        "ACCIDENT",
        "Major road accident",
        28.6139,
        77.2090,
        "CRITICAL",
        4,
        "CREATED",
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
        [],
        [],
        None,
        None,
    )

    hospital1 = Hospital(
        "HOS001",
        "Nearest Trauma Hospital",
        28.6140,
        77.2091,
        100,
        20,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    hospital2 = Hospital(
        "HOS002",
        "Full Hospital",
        28.6150,
        77.2100,
        100,
        0,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    hospital3 = Hospital(
        "HOS003",
        "Far Trauma Hospital",
        28.7000,
        77.1000,
        100,
        30,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    suitable = find_suitable_hospitals(
        incident,
        [hospital1, hospital2, hospital3],
        ["ICU", "TRAUMA"],
    )

    assert len(suitable) == 2

    hospital_ids = [
        item["hospital"].hospitalId
        for item in suitable
    ]

    assert "HOS001" in hospital_ids
    assert "HOS003" in hospital_ids
    assert "HOS002" not in hospital_ids

    ranked = rank_hospitals(suitable)

    assert ranked[0]["hospital"].hospitalId == "HOS001"
    assert ranked[0]["distanceKm"] <= ranked[1]["distanceKm"]

    print("Hospital filtering and ranking: PASSED")


def test_select_allocation():
    incident = Incident(
        "INC003",
        "ACCIDENT",
        "Critical road accident",
        28.6139,
        77.2090,
        "CRITICAL",
        2,
        "CREATED",
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
        [],
        ["OXYGEN"],
        None,
        None,
    )

    nearest_ambulance = Ambulance(
        "AMB001",
        "DL01AB1111",
        28.6140,
        77.2091,
        "AVAILABLE",
        ["OXYGEN"],
        None,
    )

    farther_ambulance = Ambulance(
        "AMB002",
        "DL01AB2222",
        28.7000,
        77.1000,
        "AVAILABLE",
        ["OXYGEN"],
        None,
    )

    unsuitable_hospital = Hospital(
        "HOS001",
        "Full Hospital",
        28.6140,
        77.2091,
        100,
        0,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    nearest_hospital = Hospital(
        "HOS002",
        "Nearest Suitable Hospital",
        28.6150,
        77.2100,
        100,
        25,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    farther_hospital = Hospital(
        "HOS003",
        "Far Suitable Hospital",
        100,
        100,
        100,
        30,
        ["ICU", "TRAUMA"],
        "ACTIVE",
    )

    allocation = select_allocation(
        incident,
        [nearest_ambulance, farther_ambulance],
        [
            unsuitable_hospital,
            nearest_hospital,
            farther_hospital,
        ],
        ["ICU", "TRAUMA"],
    )

    assert allocation is not None

    assert allocation["incidentId"] == "INC003"
    assert allocation["ambulanceId"] == "AMB001"
    assert allocation["hospitalId"] == "HOS002"

    assert allocation["ambulanceDistanceKm"] >= 0
    assert allocation["hospitalDistanceKm"] >= 0

    print("End-to-end allocation selection: PASSED")


def test_allocation_failure():
    incident = Incident(
        "INC004",
        "FIRE",
        "Emergency with no resources",
        28.6139,
        77.2090,
        "HIGH",
        1,
        "CREATED",
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
        [],
        ["OXYGEN"],
        None,
        None,
    )

    unavailable_ambulance = Ambulance(
        "AMB004",
        "DL01AB4444",
        28.6140,
        77.2091,
        "BUSY",
        ["OXYGEN"],
        None,
    )

    hospital = Hospital(
        "HOS004",
        "Available Hospital",
        28.6140,
        77.2091,
        100,
        20,
        ["ICU"],
        "ACTIVE",
    )

    allocation = select_allocation(
        incident,
        [unavailable_ambulance],
        [hospital],
        ["ICU"],
    )

    assert allocation is None

    print("Allocation failure handling: PASSED")


if __name__ == "__main__":
    test_distance()
    test_equipment_matching()
    test_ambulance_eligibility()
    test_find_eligible_ambulances()
    test_hospital_facilities()
    test_hospital_suitability()
    test_find_suitable_hospitals()
    test_select_allocation()
    test_allocation_failure()

    print("ALL ALLOCATION ENGINE TESTS PASSED")
