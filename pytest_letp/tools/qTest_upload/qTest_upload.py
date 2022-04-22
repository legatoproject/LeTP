"""Script upload test results to qTest."""

import sys
import os
import json
import getopt
import re
from qTest_lib import write_config, QTestAPI, StatusID


SERVER_URL = "https://sierrawireless.qtestnet.com"
PROJECT = "Legato"
ACCESS_TOKEN = ""
JSON_PATH = ""
HTML_PATH = ""
QTEST_INFO = ""
TEST_SUITE_ID = 0
STATUS_ID = 0


def get_param():
    """Get option from user.

    Returns:
        json path for get data.
        html path for get data.
    """
    assert len(sys.argv) == 5, "Incorrect parameter"
    try:
        opts = getopt.getopt(sys.argv[1:], "", ["json=", "html="])[0]
    except getopt.GetoptError:
        print("python3 qTest_upload.py --json <json path> --html <html path>")
    for opt, arg in opts:
        if opt == "--json":
            JSON_PATH = arg
        elif opt == "--html":
            HTML_PATH = arg
        else:
            assert False, "Unhandled option"
    return JSON_PATH, HTML_PATH


def get_data_from_json():
    """Get data from json file.

    Returns:
        Requirement data to upload qTest
    """
    with open(JSON_PATH, encoding="utf8") as f:
        json_data = json.load(f)
    Config_module = list(json_data["env"]["per_env"].keys())[0]
    Jenkins_job_info = json_data["env"]["per_env"][Config_module]
    TestbedID = Jenkins_job_info["tb.id"]
    print(TestbedID)
    TBmodule = Jenkins_job_info["tb.module"]
    print(TBmodule)
    TBimei = Jenkins_job_info["tb.imei"]
    print(TBimei)
    TBiccid = Jenkins_job_info["tb.iccid"]
    print(TBiccid)
    Legato_version = Jenkins_job_info["legato"].split(" ")[0]
    print(Legato_version)
    FW_Version = Jenkins_job_info["modem"].split(" ")[0]
    if "HL78" in TBmodule:
        FW_Version = FW_Version.split(".RK")[0]
    print(FW_Version)
    Yocto_version = ""
    Build_number = Jenkins_job_info["job.url"]
    print(Build_number)
    if "WP" in TBmodule:
        Yocto_version = Jenkins_job_info["linux"].split(" ")[0]
        print(Yocto_version)
    return (
        TestbedID,
        TBmodule,
        TBimei,
        TBiccid,
        Legato_version,
        FW_Version,
        Yocto_version,
        Build_number,
    )


print("=======================================START===================================")
JSON_PATH, HTML_PATH = get_param()
print(f"Json path: {JSON_PATH}")
print(f"HTML path: {HTML_PATH}")
QTEST_INFO = os.getenv("QTEST_INFO")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
pattern = r"(?P<release>.*)?;\s?(?P<test_suit>.*)"
release_name = re.search(pattern, QTEST_INFO).group("release")
test_suite_name = re.search(pattern, QTEST_INFO).group("test_suit")
print(f"release_name: {release_name}")
print(f"test_suite_name: {test_suite_name}")
pattern = r"(Bearer\s)?(?P<token>.*)"
ACCESS_TOKEN = re.search(pattern, ACCESS_TOKEN).group("token")
print(f"Access token: {ACCESS_TOKEN}")

# Load data from html file
with open(HTML_PATH, "r", encoding="utf8") as f:
    html_data = f.read()
html_data1 = html_data.split("L_ReinitTest", 1)[1]
html_data2 = html_data1.split("<tr>", 1)[1]
pattern_name = r"scope.*\.(L[_E].*_\d+)"
pattern_status = r"td class=\"(\w+)"
list_test_cases = re.findall(pattern_name, html_data2)
list_status = re.findall(pattern_status, html_data2)
list_test_results = {}
number_testcases = len(list_test_cases)
for i in range(number_testcases):
    list_test_results[list_test_cases[i]] = list_status[i]

# Get information of jenkins job
(
    TestbedID,
    TBmodule,
    TBimei,
    TBiccid,
    Legato_version,
    FW_Version,
    Yocto_version,
    Build_number,
) = get_data_from_json()

# Write data to test_data.xml file
write_config("Module_Ref/value_id", TestbedID)
write_config("Legato_Version/value", Legato_version)
write_config("Comment/value", Build_number)
if "HL78" in TBmodule:
    write_config("FW_Version_HL78/value", FW_Version)
elif "RC76" in TBmodule:
    write_config("FW_Version_RC76/value", FW_Version)
elif "WP76" in TBmodule or "WP77" in TBmodule:
    write_config("LXSWI_Version/value", Yocto_version)
    if "WP76" in TBmodule:
        write_config("FW_Version_WP76/value", FW_Version)
    else:
        write_config("FW_Version_WP77/value", FW_Version)


REST_api = QTestAPI(ACCESS_TOKEN)
# Get project ID
project_id = REST_api.get_project_ID(PROJECT)
# Get release ID
release_id = REST_api.get_release_ID(release_name, project_id)
# Get testsuit ID
TEST_SUITE_ID = REST_api.get_testSuite_ID(test_suite_name, project_id, release_id)

Remaining_test_cases = ""
for test_case_name, test_status in list_test_results.items():
    if test_status == "passed":
        STATUS_ID = StatusID.Passed
        print(f"=== Uploading test result for {test_case_name}")
        Upload_result, test_run_id = REST_api.get_properties_info(
            project_id, TEST_SUITE_ID, test_case_name
        )
        if Upload_result != 1:
            REST_api.post_result_qtest(project_id, Upload_result, test_run_id)
            print(f"=== Upload test result for {test_case_name} successfully")
        else:
            Remaining_test_cases += test_case_name + "\n"
            print(f"=== Cannot upload test result for {test_case_name}")
print("=====List of remaining test cases=====")
print(Remaining_test_cases)
print("========================================END====================================")
