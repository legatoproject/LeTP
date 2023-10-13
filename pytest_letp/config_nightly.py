"""Script to configure parameters before running a campaign from qTest."""
import re
import os
import subprocess
from lib.pytest_qTest import QTestAPI


# ====================================================================================
# Global variables
# ====================================================================================
SERVER_URL = "https://sierrawireless.qtestnet.com/"
PROJECT_ID = "99501"  # Legato project
NIGHTLY_CYCLE = 4076133  # Test Cycle CL-103: Nightly-master


# ====================================================================================
# Functions
# ====================================================================================
def get_run_day(manifest):
    """Get date needs to run."""
    print(f"MANIFEST_PATH: {manifest}")
    pattern = r"(?P<day>\d{4}\.\d{2}\.\d{2})"
    run_day = re.search(pattern, manifest).group("day")
    return run_day


if __name__ == "__main__":
    access_token = os.getenv("ACCESS_TOKEN")
    pattern = r"(Bearer\s)?(?P<token>.*)"
    access_token = re.search(pattern, access_token).group("token")
    manifest = os.getenv("MANIFEST_PATH")
    run_day = get_run_day(manifest)
    path = "Legato/Nightly-master/{}/{}/{}"
    nightly = QTestAPI(access_token, PROJECT_ID)
    print(f"Get test cycle by day: {run_day}")
    json_cycle = nightly.get_cycles(NIGHTLY_CYCLE, "test-cycle")
    for test_cycle in json_cycle:
        if test_cycle["name"] == run_day:
            print(f"The test cycle - {run_day} has been initiated previously")
            break
    else:
        test_cycle_list = [test_cycle["name"] for test_cycle in json_cycle]
        oldest_test_cycle = sorted(test_cycle_list)[0]
        for test_cycle in json_cycle:
            if test_cycle["name"] == oldest_test_cycle:
                test_cycle_by_day = test_cycle["id"]
        data = {"name": run_day}
        nightly.update_cycle_name(test_cycle_by_day, data)

        print("Get list of test suites")
        json_cycle = nightly.get_cycles(test_cycle_by_day, "test-cycle")
        for target_cycle in json_cycle:
            target_data = nightly.get_suites(target_cycle["id"], "test-cycle")
            for test_suite in target_data:
                print("Reset test results of "
                      + path.format(run_day, target_cycle["name"], test_suite["name"]))
                os.environ["QTEST_CAMPAIGN"] = str(test_suite["id"])
                qtest_upload_path = os.path.join(
                    os.environ.get("LETP_PATH"),
                    "pytest_letp",
                    "tools",
                    "qTest_upload",
                    "qTest_upload.py")
                command = f"python3 {qtest_upload_path} --wipe=True"
                try:
                    subprocess.run(command, shell=True, check=True)
                except:
                    print(f"Error: {Exception}")
        print("The previous test results of the test cycle have been reset")
        # Clean the environment
        os.unsetenv("QTEST_CAMPAIGN")
