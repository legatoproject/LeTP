"""!Airvantage Rest API."""
# pylint: disable=too-many-public-methods,too-many-instance-attributes
import os
import json
import requests
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class AVServer:
    """!Connection between letp and AirVantage rest api."""

    def __init__(self, url, username, password, client_id, client_secret, company):
        """!Initialize AVServer.

        @param url: url of airvantage server.
        @param username: client username.
        @param password: client password.
        @param client_id: client id.
        @param client_secret: client secret.
        @param company: client company.
        """
        self._url = url
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret
        self._company = company
        self._access_token = None
        self._headers = {"Content-Type": "application/json"}
        self._default_data = {
            "requestConnection": True,
            "scheduledTime": None,
            "timeout": None,
            "notify": False,
        }

    # =================================================================================
    # Helper functions
    # =================================================================================
    def _query(self, **kwargs):
        """!Generate a query from kwargs.

        @return dict: organized query dictionary.
        """
        query = {"company": self._company, "access_token": self._access_token}
        for key, val in kwargs.items():
            query[key] = val
        return query

    @staticmethod
    def _request(**kwargs):
        """!Request function for running Python http requests.

        @param **kwargs: arguments passed to requests.request.

        @return requests response object.
        """
        try:
            return requests.request(**kwargs)
        except requests.exceptions.RequestException as e:
            swilog.error(f"error in request: {e}")
            return None

    def _request_json_entry(self, entry, **kwargs):
        """!Request function for running Python http requests json.

        @param entry(str): json entry to return.
        @param **kwargs: arguments passed to requests.request.

        @return dict: json entry from response.
        """
        response = self._request(**kwargs)
        if not response:
            return None
        try:
            return response.json()[entry]
        except KeyError:
            swilog.error(f"error {entry} is not in response")
            return None

    def _request_item_uid(self, **kwargs):
        """!Request function for getting uid of request.

        @param entry(str): json entry to return.
        @param **kwargs: arguments passed to requests.request.

        @return str: uid entry from response.
        """
        response = self._request(**kwargs)
        if not response:
            return None
        try:
            return response.json()["items"][0]["uid"]
        except KeyError:
            swilog.error("error items/0/uid is not in response")
            return None

    def _post_data(self, specific_dict):
        """!Combine default data for post as well as specific."""
        data = self._default_data
        data.update(specific_dict)
        return json.dumps(data)

    # =================================================================================
    # Setup functions
    # =================================================================================
    def authenticate(self):
        """!Request an access token from AirVantage.

        @return bool: True if successful, otherwise False.
        """
        url = self._url + "/api/oauth/token"
        query = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        self._access_token = self._request_json_entry(
            entry="access_token",
            method="GET",
            url=url,
            headers=self._headers,
            params=query,
        )
        return self._access_token is not None

    # =================================================================================
    # System Functions
    # =================================================================================
    def create_system(
        self, name=None, module_type=None, imei=None, gateway_uid="", app_uid=""
    ):
        """!Create a new system.

        @param name (str): system name.
        @param module_type (str): generic module type.
        @param imei (str): system imei.
        @param gateway_uid (str): module gateway uid.
        @param app_uid (str): module app uid.

        @return str: system uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/systems"
        query = self._query()
        if not name:
            if "TB_ID" in os.environ:
                name = f"{os.environ['TB_ID']}_{module_type}"
            else:
                name = f"{module_type}_{imei}"
        data = {
            "systems": {"uids": [None]},
            "name": name,
            "state": "READY",
            "lifeCycleState": "ACTIVE",
            "gateway": {"uid": gateway_uid},
            "applications": [{"uid": app_uid}],
        }
        return self._request_json_entry(
            entry="uid",
            method="POST",
            url=url,
            data=json.dumps(data),
            headers=self._headers,
            params=query,
        )

    def find_system(self, imei):
        """!Find target on server.

        @param imei (str): target imei.

        @return str: system uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/systems"
        query = self._query(gateway=f"imei:{imei}")
        return self._request_item_uid(
            method="GET", url=url, headers=self._headers, params=query
        )

    def find_gateway_uid(self, imei):
        """!Find gateway uid.

        @param imei (str): target imei.

        @return str: gateway uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/gateways"
        query = self._query(imei=imei, fields="uid")
        return self._request_item_uid(
            method="GET", url=url, headers=self._headers, params=query
        )

    def system_activate_uid(self, uid):
        """!Activate a selection of systems.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/activate"
        query = self._query()
        data = self._post_data({"systems": {"uids": [uid]}})
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_terminate_uid(self, uid):
        """!Terminates a selection of systems.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/terminate"
        query = self._query()
        data = self._post_data({"systems": {"uids": [uid]}})
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_resume_uid(self, uid):
        """!Resume a selection of systems.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/resume"
        query = self._query()
        data = self._post_data({"systems": {"uids": [uid]}})
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_suspend_uid(self, uid):
        """!Suspend a selection of systems.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/suspend"
        query = self._query()
        data = self._post_data({"systems": {"uids": [uid]}})
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_delete_uid(self, uid):
        """!Delete a specific system from AirVantage.

        @param uid (str): system uid.

        @return bool: True if successful, otherwise False.
        """
        url = self._url + f"/api/v1/systems/{uid}"
        query = self._query()
        response = self._request(
            method="DELETE", url=url, headers=self._headers, params=query
        )
        return response.ok

    def system_data_retrieve(self, uid, obj):
        """!Create a job to retrieve data.

        @param uid (str): system uid.
        @param obj: data path. eg LE_AVDATA_CTRL.xxx.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/data/retrieve?"
        query = self._query()
        specific_data = {"reboot": False, "systems": {"uids": [uid]}, "data": [obj]}
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_apply_settings(self, uid, obj_data):
        """!Apply settings to the system.

        @param uid (str): system uid.
        @param data: data to be write. Data must be in list of dictionary type.
                    eg: [{"key" : "Path.to.app", "value" : 120}]
                        or
                        [
                            {"key" : "Path.key1", "value" : 120},
                            {"key" : "Path.key2", "value" : 120}
                        ]

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/settings?"
        query = self._query()
        specific_data = {"reboot": False, "systems": {"uids": [uid]}, "settings": []}
        for content in obj_data:
            specific_data["settings"].append(content)
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_apply_command(self, uid, command_id, parameters):
        """!Apply command to the system.

        @param uid (str): system uid.
        @param command_id (str): data path.
        @param parameters: parameters value.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/command?"
        query = self._query()
        specific_data = {
            "reboot": False,
            "systems": {"uids": [uid]},
            "commandId": command_id,
            "parameters": parameters,
        }
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_reboot(self, uid):
        """!Reboot device.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/reboot?"
        query = self._query()
        data = self._post_data({"systems": {"uids": [uid]}})
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def system_message_list(self, uid, size=10):
        """!Get the list of messages of the system.

        @param uid (str): system uid.
        @param size (int): size the messages list.

        @return list: list of message uids if successful, otherwise None.
        """
        url = self._url + f"/api/v1/systems/{uid}/messages?"
        query = self._query(size=size)
        uid_list = []
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        try:
            for i in range(size):
                uid_list.append(response.json()["messages"][i]["uid"])
            return uid_list
        except KeyError:
            return None

    def system_message_details(self, uid, message_uid):
        """!Detailed message of system associated with message ID.

        @param uid (str): system uid.
        @param message_uid (str): message uid.

        @return dict: json formed message details if successful, otherwise None.
        """
        url = self._url + f"/api/v1/systems/{uid}/messages/{message_uid}"
        query = self._query()
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        return response.json()

    def system_last_datapoints(self, uid, points=None, prefix=None):
        """!Get the last data point of the system.

        @param uid (str): system uid.
        @param points (str): list of data ids separated by a ','.
        @param prefix (str): prefix of requested data ids.

        @return dict: json formed data details if successful, otherwise None.
        """
        url = self._url + f"/api/v1/systems/{uid}/data?"
        query = self._query()
        if points:
            query["ids"] = points
        if prefix:
            query["idPrefix"] = prefix
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        return response.json()

    def get_data_value_path(self, uid, path="lwm2m.3.0.0"):
        """!Get the data value associated with lwm2m path.

        @param uid (str): system uid.
        @param path (str): lwm2m path.

        @return str: lwm2m data value if successful, otherwise None.
        """
        url = self._url + f"/api/v1/systems/{uid}/data?"
        query = self._query()
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        return response.json()[path][0]["value"]

    # =================================================================================
    # Operation Functions
    # =================================================================================
    def get_pending_operations(self, uid):
        """!Get list of pending operations.

        @param uid (str): system uid.

        @return list: list of pending operation uids if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations?"
        query = self._query(
            entities="system", asc="name", states="IN_PROGRESS", target=uid
        )
        op_list = []
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        try:
            if response.json()["count"] == 0:
                return None
            for operation in response.json()["items"]:
                op_list.append(operation["uid"])
            return op_list
        except KeyError:
            return None

    def operation_state(self, uid):
        """!Check the operation state and verify.

        @param uid (str): operation uid.

        @return dict: operation state if successful, otherwise None.
                {
                    "state": {SCHEDULED, IN_PROGRESS, FINISHED},
                    "reason": {PENDING, IN_PROGRESS, CANCELLED, FAILURE, SUCCESS},
                }
        """
        url = self._url + f"/api/v1/operations/{uid}?"
        query = self._query()
        result = {"state": "UNKNOW", "reason": "UNKNOW"}
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        try:
            result["state"] = response.json()["state"]
            for i in range(len(response.json()["counters"])):
                if response.json()["counters"][i]["count"] != 0:
                    result["reason"] = response.json()["counters"][i]["state"]
            return result
        except KeyError:
            return None

    def cancel_operation(self, uid):
        """!Cancel an operation.

        @param uid (str): operation uid.

        @return bool: True if successful, otherwise False.
        """
        url = self._url + f"/api/v1/operations/{uid}/cancel?"
        query = self._query()
        data = self._post_data({"reboot": False})
        response = self._request(
            method="POST", url=url, data=data, headers=self._headers, params=query
        )
        return response.ok

    def sync(self, uid):
        """!Create a sync Job on av server.

        @param uid (str): system uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/synchronize?"
        query = self._query()
        specific_data = {"reboot": False, "systems": {"uids": [uid]}}
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def install_application(self, uid, app_uid):
        """!Install an application.

        @param uid (str): system uid.
        @param app_uid (str): application uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/applications/install?"
        query = self._query()
        specific_data = {
            "reboot": False,
            "systems": {"uids": [uid]},
            "application": app_uid,
        }
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def uninstall_application(self, uid, app_uid):
        """!Uninstall an application.

        @param uid (str): system uid.
        @param app_uid (str): application uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/applications/uninstall?"
        query = self._query()
        specific_data = {
            "reboot": False,
            "systems": {"uids": [uid]},
            "application": app_uid,
        }
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def start_application(self, uid, app_uid):
        """!Start an application.

        @param uid (str): system uid.
        @param app_uid (str): application uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/applications/start?"
        query = self._query()
        specific_data = {
            "reboot": False,
            "systems": {"uids": [uid]},
            "application": app_uid,
        }
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def stop_application(self, uid, app_uid):
        """!Stop an application.

        @param uid (str): system uid.
        @param app_uid (str): application uid.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/applications/stop?"
        query = self._query()
        specific_data = {
            "reboot": False,
            "systems": {"uids": [uid]},
            "application": app_uid,
        }
        data = self._post_data(specific_data)
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def send_sms(self, uid, text="hello"):
        """!Send SMS to the system.

        @param uid (str): system uid.
        @param text (str): text content.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/systems/sms?"
        query = self._query()
        data = {"content": text, "reboot": False, "systems": {"uids": [uid]}}
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=json.dumps(data),
            headers=self._headers,
            params=query,
        )

    # =================================================================================
    # Application Functions
    # =================================================================================
    def find_application(self, name=None, app_type=None, revision="1.0.0"):
        """!Find a application on the airvatage server.

        @param name (str): application name.
        @param app_type (str): application type.
        @param revision (str): application revision.

        @return str: application uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/applications?"
        query = self._query(fields="uid", name=name, type=app_type, revision=revision)
        return self._request_item_uid(
            method="GET", url=url, headers=self._headers, params=query
        )

    def release_application(self, file):
        """!Release  an Application.

        @param file (str): path to application zip file.

        @return str: operation uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/applications/release?"
        query = self._query()
        assert os.path.exists(file), f"File {file} does not exist."
        with open(file, "rb") as f:
            data = f.read()
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=data,
            headers=self._headers,
            params=query,
        )

    def publish_application(self, app_uid):
        """!Publish an application.

        @param app_uid (str): application uid.

        @return str: opertaion uid if successful, otherwise None.
        """
        url = self._url + "/api/v1/operations/applications/publish?"
        query = self._query()
        data = {"application": app_uid}
        return self._request_json_entry(
            entry="operation",
            method="POST",
            url=url,
            data=json.dumps(data),
            headers=self._headers,
            params=query,
        )

    def delete_application(self, app_uid):
        """!Delete an application.

        @param app_uid (str): application uid.

        @return str: opertaion uid if successful, otherwise None.
        """
        url = self._url + f"/api/v1/applications/{app_uid}?"
        query = self._query()
        response = self._request(
            method="DELETE", url=url, headers=self._headers, params=query
        )
        return response.status_code == 200

    def application_details(self, app_uid):
        """!Request Application content.

        @param app_uid: application uid

        @return dict: application details if successful, otherwise None.
                {
                    "deprecated": (timestamp),
                    "released": (timestamp),
                    "published": (timestamp),
                    "category": (str),
                    "applicationManager": (str),
                    "isPublic": (bool),
                    "isReference": (bool),
                    "revision": (str),
                    "labels": (list),
                    "ownerCompany": (str),
                    "uid": (str),
                    "owner": {
                        "uid": (str),
                        "name": (str),
                    },
                    "type": (str),
                    "state": (str),
                    "name": (str),
                }
        """
        url = self._url + f"/api/v1/applications/{app_uid}?"
        query = self._query()
        response = self._request(
            method="GET", url=url, headers=self._headers, params=query
        )
        return response.json()
