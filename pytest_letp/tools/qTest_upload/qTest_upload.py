"""Script upload test results to qTest."""

import sys
import os
import json
import getopt
import re
from qTest_lib import QTestAPI, write_config


# ====================================================================================
# Global variables
# ====================================================================================
PROJECT_NAME = "Legato"
ACCESS_TOKEN = ""
JSON_PATH = ""
HTML_PATH = ""
QTEST_INFO = ""
PROJECT_ID = 0
RELEASE_NAME = ""
TEST_SUITE_NAME = ""
RELEASE_ID = 0


# ====================================================================================
# Functions
# ====================================================================================
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
        Requirement data to upload qTest.
    """
    with open(JSON_PATH, encoding="utf8") as f:
        json_data = json.load(f)
    Config_module = list(json_data["env"]["per_env"].keys())[0]
    Jenkins_job_info = json_data["env"]["per_env"][Config_module]
    print("============================> Below fields will be uploaded to qTest.")
    TestbedID = Jenkins_job_info["tb.id"]
    print(f"TestbedID: {TestbedID}")
    TBmodule = Jenkins_job_info["tb.module"]
    print(f"TBmodule: {TBmodule}")
    TBimei = Jenkins_job_info["tb.imei"]
    print(f"TBimei: {TBimei}")
    TBiccid = Jenkins_job_info["tb.iccid"]
    print(f"TBiccid: {TBiccid}")
    Build_number = Jenkins_job_info["job.url"]
    print(f"Comments: {Build_number}")
    Legato_version = Jenkins_job_info["legato"].split("_")[0].split(" ")[0]
    print(f"Legato_version: {Legato_version}")
    FW_Version = Jenkins_job_info["modem"].split(" ")[0]
    if "HL78" in TBmodule:
        FW_Version = FW_Version.split(".RK")[0]
    print(f"FW_Version: {FW_Version}")
    Yocto_version = ""
    if "WP" in TBmodule:
        Yocto_version = Jenkins_job_info["linux"].split(" ")[0]
        print(f"Yocto_version: {Yocto_version}")
    print("<====================================================================")
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


def pre_upload(test_run_id, versions):
    """Pre-upload test result."""
    property_info = REST_api.get_properties_info(test_run_id)
    print("==== Check the validity of Legato, FW, Yocto version =====")
    print(versions)
    for version in versions:
        if version in str(property_info):
            print(f"{version} had been added to qTest")
        else:
            print(f"ERROR: {version} had not been added to qTest")
            assert False
    REST_api.fill_field_ID(property_info, test_run_id)


def check_duplicate(release_data, test_case_name):
    """Check the duplicate of testcases.

    Returns:
        True if test cases is duplicated.
        False if test cases isn't duplicated.
    """
    k = 0
    for test_cases in release_data.values():
        if test_case_name in test_cases:
            k += 1
    if k == 1:
        return True
    return False


def upload_qtest(release_data, test_case_name):
    """Upload test result to qTest.

    Returns:
        True if upload successfully.
        False if upload failed.
    """
    for test_cases in release_data.values():
        if test_case_name in test_cases:
            is_upload_success = REST_api.post_result_qtest(test_cases[test_case_name])
    return is_upload_success


# ====================================================================================
# Main
# ====================================================================================
print("=====================================START===================================")
JSON_PATH, HTML_PATH = get_param()
print(f"Json path: {JSON_PATH}")
print(f"HTML path: {HTML_PATH}")
QTEST_INFO = os.getenv("QTEST_INFO")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
RELEASE_NAME = QTEST_INFO
if ";" in QTEST_INFO:
    pattern = r"(?P<release>.*)?;\s?(?P<test_suit>.*)"
    RELEASE_NAME = re.search(pattern, QTEST_INFO).group("release")
    TEST_SUITE_NAME = re.search(pattern, QTEST_INFO).group("test_suit")
print(f"RELEASE_NAME: {RELEASE_NAME}")
print(f"TEST_SUITE_NAME: {TEST_SUITE_NAME}")

pattern = r"(Bearer\s)?(?P<token>.*)"
ACCESS_TOKEN = re.search(pattern, ACCESS_TOKEN).group("token")
print(f"ACCESS_TOKEN: {ACCESS_TOKEN}")

REST_api = QTestAPI(ACCESS_TOKEN, PROJECT_NAME, RELEASE_NAME)

# Load data from html file
with open(HTML_PATH, "r", encoding="utf8") as f:
    html_data = f.read()
html_data1 = html_data.split("L_ReinitTest", 1)[1]
html_data2 = html_data1.split("<tr>", 1)[1]
pattern_name = r"scope.*\.(L[_E].*_\d+)"
pattern_status = r"td class=\"(\w+)"
list_test_cases_run = re.findall(pattern_name, html_data2)
list_status = re.findall(pattern_status, html_data2)
dict_test_cases = {}
number_testcases = len(list_test_cases_run)
for i in range(number_testcases):
    dict_test_cases[list_test_cases_run[i]] = list_status[i]

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
versions = [Legato_version, FW_Version]
if "HL78" in TBmodule:
    write_config("FW_Version_HL78/value", FW_Version)
elif "RC76" in TBmodule:
    write_config("FW_Version_RC76/value", FW_Version)
elif "WP76" in TBmodule or "WP77" in TBmodule:
    versions.append(Yocto_version)
    write_config("LXSWI_Version/value", Yocto_version)
    if "WP76" in TBmodule:
        write_config("FW_Version_WP76/value", FW_Version)
    else:
        write_config("FW_Version_WP77/value", FW_Version)

dict_test_suites = {}
release_data = {}
if TEST_SUITE_NAME != "":
    print(f"Upload test result for test suite: {TEST_SUITE_NAME}")
    TEST_SUITE_ID = REST_api.get_testSuite_ID(TEST_SUITE_NAME)
    list_test_cases = REST_api.get_testRun_ID(TEST_SUITE_ID)
    release_data[TEST_SUITE_NAME] = list_test_cases
    SAMPLE_TEST_CASE_ID = list(list_test_cases.values())[0]
else:
    print(f"List of test suite on release {RELEASE_NAME}: {REST_api.test_suite_names}")
    for test_suite_name in REST_api.test_suite_names:
        print(f"test_suite_name: {test_suite_name}")
        TEST_SUITE_ID = REST_api.get_testSuite_ID(test_suite_name)
        list_test_cases = REST_api.get_testRun_ID(TEST_SUITE_ID)
        release_data[test_suite_name] = list_test_cases
        SAMPLE_TEST_CASE_ID = list(list_test_cases.values())[0]
pre_upload(SAMPLE_TEST_CASE_ID, versions)
Uploaded_test_cases = []
Need_to_investigate_test_cases = []
Remaining_test_cases = []
print(f"===> Uploading test result for {len(list_test_cases_run)} test cases .... ")
for test_case_name in list_test_cases_run:
    if dict_test_cases[test_case_name] == "passed":
        # Check if test case is duplicated
        up_qtest = check_duplicate(release_data, test_case_name)
        upload_result = False
        if up_qtest:
            # Upload test result to qTest
            upload_result = upload_qtest(release_data, test_case_name)
        # Add test case to list of uploaded test cases
        if upload_result:
            Uploaded_test_cases.append(test_case_name)
        else:
            # Add test case to list duplicated
            Remaining_test_cases.append(test_case_name)
    else:
        # Add test case to list of test cases failed or error or skipped
        Need_to_investigate_test_cases.append(test_case_name)
print(f"===> List of {len(Uploaded_test_cases)} test cases are uploaded successfully")
for i in Uploaded_test_cases:
    print(i)
print(
    f"===> List of {len(Remaining_test_cases)} test cases "
    + "are duplicated or not exist on this release"
)
for i in Remaining_test_cases:
    print(i)
print(
    f"===> List of {len(Need_to_investigate_test_cases)} test cases "
    + "failed or error or skipped"
)
for i in Need_to_investigate_test_cases:
    print(i)
print("======================================END====================================")
