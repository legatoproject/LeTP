"""Script to configure parameters before running a campaign from qTest."""
import re
import os
import subprocess
import json
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
def get_test_number(nightly, test_num, test_suite, campaign_name):
    """Get the number of test cases to be run."""
    test_run_data = nightly.get_test_runs(test_suite["id"], "test-suite")
    test_num["system_test_num"] += int(test_run_data["total"])
    if test_suite["name"] == campaign_name:
        test_num["campaign_test_num"] = int(test_run_data["total"])


if __name__ == "__main__":
    access_token = os.getenv("ACCESS_TOKEN")
    pattern = r"(Bearer\s)?(?P<token>.*)"
    access_token = re.search(pattern, access_token).group("token")
    campaign_path = os.getenv("TEST_CHOICE")
    run_day, target_name, campaign_name = campaign_path.split("/")[-3:]
    test_num = {"system_test_num": 0, "campaign_test_num": 0}
    path = "Legato/Nightly-master/{}/{}/{}"
    nightly = QTestAPI(access_token, PROJECT_ID)
    print(f"Get test cycle by day: {run_day}")
    json_cycle = nightly.get_cycles(NIGHTLY_CYCLE, "test-cycle")
    for test_cycle in json_cycle:
        if test_cycle["name"] == run_day:
            print(f"The test cycle - {run_day} has been initiated previously")
            json_cycle = nightly.get_cycles(test_cycle["id"], "test-cycle")
            for target_cycle in json_cycle:
                if target_cycle["name"] == target_name:
                    target_data = nightly.get_suites(target_cycle["id"], "test-cycle")
                    for test_suite in target_data:
                        get_test_number(nightly, test_num, test_suite, campaign_name)
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
        exp_tests_for_targets = {}
        for target_cycle in json_cycle:
            test_number = 0
            target_data = nightly.get_suites(target_cycle["id"], "test-cycle")
            for test_suite in target_data:
                test_run_data = nightly.get_test_runs(test_suite["id"], "test-suite")
                test_number += int(test_run_data["total"])
                if target_cycle["name"] == target_name:
                    get_test_number(nightly, test_num, test_suite, campaign_name)
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
            exp_tests_for_targets[target_cycle["name"]] = test_number
        print("The previous test results of the test cycle have been reset")

        # The number of test cases of targets
        print(f"exp_tests_for_targets: {exp_tests_for_targets}")
        filename = "collected_total.json"
        path = os.path.join(
            os.environ.get("LETP_PATH"),
            "pytest_letp",
            "config",
            filename)
        with open(path, "w", encoding="utf8") as f:
            f.write(json.dumps(exp_tests_for_targets, indent=4, separators=(",", ": ")))
        print(f"File {path} was created!")
        # Clean the environment
        os.unsetenv("QTEST_CAMPAIGN")

    # The number of test cases the campaign is running
    print(f"collected_test: {test_num}")
    filename = "collected_test.json"
    path = os.path.join(
        os.environ.get("LETP_PATH"),
        "pytest_letp",
        "config",
        filename)
    with open(path, "w", encoding="utf8") as f:
        f.write(json.dumps(test_num, indent=4, separators=(",", ": ")))
    print(f"File {path} was created!")
