#!/usr/bin/env python3
"""!@package OneClick_report Generate the final HTML test report.

Test Report is based on data json results.
"""
import json
import os
import sys
from jinja2 import Environment, FileSystemLoader

COMBINE_REPORT = False
RMD = False


def get_task_logs(log_path):
    """Get task log from .txt file."""
    logs = []
    with open(log_path, encoding="utf8") as file:
        for line in file:
            log = json.loads(line)
            log_message = log["log_message"]
            color = log["color"]
            logs.append(
                f"<span style='color: {color}; font-size:14px;"
                + f"'>{log_message}</span></br>"
            )

    return "".join(logs)


def get_one_click_data(data_path):
    """Get execution and results of One-Click test cases."""
    execution = {}
    data = {}
    for platform in data_path:
        json_file = data_path[platform][1]
        assert os.path.exists(json_file), "Could not find JSON file"
        with open(json_file, encoding="utf8") as f:
            all_data = json.load(f)
            execution[platform] = all_data["Execution"]
            data[platform] = all_data["Tests"]
    assert len(data) != 0, "No data to generate report"

    return execution, data


def get_data(data_path):
    """Get execution and results of Swilib or Autotestplus."""
    execution = {}
    data = {}
    for platform in data_path:
        json_file = data_path[platform][0]
        assert os.path.exists(json_file), "Could not find JSON file"
        with open(json_file, encoding="utf8") as f:
            all_data = json.load(f)
        execution[platform] = all_data["Execution"]
        data[platform] = all_data["Tests"]
    assert len(data) != 0, "No data to generate report"

    return execution, data


def get_summary(data):
    """Get data from job run with One-click server."""
    test_summary = data["Tests"]
    total_tcs_run = len(test_summary)
    total_passed = 0
    total_failed = 0
    total_noTC = 0
    total_norun = 0
    total_NA = 0
    divider = float(total_tcs_run) / 100
    for tc in test_summary:
        if tc["Result"] == "Passed":
            total_passed += 1
        elif tc["Result"] == "Failed":
            total_failed += 1
        elif tc["Result"] == "No Run":
            total_norun += 1
        elif tc["Result"] == "NoTC":
            total_noTC += 1
        elif tc["Result"] == "N/A":
            total_NA += 1
    summary = {
        "TestcasesRun": {"count": total_tcs_run, "percentage": total_tcs_run / divider},
        "Passed": {"count": total_passed, "percentage": total_passed / divider},
        "Failed": {"count": total_failed, "percentage": total_failed / divider},
        "NoTC": {"count": total_noTC, "percentage": total_noTC / divider},
        "N/A": {"count": total_NA, "percentage": total_NA / divider},
        "No Run": {"count": total_norun, "percentage": total_norun / divider},
    }

    return summary


def get_letp_data(platform, data_path):
    """Get data from job run with LeTP framework."""
    json_data = {}
    assert os.path.exists(data_path[platform][0]), "Could not find JSON file"

    with open(data_path[platform][0], encoding="utf8") as f:
        json_data = json.load(f)
    if len(json_data) == 0:
        print(f"========== LeTP data for {platform} NOT AVAILABLE ==========")
    else:
        for key in json_data["stats"]:
            if key != "global":
                return json_data["stats"][key]

    return json_data


def get_TPE_nightly_data(data_path):
    """Get the execution results of One-click and LeTP test cases."""
    letp_stats = {}
    swi_auto_stats = {}
    for platform in data_path:
        if "letp" in platform.lower():
            json_data = get_letp_data(platform, data_path)
            if len(json_data) != 0:
                letp_stats[platform] = json_data
        else:
            json_file = data_path[platform][0]
            assert os.path.exists(json_file), "Could not find JSON file"
            with open(json_file, encoding="utf8") as f:
                json_data = json.load(f)
                swi_auto_stats[platform] = get_summary(json_data)
    if len(letp_stats) == 0 and len(swi_auto_stats) == 0:
        print("No data to generate report")
        sys.exit(1)

    return letp_stats, swi_auto_stats


def generate_basic_report(
    env, data, execution, execution_info, testsystem, title, task_log
):
    """!Generate basic report in HTML to send by mail."""
    basic_template = env.get_template("oneclick_report_template.basic.html")
    html_basic_output = basic_template.render(
        data=data,
        execution=execution,
        execution_info=execution_info,
        testsystem=testsystem,
        title=title,
        task_log=task_log,
    )
    with open("test_report.basic.html", "w", encoding="utf8") as f:
        f.write(html_basic_output)
        print("Generating report in test_report.basic.html")
    if not os.path.exists("test_report.basic.html"):
        return False

    return True


def generate_swi_auto_report(title, execution, data, summary):
    """!Generate Swilib & AutotestPlus reports in HTML."""
    template_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    env = Environment(loader=FileSystemLoader(template_folder))
    template = env.get_template("TPE_report_template.html")
    html_output = template.render(
        data=data,
        execution=execution,
        summary_stats=summary,
        title=title,
        combine_report=COMBINE_REPORT,
    )

    with open("test_report.html", "w", encoding="utf8") as f:
        f.write(html_output)
        print("Generating report in test_report.html")

    if not os.path.exists("test_report.html"):
        return False

    return True


def generate_report(title, task_log, execution, data):
    """!Generate One-click report in HTML."""
    template_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    env = Environment(loader=FileSystemLoader(template_folder))
    template = env.get_template("oneclick_report_template.html")

    testsystem = {}
    for platform in data:
        testsystem[platform] = [data[platform][0]]
        for tc in data[platform]:
            if tc["Result"] != "No Run":
                testsystem[platform] = [tc]
                break
    execution_info = []
    for platform in execution:
        for info in execution[platform]:
            execution_info.append(info)
        break

    html_output = template.render(
        data=data,
        execution=execution,
        execution_info=execution_info,
        testsystem=testsystem,
        title=title,
        task_log=task_log,
        combine_report=COMBINE_REPORT,
    )

    with open("test_report.html", "w", encoding="utf8") as f:
        f.write(html_output)
        print("Generating report in test_report.html")

    if not os.path.exists("test_report.html") or not generate_basic_report(
        env, data, execution, execution_info, testsystem, title, task_log
    ):
        return False

    return True


def combine_reports(title, letp_data, swi_auto_data, artifact_path):
    """!Combine report in HTML."""
    template_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    env = Environment(loader=FileSystemLoader(template_folder))
    template = env.get_template("oneclick_report_template.html")
    if RMD:
        template = env.get_template("TPE_report_template.html")

    letp_headers = []
    swi_auto_headers = []
    for platform in swi_auto_data:
        for keys in swi_auto_data[platform]:
            swi_auto_headers.append(keys)
        break
    for platform in letp_data:
        for keys in letp_data[platform]:
            letp_headers.append(keys)
        break

    html_output = template.render(
        letp_data=letp_data,
        swi_auto_data=swi_auto_data,
        artifact_path=artifact_path,
        title=title,
        combine_report=COMBINE_REPORT,
        letp_headers=letp_headers,
        swi_auto_headers=swi_auto_headers,
    )

    with open("test_report.html", "w", encoding="utf8") as f:
        f.write(html_output)
        print("Generating report in test_report.html")
    with open("test_report.basic.html", "w", encoding="utf8") as f:
        f.write(html_output)
        print("Generating report in test_report.basic.html")
    if not os.path.exists("test_report.html") and not os.path.exists(
        "test_report.basic.html"
    ):
        return False

    return True


def run(title, data_path, artifact_path=None):
    """Entry point to generate report.

    Args:
        title (str): Report title.
        data_path: Results of test cases in JSON format. Defaults to "{}".
        artifact_path: Where to store artifacts.

    Returns:
        boolean:
            True: If report generated successfully.
            False: If report generated failed.
    """
    if RMD and artifact_path is None:
        summary_stats = {}
        execution, data = get_data(data_path)
        for platform in data_path:
            json_file = data_path[platform][0]
            assert os.path.exists(json_file), "Could not find JSON file"
            with open(json_file, encoding="utf8") as f:
                json_data = json.load(f)
            summary_stats[platform] = get_summary(json_data)
            summary_stats[platform].pop('NoTC')

        return generate_swi_auto_report(title, execution, data, summary_stats)

    if artifact_path is None:
        task_log = {}
        for platform in data_path:
            txt_file = data_path[platform][0]
            assert os.path.exists(txt_file), "Could not find '.txt' file"
            task_log[platform] = get_task_logs(txt_file)

        execution, data = get_one_click_data(data_path)

        return generate_report(title, task_log, execution, data)
    else:
        letp_data, swi_auto_data = get_TPE_nightly_data(data_path)

        return combine_reports(title, letp_data, swi_auto_data, artifact_path)


if __name__ == "__main__":
    data_path = json.loads(os.environ.get("JSON_DATA", {}))
    title = os.environ.get("TITLE")
    artifact_path = os.environ.get("ARTIFACT_PATH")

    assert len(data_path) != 0, "Could not find DATA path to generate report"

    if "TPE-Nightly" in title:
        COMBINE_REPORT = True
        artifact_path = artifact_path.replace(
            "/storage/artifacts", "https://get.central"
        )

    if "QA-TestEngine" in title or "Customize" in title:
        RMD = True

    if COMBINE_REPORT:
        ret = run(title, data_path, artifact_path)
    else:
        ret = run(title, data_path)
    sys.exit(0 if ret else 1)
