"""!@package pytest_test_campaign Json Test campaign.

It contains test list and its config.

A test campaign file in json format, located in a runtest folder,
can be used to create a test campaign.
@section testCampaignName Test names
The json file describes a list of tests in the pytest syntax (a folder, a file,
a test function inside a file, markers, ...). There is also the possibility to
point to another json file.
The syntax is:
"name": "path/test_selection" where path is the relative path from $LETP_TESTS
or an absolute path.

Here is an example:
~~~~~~~~~~~~~{.xml}
[
    { "name": "legato/security/sandbox/host/test_basic.py::L_SandBox_0001" },
    { "name": "legato/security/sandbox/host/test_basic.py::L_SandBox_0004" },
]
~~~~~~~~~~~~~

And a combination of tests and inclusion of json files:
~~~~~~~~~~~~~{.xml}
[
    { "name": "legato/security/sandbox/host/test_basic.py::L_SandBox_0001" },
    { "name": "legato/c-runtime/timers/runtest/timers.json" },
    { "name": "legato/c-runtime/file/runtest/file.json" }
]
~~~~~~~~~~~~~

With the tag "main_config", the user can set the xml parameters or include xml
files (same parameters as the  Command line --config). See the "–ci" option for
creating automatically the "main_config" content based on the xml files. <br>
With the tag "config", specifically for a test function or a json test set, it is
possible to override the default parameters with other xml config files or to set
a xml field. If it a json test set, this specific configuration will be applied for
all the tests declared in the test set.

In the following example, the serial link 2 (slink2 for AT commands) is activated
and generic_config.xml is also applied for the all the tests of this file. <br>
config/test/foo_sandbox.xml is only applied to sandbox.json. <br>
The extra configuration of the tests L_AVC2_AtCommand_0001 is foo_airvantage.xml
and bar_airvantage.xml. Moreover host/nfs_mount is set to "/tmp/NFS".
~~~~~~~~~~~~~{.xml}
{
    "main_config": [
                    "$LETP_TESTS/config/test/generic_config.xml",
                    "module/slink2(used)=1",
                    "module/slink2/desc=at",
                    "module/slink2/name=/dev/ttyUSB1",
                    "module/slink2/port=4002",
                    "module/slink2/rtscts=0",
                    "module/slink2/speed=115200"
                ]
},
{
    "name": "legato/security/sandbox/runtest/sandbox.json",
    "config": "config/test/foo_sandbox.xml"
},
{
    "name": "legato/services/airvantage/host/test_atCmd.py::L_AVC2_AtCommand_0001",
    "config": "foo_airvantage.xml,bar_airvantage.xml,host/nfs_mount=/tmp/NFS"
}
~~~~~~~~~~~~~
"""
import os
import json

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class TestsCampaign:
    """!Test campain container."""

    def __init__(self, file_name):
        self._file_name = file_name

    @staticmethod
    def _search_list(pattern, obj):
        ret = {}
        if pattern in obj:
            return obj[pattern]
        for item in obj:
            ret = TestsCampaign.search_item(pattern, item)
            if ret != {}:
                break
        return ret

    @staticmethod
    def _search_dict(pattern, obj):
        ret = {}
        if pattern in obj:
            return obj[pattern]
        else:
            for item in obj:
                # Python 3 compatibility hack for unicode
                try:
                    unicode("")
                except NameError:
                    unicode = str
                if isinstance(obj[item], (str, unicode)):
                    if pattern in obj[item]:
                        return obj
                    else:
                        break
                else:
                    ret = TestsCampaign.search_item(pattern, obj[item])
                    if ret != {}:
                        break
        return ret

    @staticmethod
    def search_item(pattern, obj):
        """Search for a pattern in a Json python representation."""
        ret = {}
        if isinstance(obj, list):
            ret = TestsCampaign._search_list(pattern, obj)
        elif isinstance(obj, dict):
            ret = TestsCampaign._search_dict(pattern, obj)
        return ret


class TestsCampaignJson(TestsCampaign):
    """!Test campaign in JSON format."""

    @staticmethod
    def read_tests_from_json(json_file):
        """Read tests info form one json file."""
        with open(json_file, "r") as fp:
            js = json.load(fp)
            # Search a configuration in the json file
            main_config_json = TestsCampaign.search_item("main_config", js)
            # Find the letp section
            letp_json = TestsCampaign.search_item("letp", js)
            if letp_json != {}:
                # letp token found. Expect the same format as the json
                # used in validation campaign
                tests_from_json = TestsCampaign.search_item("tests", letp_json)
            else:
                # Expect only a list of tests
                tests_from_json = js
        return main_config_json, tests_from_json

    @staticmethod
    def json_collect_tests(json_file, options=""):
        """Collect all the LeTP tests in a Json file.

        Search recursively if a json file is referenced.

        :json_file: path of Json test file
        :return: tuple composed of the list of the host tests
            and the list of the target tests
        """
        main_config_json, tests_from_json = TestsCampaignJson.read_tests_from_json(
            json_file
        )
        test_list_host = []
        test_list_target = []
        for test in tests_from_json:
            if "name" not in test:
                continue
            name = os.path.expandvars(test["name"])
            main_config_json_str = (
                (main_config_json[0] + ",") if len(main_config_json) != 0 else ""
            )
            config = (
                options
                + main_config_json_str
                + (test["config"] if "config" in test else "")
            )
            if not name.endswith(".json"):
                if "/target/" not in name:
                    test_list_host.append([name, config])
                else:
                    test_list_target.append([name, config])
                continue
            # Collect also the tests for this file
            (
                tests_host,
                tests_target,
                _tmp_main_config,
            ) = TestsCampaignJson.json_collect_tests(
                os.path.join(os.environ["LETP_TESTS"], name), config
            )
            if len(tests_host) != 0:
                test_list_host += tests_host
            if len(tests_target) != 0:
                test_list_target += tests_target
        # Returned a tuple with the host and target tests without
        # the json files and the main configuration passed by the json
        return (
            [
                [os.path.join(os.environ["LETP_TESTS"], test[0]), test[1]]
                for test in test_list_host
            ],
            test_list_target,
            main_config_json,
        )

    def get_tests(self):
        """Get tests tuples."""
        return self.json_collect_tests(self._file_name)
