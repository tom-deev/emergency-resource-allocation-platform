import os
import subprocess
import sys


TEST_FILES = [
    "backend/src/validation/test_validation.py",
    "backend/src/utils/test_response.py",

    "backend/src/repositories/test_repository_create.py",
    "backend/src/repositories/test_repository_get_by_id.py",
    "backend/src/repositories/test_repository_get_all.py",
    "backend/src/repositories/test_repository_update.py",
    "backend/src/repositories/test_user_repository.py",
    "backend/src/repositories/test_incident_repository.py",
    "backend/src/repositories/test_incident_conditional_update.py",

    "backend/src/services/test_incident_service.py",
    "backend/src/services/test_incident_verification_service.py",
    "backend/src/services/test_ambulance_service.py",
    "backend/src/services/test_hospital_service.py",
    "backend/src/services/test_user_service.py",
    "backend/src/services/test_allocation_service.py",

    "backend/src/allocation/test_engine.py",

    "backend/src/test_handler.py",
    "backend/src/test_allocation_handler.py",
    "backend/src/test_auth_handler.py",
    "backend/src/test_workflow_and_auth.py",
    "backend/src/test_priority_queue.py",
    "backend/src/test_ambulance_dispatch.py",
    "backend/src/test_hospital_reservation.py",
    "backend/src/test_transport_completion_dashboard.py",
    "backend/src/test_ownership_and_privacy.py",
    "backend/src/test_operator_otp_auth.py",
    "backend/src/test_incident_archiving.py",
]


def main():
    project_root = os.getcwd()

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.path.join(
        project_root,
        "backend",
        "src",
    )

    for test_file in TEST_FILES:
        print()
        print("=" * 70)
        print(f"RUNNING: {test_file}")
        print("=" * 70)

        result = subprocess.run(
            [sys.executable, test_file],
            cwd=project_root,
            env=environment,
        )

        if result.returncode != 0:
            print()
            print(f"FAILED: {test_file}")
            sys.exit(result.returncode)

    print()
    print("=" * 70)
    print(f"ALL {len(TEST_FILES)} BACKEND TEST SUITES PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
