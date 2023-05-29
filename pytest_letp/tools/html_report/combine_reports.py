#!/usr/bin/env python3
"""!@package OneClick_report Generate the final HTML test report.

Test Report is based on data json results.
"""
import json
import os
import sys
from jinja2 import Environment, FileSystemLoader


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


def get_data(data_path):
    """Get execution and results of One-Click test cases."""
    execution = {}
    data = {}
    for platform in data_path:
        json_file = ""
        for file in data_path[platform]:
            if ".json" in file:
                json_file = file
        if os.path.exists(json_file):
            with open(json_file, encoding="utf8") as f:
                all_data = json.load(f)
                execution[platform] = all_data["Execution"]
                data[platform] = all_data["Tests"]
    assert len(data) != 0, "No data to generate report"

    return execution, data


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


def generate_report(title, task_log, execution, data):
    """!Generate report in HTML."""
    template_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    env = Environment(loader=FileSystemLoader(template_folder))
    template = env.get_template("oneclick_report_template.html")

    testsystem = {}
    for platform in data:
        testsystem[platform] = data[platform][0]
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
    )

    with open("test_report.html", "w", encoding="utf8") as f:
        f.write(html_output)
        print("Generating report in test_report.html")

    if not os.path.exists("test_report.html") or not generate_basic_report(
        env, data, execution, execution_info, testsystem, title, task_log
    ):
        return False

    return True


def run(title, data_path):
    """Entry point to generate report.

    Args:
        title (str): Report title.
        data_path: Results of test cases in JSON format. Defaults to "{}".

    Returns:
        boolean:
            True: If report generated successfully.
            False: If report generated failed.
    """
    data_path = json.loads(data_path)
    if len(data_path) == 0:
        print("Could not find DATA path to generate report")
        sys.exit(1)
    task_log = {}
    execution = {}
    for platform in data_path:
        txt_file = ""
        for file in data_path[platform]:
            if ".txt" in file:
                txt_file = file
        if os.path.exists(txt_file):
            task_log[platform] = get_task_logs(txt_file)

    execution, data = get_data(data_path)

    if not generate_report(title, task_log, execution, data):
        return False

    return True


if __name__ == "__main__":
    ret = run(os.environ.get("TITLE"), os.environ.get("JSON_DATA", {}))
    sys.exit(0 if ret else 1)
