r"""Airvantage API module.

Use the av_lib module to interact with the av_server module.

Examples
^^^^^^^^

.. code-block:: python

    from pytest_letp.lib import av_lib

    @pytest.mark.config("$LETP_TESTS/config/av_server.xml")
    def test_av_sync(target, read_config):
        # Create av handler
        av_handler = av_lib.AVManager(target, read_config)
        # Start sync job
        sync_job = av_handler.sync()
        # Start AVC session
        target.run_at_cmd("at+wdss=1,1", 90, [r"\+WDSI: 6", r"\+WDSI: 23,1"])
        # Wait for job to be successful
        assert av_handler.wait_for_operation_state(sync_job), "Sync job failed"
        # Stop AVC session
        target.run_at_cmd("at+wdss=1,0", 20, [r"\+WDSI: 8"])
"""
# pylint: disable=too-many-public-methods
from time import sleep
from pytest_letp.lib import swilog
from pytest_letp.lib.av_server import AVServer

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class AvLibException(Exception):
    """Airvantage library exception."""

    def __init__(self, msg=None):
        error_msg = "AvLibException"
        if msg:
            error_msg += f": {msg}"
        swilog.error(error_msg)
        super().__init__(error_msg)


class AVTargetAdapter:
    """Target adapter for AVManager."""

    def __init__(self, target):
        self.generic_name = target.generic_name
        self.system_type = target.module_name
        self.imei = target.imei
        self.uid = None


class AVResultVerifier:
    """Airvantage result helper class."""

    def __init__(self, verify_func, expected_result=None, inverse=False):
        """Airvantage result verifier.

        :param verify_func: Function to verify result against.
        :param expected_result: expected result of response.
        :param bool inverse: inverse the result.
        """
        self.verify_func = getattr(self, verify_func.__name__)
        self.expected_result = expected_result
        self.inverse = inverse

    def validate_rsp(self, rsp):
        """Validate response.

        :param rsp: response from AV function to validate in verify_func.

        :return bool: result of verify_func.
        """
        return self.verify_func(rsp)

    @staticmethod
    def return_rsp(rsp, boolean, return_rsp):
        """Return response or result depending on configuration.

        :param rsp: response to return.
        :param bool boolean: boolean to return.
        :param bool return_rsp: if True return reponse if False return boolean.

        :return rsp or bool: depending on value of return_rsp.
        """
        return rsp if return_rsp else boolean

    def is_not_none(self, cmp):
        """Return boolean result of cmp is not None.

        :param cmp: variable for comparison.

        :return bool: result of comparison.
        """
        return cmp is not None if not self.inverse else cmp is None

    def is_true(self, cmp):
        """Return boolean result of cmp is True.

        :param cmp: variable for comparison.

        :return bool: result of comparison.
        """
        return cmp if not self.inverse else not cmp

    def is_equal_to(self, cmp):
        """Return boolean result of cmp == alt.

        :param cmp: variable for comparison.

        :return bool: result of comparison.
        """
        return (
            cmp == self.expected_result
            if not self.inverse
            else cmp != self.expected_result
        )

    def is_greater_than(self, cmp):
        """Return boolean result of cmp > alt.

        :param cmp: variable for comparison.

        :return bool: result of comparison.
        """
        return (
            cmp > self.expected_result
            if not self.inverse
            else cmp < self.expected_result
        )

    def is_greater_than_or_equal_to(self, cmp):
        """Return boolean result of cmp >= alt.

        :param cmp: variable for comparison.

        :return bool: result of comparison.
        """
        return (
            cmp >= self.expected_result
            if not self.inverse
            else cmp <= self.expected_result
        )

    @staticmethod
    def compare_dict(cmp_dict, cmp_func):
        """Return dictionary of all non-None keys.

        :param dict cmp_dict: dictionary for comparison.
        :param function cmp_func: function to compare with.

        :return dict: result of comparison.
        """
        return {key: val for key, val in cmp_dict.items() if cmp_func(cmp=val)}


class AVManager:
    """Airvantage management tool."""

    def __init__(self, target, config):
        """Initialize AVLib.

        Steps:
            -# Get module information.
            -# Authenticate with server.
            -# Find module on server.
               If not found, create new system.

        :exception AvLibException: If failed to authenticate to server.
        """
        kwargs = {}
        for value in config.find("av_server"):
            kwargs[value.tag] = value.text if value.text else ""
        self.server = AVServer(**kwargs)
        self._module_info = AVTargetAdapter(target)
        if not self.server.authenticate():
            raise AvLibException("server authentication failed.")
        self._module_info.uid = self.server.find_system(self._module_info.imei)
        if not self._module_info.uid:
            self.create_system()
        self.uid = self._module_info.uid

    def create_system(self):
        """Create system on AirVantage."""
        swilog.warning(
            f"Module with imei: {self._module_info.imei} not found on server."
        )
        app_uid = self.server.find_application(
            name=self._module_info.generic_name,
            app_type=f"{self._module_info.system_type}_LE",
        )
        gateway_uid = self.server.find_gateway_uid(self._module_info.imei)
        swilog.info("Creating system on AirVantage server.")
        self.server.create_system(
            module_type=self._module_info.generic_name,
            imei=self._module_info.imei,
            gateway_uid=gateway_uid,
            app_uid=app_uid,
        )
        self._try_for_result(
            function=self.server.find_system,
            result_verifier=AVResultVerifier(AVResultVerifier.is_not_none),
            return_boolean=False,
            imei=self._module_info.imei,
        )

    @staticmethod
    def _try_for_result(
        function,
        result_verifier=AVResultVerifier(AVResultVerifier.is_true),
        attempts=30,
        wait_time=2,
        return_rsp=False,
        **kwargs,
    ):
        """Attempt to run function in iterations and compare result.

        :param function: function to run.
        :param kwargs: function arguments to pass in.
        :param result_verifier: class to verify result.
        :param int attempts: attempts to try for result.
        :param bool return_rsp:
                if True:
                    return function response.
                else:
                    return bool if result is True.

        :return rsp or bool: depending on value of return_rsp.
        """
        for i in range(attempts):
            swilog.info(f"Trying {function} attempt: {i + 1} of {attempts}")
            rsp = function(**kwargs)
            # Handle comparison operators.
            result = result_verifier.validate_rsp(rsp)
            if result:
                return AVResultVerifier.return_rsp(rsp, True, return_rsp)
            swilog.warning(f"Received {rsp} instead of {result}")
            sleep(wait_time)
        swilog.error(f"Did not receive {result} within {attempts} attempts")
        return AVResultVerifier.return_rsp(None, False, return_rsp)

    def wait_for_operation_state(
        self,
        uid,
        expected_state="FINISHED",
        expected_reason="SUCCESS",
        attempts=30,
        wait_time=2,
    ):
        """Wait for specified state of operation from AirVantage.

        :param str uid: operation uid.
        :param str expected_state: expected state of operation.
        :param str expected_reason: expected reason for state of operation.
        :param int attempts: number of attempts to check for operation.
        :param int wait_time: time to wait between checks.

        :return bool: True if state and reason are reached, otherwise False.
        """
        swilog.info("Checking operation state.")
        expected_result = {"state": expected_state, "reason": expected_reason}
        return self._try_for_result(
            function=self.server.operation_state,
            result_verifier=AVResultVerifier(
                AVResultVerifier.is_equal_to, expected_result
            ),
            attempts=attempts,
            wait_time=wait_time,
            uid=uid,
        )

    def get_app_info(self, **kwargs):
        """Get application info from AirVantage server.

        :param int app_uid: application uid.
        :param str app_name: application name.
        :param str app_revision: application revision.
        :param str app_type: application type.

        :return dict: app info in dictionary if successful, otherwise None.

        .. code-block:: python

            {
                "uid": (str),
                "name": (str),
                "revision": (str),
                "type": (str),
                "category": (str),
                "state": (str),
            }
        """
        app_uid = (
            kwargs["app_uid"]
            if "app_uid" in kwargs
            else self.server.find_application(**kwargs)
        )
        return self.server.application_details(app_uid=app_uid)

    def get_app_detail(self, detail, **kwargs):
        """Get application detail from AirVantage server.

        :param str detail: application detail
                ("uid", "name", "revision", "type", "category", "state")
        :param str app_uid: application uid.
        :param str app_name: application name.
        :param str app_revision: application revision.
        :param str app_type: application type.

        :return str: detail requested if successful, otherwise None.
        """
        return self.get_app_info(**kwargs)[detail]

    def remove_app(self, attempts=10, **kwargs):
        """Remove apps from AirVantage.

        Delete all apps matching description from AirVantage.
        Check if the apps are removed.

        :param str app_uid: application uid.
        :param str app_name: application name.
        :param str app_revision: application revision.
        :param str app_type: application type.
        :param int attempts: attempts to remove application.

        :return bool: True if successful, otherwise False.
        """
        previous_uid = ""
        for _ in range(attempts):
            swilog.info("Checking if there is an app that matches the desciption.")
            app_info = self.get_app_info(**kwargs)
            if not app_info:
                swilog.info(f"No apps found with:\n{kwargs}")
                return True
            if app_info["uid"] == previous_uid:
                swilog.error(f"Could not remove app:\n{app_info}")
                break
            swilog.info(f"Found app:\n{app_info}")
            swilog.info("Trying to remove app.")
            self._try_for_result(
                function=self.server.delete_application, uid=app_info["uid"]
            )
            previous_uid = app_info["uid"]
        swilog.warning(f"Failed to remove app:\n{kwargs}")
        return False

    def check_app_status(self, expected_status, attempts=10, **kwargs):
        """Check app status on airVantage.

        :param str app_uid: application uid.
        :param str app_name: application name.
        :param str app_revision: application revision.
        :param str app_type: application type.
        :param str expected_status: expected application status.
        :param int attempts: attempts to remove application.

        :return bool: True if expected_status matches status, otherwise False.
        """
        swilog.info(f"Checking app for status: {expected_status} on airVantage.")
        return self._try_for_result(
            function=self.get_app_detail,
            result_verifier=AVResultVerifier(
                AVResultVerifier.is_equal_to, expected_status
            ),
            attempts=attempts,
            detail="status" * kwargs,
        )

    def upload_app(self, file, app_name, app_revision, app_type):
        """Release and Publish app to airVantage.

        :param str file: path of file to upload.
        :param str app_name: application name.
        :param str app_revision: application revision.
        :param str app_type: application type.

        :return str: application uid if successful, otherwise None.
        """
        if not self.remove_app(app_revision=app_revision, app_type=app_type):
            swilog.warning(
                f"Cannot upload {app_name} to AirVantage, "
                "because another app with the same revision and type already exists."
            )
            return None
        swilog.info(f"Trying to release {app_name} onto AirVantage.")
        app_uid = self.server.release_application(file)
        if not self.check_app_status(expected_status="RELEASED", app_uid=app_uid):
            swilog.warning(f"Cannot release {app_name} onto AirVantage")
            return None
        swilog.info(f"Trying to publish {app_name} onto AirVantage")
        self.server.publish_application(app_uid)
        if not self.check_app_status(expected_status="PUBLISHED", app_uid=app_uid):
            swilog.warning(f"Cannot publish {app_name} onto AirVantage")
            return None
        return app_uid

    # =================================================================================
    # Wrapping Target System Functions
    # =================================================================================
    def system_activate_uid(self):
        """Activate a selection of systems.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_activate_uid(self.uid)

    def system_terminate_uid(self):
        """Terminates a selection of systems.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_terminate_uid(self.uid)

    def system_resume_uid(self):
        """Resume a selection of systems.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_resume_uid(self.uid)

    def system_suspend_uid(self):
        """Suspend a selection of systems.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_suspend_uid(self.uid)

    def system_delete_uid(self):
        """Delete a specific system from AirVantage.

        :return bool: True if successful, otherwise False.
        """
        return self.server.system_delete_uid(self.uid)

    def system_data_retrieve(self, obj):
        """Create a job to retrieve data.

        :param obj: data path. eg LE_AVDATA_CTRL.xxx.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_data_retrieve(self.uid, obj)

    def system_apply_settings(self, obj_data):
        """Apply settings to the system.

        :param data: data to be write. Data must be in list of dictionary type.

        .. code-block:: python

            [{"key" : "Path.to.app", "value" : 120}]
            # or
            [
                {"key" : "Path.key1", "value" : 120},
                {"key" : "Path.key2", "value" : 120}
            ]

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_apply_settings(self.uid, obj_data)

    def system_apply_command(self, command_id, parameters):
        """Apply command to the system.

        :param str command_id: data path.
        :param parameters: parameters value.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_apply_command(self.uid, command_id, parameters)

    def system_reboot(self):
        """Reboot device.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.system_reboot(self.uid)

    def system_message_list(self, size=10):
        """Get the list of messages of the system.

        :param int size: size the messages list.

        :return list: list of message uids if successful, otherwise None.
        """
        return self.server.system_message_list(self.uid, size)

    def system_message_details(self, message_uid):
        """Detailed message of system associated with message ID.

        :param str message_uid: message uid.

        :return dict: json formed message details if successful, otherwise None.
        """
        return self.server.system_message_details(self.uid, message_uid)

    def system_last_datapoints(self, points=None, prefix=None):
        """Get the last data point of the system.

        :param str points: list of data ids separated by a ','.
        :param str prefix: prefix of requested data ids.

        :return dict: json formed data details if successful, otherwise None.
        """
        return self.server.system_last_datapoints(self.uid, points, prefix)

    def get_data_value_path(self, path="lwm2m.3.0.0"):
        """Get the data value associated with lwm2m path.

        :param str path: lwm2m path.

        :return str: lwm2m data value if successful, otherwise None.
        """
        return self.server.get_data_value_path(self.uid, path)

    def get_pending_operations(self):
        """Get list of pending operations.

        :return list: list of pending operation uids if successful, otherwise None.
        """
        return self.server.get_pending_operations(self.uid)

    def cancel_pending_operations(self):
        """Cancel all pending operations."""
        for uid in self.get_pending_operations():
            self.server.cancel_operation(uid)
            assert self.wait_for_operation_state(
                uid, expected_state="FINISHED", expected_reason="CANCELLED"
            ), "Failed to cancel operation"

    def sync(self):
        """Create a sync Job on av server.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.sync(self.uid)

    def install_application(self, app_uid):
        """Install an application.

        :param str app_uid: application uid.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.install_application(self.uid, app_uid)

    def uninstall_application(self, app_uid):
        """Uninstall an application.

        :param str app_uid: application uid.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.uninstall_application(self.uid, app_uid)

    def start_application(self, app_uid):
        """Start an application.

        :param str app_uid: application uid.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.start_application(self.uid, app_uid)

    def stop_application(self, app_uid):
        """Stop an application.

        :param str app_uid: application uid.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.stop_application(self.uid, app_uid)

    def send_sms(self, text="hello"):
        """Send SMS to the system.

        :param str text: text content.

        :return str: operation uid if successful, otherwise None.
        """
        return self.server.send_sms(self.uid, text)
