"""Test configurations."""
import enum
import json
import os
import pathlib
import pprint
import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

from pytest_letp.lib import swilog
from pytest_letp.lib.misc import convert_path
from pytest_letp.tools.html_report.test_report import ALL_COMPONENTS

__copyright__ = "Copyright (C) Sierra Wireless Inc."


TEST_CONFIG_KEY = "LeTPTestConfig"


class ConfigType(enum.Enum):
    """The test configuration type."""

    # Configured attributes of the tag. e.g. test_run/context(context2)=456
    XML_ATTR = enum.auto()
    # Configured tags. e.g. module/name=ar7594
    XML_TAG = enum.auto()
    # Configured files. e.g. scenario/config/target_ar759x.xml
    XML_FILE = enum.auto()


class TestConfigsParser:
    """Test Configuration parser.

    e.g. --config and the configuration in the json file for the test.

    The each configuration item follows xml path related formats:

    1. Change the tag:
       module/name=ar7594
    2. Change the attribute of the tag
       test_run/context(context2)=456
    3. Use one specific xml file. The whole file will be included.
       scenario/config/target_ar759x.xml

    The item may contains , for multiple configs.
    """

    def __init__(self, cmd_line_cfgs: list):
        """Init a configs parser object.

        Args:
            cmd_line_cfgs: the configuration array.
        """
        assert isinstance(cmd_line_cfgs, list)
        self.cmd_line_cfgs = cmd_line_cfgs if cmd_line_cfgs else []
        self.config_dict = {}
        for each in ConfigType:
            self.config_dict[each] = []
        self._run()

    def get_tag_configs(self):
        """Get tags configurations."""
        return self.config_dict[ConfigType.XML_TAG]

    def get_attributes_configs(self):
        """Get configs for xml attributes.

        e.g. test_run/context(context2)=456
        """
        return self.config_dict[ConfigType.XML_ATTR]

    def get_all_set_configs(self):
        """Get all set configs with =."""
        return self.get_tag_configs() + self.get_attributes_configs()

    def get_xml_configs(self):
        """Get configs for the tag.

        e.g. test_run/id=test
        """
        return self.config_dict[ConfigType.XML_FILE]

    def is_valid(self):
        """Check any configuration exists."""
        return any(self.config_dict.values())

    def _build_cfg_array(self):
        """Build configs with no ',' inside."""
        # each element may also contain ,
        joined_config = ",".join(self.cmd_line_cfgs)
        simple_configs_array = joined_config.split(",")
        return simple_configs_array

    def _run(self):
        """Run the parser to fill in configuration dictionary."""
        simple_configs_array = self._build_cfg_array()
        for config in simple_configs_array:
            assert isinstance(config, str)
            if not config:
                # Empty string ''
                continue
            if ")=" in config:
                self.config_dict[ConfigType.XML_ATTR].append(config)
            elif "=" in config:
                self.config_dict[ConfigType.XML_TAG].append(config)
            elif config.endswith("xml"):
                self.config_dict[ConfigType.XML_FILE].append(config)
            else:
                raise NotImplementedError


class LeTPConfigPath:
    """LeTP tests may contain several config trees in different folders."""

    def __init__(self, config_path):
        """Init a relative LeTP config path.

        Input examples: $LETP_TESTS/scenario/config/target_wp750x.xml
        scenario/config/target_wp750x.xml
        """
        self.config_path = config_path

    @staticmethod
    def _find_matched_module_config(xml_dir_name, file_name):
        """Find the matched module config.

        e.g. wp7603.xml -> wp76xx.xml
        """
        all_modules = os.listdir(xml_dir_name)
        matched_prefix_array = []
        for module_name in all_modules:
            sequence_matcher = SequenceMatcher(None, file_name, module_name)
            all_matches = sequence_matcher.get_matching_blocks()
            prefix_match_length = 0
            for _match in all_matches:
                if _match.a == 0 and _match.b == 0:
                    prefix_match_length = _match.size
            matched_prefix_array.append(prefix_match_length)
        max_matched = max(matched_prefix_array)
        resolved_xml_file = None
        if max_matched >= 4:
            # Match at least four digits prefix. WPXX, ARXX, etc.
            # e.g. wp7604 will match wp76xx.xml
            xml_file_name_index = matched_prefix_array.index(max_matched)
            candidate_xml_file_name = all_modules[xml_file_name_index]
            resolved_xml_file = os.path.join(xml_dir_name, candidate_xml_file_name)
            swilog.warning("{} will be used!".format(resolved_xml_file))
        return resolved_xml_file

    @staticmethod
    def _find_xml_config(xml_file):
        if os.path.exists(xml_file):
            return xml_file
        xml_dir_name = os.path.dirname(xml_file)
        if (os.path.exists(xml_dir_name) and
                xml_dir_name.endswith(("/module", "\\module"))):
            file_name = os.path.basename(xml_file)
            return LeTPConfigPath._find_matched_module_config(xml_dir_name, file_name)
        return None

    def resolve_xml(self):
        """Resolve the matched xml files.

        Searching order in the configuration trees:
        1. $LETP_TESTS
        2. letp-internal
        3. LeTP
        """
        if "$" in self.config_path:
            xml_file = os.path.expandvars(self.config_path)
            return self._find_xml_config(xml_file)
        else:
            current_path = pathlib.Path(os.path.abspath(__file__))
            letp_test_config_dir = os.environ["LETP_TESTS"]
            letp_internal_config_dir = os.environ["LETP_INTERNAL_PATH"]
            letp_config_dir = os.path.join(current_path.parent)
            for dir_name in [
                letp_test_config_dir,
                letp_internal_config_dir,
                letp_config_dir,
            ]:
                if not (dir_name and os.path.exists(dir_name)):
                    continue
                xml_file_path = os.path.join(dir_name, self.config_path)
                resolved_xml_file = self._find_xml_config(xml_file_path)
                if resolved_xml_file:
                    swilog.info("{} will be used".format(resolved_xml_file))
                    return resolved_xml_file
            swilog.error("Cannot resolve {}".format(self.config_path))
            return None


class TestConfig:
    # pylint: disable=too-many-public-methods
    """Target config object for the test.

    For referencing attributes in xml, the representation must be in a
    convention of "<parent_tag_name>/<child_tag_name>"
    """

    default_cfg_file = os.environ.get("LETP_CONFIG_XML",
                                      os.path.join("config", "testbench.xml"))
    test_base_report_cache = os.path.join(
        "log", "letp_test_results.json"
    )  # letp_tests_info
    default_cfg_xml_cache = os.path.join("log", "default_test_cfg.xml")
    last_test_config_file = os.path.join("log", "last_test_cfg.xml")
    default_cfg = None
    test_list = []

    def __init__(self, cmd_line_cfgs=None):
        self._config_container = ET.ElementTree(ET.Element("test"))
        self._elem_dict = {}  # Dictionary format of configs.
        # List with all the xml files to include
        self.xml_file_lists = []
        # List containing the executed tests
        self.collected_tests = []
        # config_params: parameters from json or command line.
        self.cmd_line_cfgs = cmd_line_cfgs if cmd_line_cfgs else []
        self.test_base_reports = None

    def get(self):
        """Get the target config in xml tree."""
        return self._config_container

    def _get_xml_root(self):
        """Get test configuration xml root."""
        return self.get().getroot()

    def _get_config_xml_in_str(self):
        """Get the target config in xml."""
        return ET.tostring(self._get_xml_root(), encoding="unicode")

    def get_testbed_id(self):
        """Get testbed ID from letp configuration.

        Description:
        Checks and get testbed ID if it is configurated from letp

        Returns:
            testbed ID if element contains testbed ID
            None otherwise
        """
        try:
            return self._get_xml_root().find("testbed/id").text
        except AttributeError:
            return None

    def get_site(self):
        """Get site ID from letp configuration.

        Descriptions:
        Parse site ID from testbed ID

        Returns:
            Site ID if element contains testbed ID
            None otherwise
        """
        if self.get_testbed_id() is not None:
            parse_testbed_id = self.get_testbed_id().split("-")
            site = parse_testbed_id[len(parse_testbed_id) - 2].upper()
            return site
        return None

    @staticmethod
    def _create_parent_folder(file_name):
        file_dir_name = os.path.dirname(file_name)
        pathlib.Path(file_dir_name).mkdir(exist_ok=True)

    def save_test_cfg_cache(self, file_name=None):
        """Save test configuration cache for debugging."""
        if not file_name:
            file_name = self.default_cfg_xml_cache
        self._create_parent_folder(file_name)
        all_xml_config = self._get_config_xml_in_str()
        with open(file_name, "w") as f_io:
            f_io.write(all_xml_config)

    def save_test_report_cache(self, file_name=None):
        """Save test results cache."""
        if not file_name:
            file_name = TestConfig.test_base_report_cache
        self._create_parent_folder(file_name)
        json_content = self.test_base_reports
        with open(file_name, "w") as f_io:
            json.dump(json_content, f_io, indent=4)
        print("File {} was created!".format(file_name))

    def add_test_components(self, components: dict):
        """Save the test env components."""
        if components:
            new_comp = self._build_component_lst(components)

            if "components" not in self._elem_dict:
                self._elem_dict["components"] = new_comp
            else:
                existing_comp = self._elem_dict["components"]
                self._elem_dict["components"] = existing_comp + new_comp

    def get_test_components(self):
        """Return the test env components."""
        return self._elem_dict.get("components")

    def _get_args_config(self, key):
        """Get test config from element dictionary."""
        if self._elem_dict and key in self._elem_dict:
            return self._elem_dict[key]
        return None

    @staticmethod
    def _get_context_key(context_key):
        """Get context key from 'test_run/context(jenkins.job)."""
        return re.sub("[()]", "", context_key.strip("test_run/context"))

    @staticmethod
    def _build_component_lst(components: dict):
        comp_lst = []

        if components:
            assert isinstance(
                components, dict
            ), r"components must be a format of {comp_name:comp_value}"

            for comp in ALL_COMPONENTS:
                if comp in components:
                    comp_str = "{}:{}".format(comp, components[comp])
                    comp_lst.append(comp_str)

        return comp_lst

    def get_context_configs(self) -> dict:
        """Get context config dictionary.

        e.g. one config entry:
        "test_run/context(jenkins.job):
        test_run/context(jenkins.job)=Legato-QA-TestEngine".
        """
        dct = {
            self._get_context_key(key): self._elem_dict[key].split("=")[1]
            for key in self._elem_dict
            if "test_run/context(" in key
        }
        return dct

    def _get_args_config_value(self, key):
        """Get values from args config.

        One entry
        "test_run/context(jenkins.job):
            test_run/context(jenkins.job)=Legato-QA-TestEngine".
        """
        value = self._get_args_config(key)
        if value:
            return value.replace("{}=".format(key), "")
        return None

    def get_jenkins_job(self):
        """Read jenkins job config if there is any."""
        return self._get_args_config_value("test_run/context(jenkins.job)")

    def get_target_name(self):
        """Read target name config if there is any."""
        return self._get_args_config_value("module/name")

    def get_test_campaign(self):
        """Read test campaign config if there is any."""
        return self._get_args_config_value("test_run/context(test.campaign)")

    def _get_parent_tag(self, tag_names):
        """Get the parent tag in the sequence of tag names."""
        parent_tag = None
        if self._config_container:
            curr_path = ""
            for tag in tag_names:
                curr_path = os.path.join(curr_path, tag)
                elmt = self._config_container.find(curr_path)
                if not isinstance(elmt, ET.Element):
                    break
                parent_tag = elmt

        if parent_tag is None:
            # can't find any tag in the xml tree, so appends
            # the new tags to the root
            parent_tag = self._get_xml_root()

        return parent_tag

    def _add_tag(self, path):
        """Add the tag to the xml tree."""
        if self._config_container:
            tag_names = path.split("/")
            parent_tag = self._get_parent_tag(tag_names)
            curr_path = parent_tag.tag

            if parent_tag.tag in tag_names:
                end_idx = tag_names.index(parent_tag.tag) + 1
                curr_path = "/".join(tag_names[:end_idx])
                del tag_names[:end_idx]

            if curr_path == "test":
                curr_path = ""

            for tag in tag_names:
                new_tag = ET.Element(tag)
                parent_tag.append(new_tag)
                curr_path = os.path.join(curr_path, tag)
                parent_tag = self._config_container.find(curr_path)

    def _search_for_value(self, key, config_container):
        """Search for value in the configuration tree by priority."""
        # Search in --config parameters as it has more priority
        val = None
        for params in self.cmd_line_cfgs:
            # Search in the input config_params
            if key in params:
                # parameters can be separated by comma
                m = re.search("%s=(.*?)," % (key), params)
                if m is None:
                    # targeted parameter can be standalone or
                    # at the end
                    # of several parameters (no comma)
                    m = re.search("%s=(.*)" % (key), params)
                val = m.group(1)
        # if val is None or val == "":
        #     # Search in the current cfg
        #     val = current_root.findtext(key)
        if val is None and config_container is not None:
            # Search for the default config in the config container.
            val = config_container.findtext(key)
        assert val is not None and val != "", (
            "The xml element '%s' was not found or filled"
            " in the configuration files" % (key)
        )
        return val

    def _merge_elements(self, current_root, xpath, config_container):
        """Merge current_root's xpath elements into the test config."""
        if "include_xml" in xpath:
            # include_xml elements are not procssed here.
            return
        global_elements = config_container.findall(xpath)
        if len(global_elements) > 1:
            assert (
                len(global_elements) <= 1
            ), "The test config should have one absolute path at most."
        global_element = global_elements[0] if global_elements else config_container
        if config_container.tag == "target2" and xpath == ".":
            xpath = "./module/"
        else:
            xpath = "{}/".format(xpath)
        all_elements = current_root.findall(xpath)
        for element in all_elements:
            global_child_element = global_element.find(element.tag)
            if global_child_element is None:
                # new tag
                global_element.insert(-1, element)
                continue
            global_child_element.attrib.update(element.attrib)
            global_child_element.text = element.text
            new_xpath = "{}{}".format(xpath, element.tag)
            self._merge_elements(current_root, new_xpath, config_container)

    @staticmethod
    def _get_current_root(config):
        # xml file configuration
        xml_file = LeTPConfigPath(config).resolve_xml()
        assert xml_file, "xml {} cannot be found.".format(config)
        cfg = ET.parse(xml_file)
        current_root = cfg.getroot()
        if current_root is None:
            return None
        assert (
            current_root.tag == "test"
        ), " Test configs should have root element 'test'"
        return current_root

    def _include_one_cfg_xml(self, config, config_container=None):
        """Create one cfg xml.

        Merge all existing elements. Process include_xml if there is
        any.
        """
        if config_container is None:
            config_container = self._config_container.getroot()
        assert config.endswith("xml")
        self.xml_file_lists.append(config)
        current_root = self._get_current_root(config)
        if current_root is None:
            return
        self._merge_elements(current_root, ".", config_container)
        included_xmls = current_root.findall(".//include_xml/file")
        for child in included_xmls:
            config_file = child.text
            child_config_file = self.expand_file_name(config_file)
            if "target2.xml" in config and "module" in child_config_file:
                config_container = config_container.find("target2")
            self._include_one_cfg_xml(child_config_file, config_container)

    def expand_file_name(self, config_file):
        """Expand file name with regex $("KEY").

        Treat the case of inclusion
        Replace reference to a xml element.
        Format is : $("element_path")
        such as $("module/name")
        e.g. config/module/specific/$("module/name").xml
        """
        config_container = self._config_container.getroot()
        for match in re.finditer(r'\$\("(.+?)"\)', config_file):
            key = match.group(1)
            val = self._search_for_value(key, config_container)
            config_file = config_file.replace(match.group(0), val)
        config_file = convert_path(config_file)  # for platform compatibility
        return config_file

    def create_cfg_xml(self, config_files):
        """Read the xml configuration file.

        Args:
            config_files: list of xml config files used to search for an unknown value.

        It is possible to include other xml files with the tag "include_xml".
        It is also possible to use the text value of a xml element in the file path
        to include with $(). In the following example, $("name") refers to the
        parameter name ("WP7502") of the xml.

        .. literalinclude:: ../../../test/config/target.xml

        In the included file, the tag "include_child_only" allows to include all the
        child of the root tree, not the root tree.
        """
        # Go to LeTP tests because configuration file path can
        # be relative to the path of execution
        swilog.info("Create config from {}".format(config_files))
        old_path = os.getcwd()
        if "LETP_TESTS" in os.environ:
            os.chdir(os.environ["LETP_TESTS"])
        # --config can be called multiple times
        for config in config_files:
            # the xml files can be separated by a comma
            if config in self.xml_file_lists:
                # Already processed
                continue
            self._include_one_cfg_xml(config)
        # Go to previous path
        os.chdir(old_path)

    def apply_extra_config(self, cfg):
        """Apply extra configs in value pairs.

        The format: key=value in the --config arg[,arg2]. Two
        variations: test_run/id=test test_run/context(context2)=456
        tag config must precede before attribute config
        """
        for config in cfg:
            # the xml files can be separated by a comma
            if not isinstance(config, str):
                continue
            for f in config.split(","):
                # Check it is a key/value
                if "=" in f:
                    if ")=" in f:
                        # Contains Attribute
                        param, val = f.split("=")
                        path, attr = param.split("(")
                        attr = attr.replace(")", "")
                        elem = self._config_container.find(path)
                        if elem is None:
                            self._add_tag(path)
                            elem = self._config_container.find(path)

                        if isinstance(elem, ET.Element):
                            elem.set(attr, val)
                            continue
                    else:
                        command = f.split("=")
                        key = command[0]
                        elem = self._config_container.find(key)
                        if elem is None:
                            self._add_tag(key)
                            elem = self._config_container.find(key)

                        if isinstance(elem, ET.Element):
                            # join in case the value has "="
                            elem.text = "=".join(command[1:])
                            continue
                    # It can happen with the jenkins json file
                    # It contains all the xml parameters
                    # (even not the default params)
                    # print("%s was not found" % (key))
                    swilog.debug("No default value for {}, not applied.".format(f))
                else:
                    swilog.debug("Ignore {} at this step.".format(f))

    def store_tests(self, item):
        """Store tests information.

        Check if it's possible to merge it with collect-only info.
        pytest has this it already.
        """
        self.collected_tests.append(item.nodeid)

    def parse_config(self, root=None, path=""):
        """Parse xml configs into a dictionary.

        Key: the element path + attributes.
        """
        # Create pytest.elem_dict with all the element path + attributes
        main_root = self._get_xml_root()
        if root is None:
            root = main_root
        for child_root in root:
            # update the current path
            if path != "":
                elem_path = "%s/%s" % (path, child_root.tag)
            else:
                elem_path = "%s" % (child_root.tag)

            text = main_root.findtext(elem_path)
            if text is not None and "\n" not in text and "include_xml" not in elem_path:
                # Add an entry for the text
                self._elem_dict[elem_path] = "%s=%s" % (
                    elem_path,
                    text if text is not None else '""',
                )
            if child_root.attrib != {}:
                for key, value in child_root.attrib.items():
                    # Add an entry for the attributes
                    self._elem_dict[elem_path + "(" + key + ")"] = "%s(%s)=%s" % (
                        elem_path,
                        key,
                        value,
                    )

            self.parse_config(child_root, elem_path)

    def get_main_config(self):
        """Get main configuration for the test."""
        return self.xml_file_lists + sorted(self._elem_dict.values())

    def collect_test_configs(self):
        """Collect test json configs."""
        values = self.get_main_config()
        tests_array = []
        for test in self.collected_tests:
            tests_array.append({"name": test})
        json_content = {"letp": {"tests": [{"main_config": values}] + tests_array}}
        json_content["test_collected"] = len(tests_array)
        if "L_ReinitTest" in str(tests_array):
            QA_ROOT = os.getenv("QA_ROOT")
            TEST_CHOICE = os.getenv("TEST_CHOICE", None)
            TC_json_path = f"{QA_ROOT}/testCampaign/{TEST_CHOICE}.json"
            if TEST_CHOICE:
                try:
                    cmd = f"letp run {TC_json_path} --collect-only"
                    rsp = os.popen(cmd).read()
                    pattern = re.search(r"test_collected': (?P<number>\d+)", rsp)
                    number_TC = int(pattern.group("number"))
                    json_content["test_collected_total"] = number_TC + 1
                except:
                    swilog.info("Cannot open JSON file with the TEST_CHOICE")
            else:
                json_content["test_collected_total"] = len(tests_array)
        # Do not suppress this print
        print(pprint.pformat(json_content))
        self.test_base_reports = json_content

    def is_random(self):
        """Read the config dict to see if the test run should be random."""
        return self._elem_dict.get("test_run/randomize")

    @staticmethod
    def read_default_config(session):
        """Read the default configuration file."""
        old_path = os.getcwd()
        if "LETP_TESTS" in os.environ:
            os.chdir(os.environ["LETP_TESTS"])
        cmd_line_configs = session.config.getoption("--config")
        default_target_config = TestConfig.build_default_config(cmd_line_configs)
        # Go to previous path
        os.chdir(old_path)
        return default_target_config

    @staticmethod
    def get_testCfg(name):
        """Get Test specific configuration if there is any in json."""
        test_list = TestConfig.test_list

        if test_list == []:
            return []

        raw_name = name.split("[")[0]
        for i, test in enumerate(test_list[0]):
            if raw_name in test[0]:
                ret = [test[1]]
                # In case a test function is called several times but with
                # several configurations,
                # delete this one because it should not be used next time.
                # For the moment it is not applicable to parametrized tests
                # unless you specify
                # all the parametrized tests one by one in the json such as:
                # "name": "legato/foo.py::my_test_function[param1]"
                # "name": "legato/foo.py::my_test_function[param2]"
                if "[" not in name or ("[" in name and "[" in test[0]):
                    swilog.warning("Remove config of {}".format(test_list[0][i]))
                    del test_list[0][i]
                else:
                    # Check it is the only parametrized test.
                    # If not, assert to tell that
                    # having several tests with several configs are not supported
                    # Get all the tests
                    all_tests = [
                        test[0]
                        for i, test in enumerate(test_list[0])
                        if raw_name in test[0]
                    ]
                    assert len(all_tests) == 1, (
                        "If you want to call the test %s "
                        "several times with several " % name
                        + "configurations in the json file, you must specify all "
                        "the parametrized "
                        'tests in the json file: \n"name": '
                        '"legato/foo.py::my_test_function[param1]" '
                        '\ninstead of \n"name": "legato/foo.py::my_test_function""'
                    )
                return ret
        # In the case the test in the json file is not exactly
        # the run test (folder, module name or Atlas .aut)
        swilog.warning(
            "Did not find the test '%s' in the json file. "
            "No specific configuration can be applied." % name
        )
        return []

    @staticmethod
    def get_marker_config(item):
        """Get the marker configs pytest.mark."""
        marker = item.get_closest_marker("config")
        marker_configs = []
        if marker is not None:
            swilog.debug("use extra config file %s " % marker.args[0])
            marker_configs = [item.get_closest_marker("config").args[0]]
        return TestConfigsParser(marker_configs)

    @staticmethod
    def get_configs_in_json(item):
        """Get configs in json file if any."""
        test_name = item.name
        configs_in_json = TestConfig.get_testCfg(test_name)
        return TestConfigsParser(configs_in_json)

    @staticmethod
    def build(item):
        """Process test config markers.

        Create in config/test the xml files you need to your test (and only
        related to your test) such as server address, firmware versions, ...
        A test can be linked to a configuration file with the pytest markers.
        No need to declare it in json or in the command line.
        For a specific test function use:

        .. code-block:: python

            @pytest.mark.config("config/test/ima.xml")
            def L_xxx():

        To associate an xml file to a whole python module, use::

            pytestmark = pytest.mark.config("config/test/ima.xml")

        The order is very important as the last read
        parameters override the others
        if they already exists. The order is:
        Static test configuration:
        - default_config file first to have the testbench.xml in first position
        - the configurations needed by the test (config markers)
        - the files indicated in the json
        Dynamic test configuration:
        - the configuration.xml of the command line
        - the parameters key=value
        """
        marker_configs = TestConfig.get_marker_config(item)
        configs_in_json = TestConfig.get_configs_in_json(item)
        default_cfg = item.session.default_cfg

        if not (configs_in_json.is_valid() or marker_configs.is_valid()):
            return default_cfg

        test_config = TestConfig(default_cfg.cmd_line_cfgs)
        test_config.create_cfg_xml(
            [TestConfig.default_cfg_file]
            + marker_configs.get_xml_configs()
            + configs_in_json.get_xml_configs()
        )
        cmd_line_configer = TestConfigsParser(default_cfg.cmd_line_cfgs)
        # Values can be overriden with format: key=value in
        # the --config arg from the command
        # line or the json option
        test_config.apply_extra_config(
            configs_in_json.get_all_set_configs()
            + marker_configs.get_all_set_configs()
            + cmd_line_configer.get_all_set_configs()
        )
        # Store elements info
        # A json file corresponding to the xml configuration
        # will be generated after collection.
        test_config.parse_config()
        test_node = test_config.get().getroot()
        test_node.text = item.nodeid
        return test_config

    @staticmethod
    def build_default_config(cmd_line_cfgs=None):
        """Build config from user config parameters and default config xml."""
        # Create configuration. Add the default config file first
        cmd_line_cfgs = cmd_line_cfgs if cmd_line_cfgs is not None else []
        target_config = TestConfig(cmd_line_cfgs)
        print(
            "Read default configuration from %s \n%s"
            % (TestConfig.default_cfg_file, pprint.pformat(cmd_line_cfgs))
        )
        cmd_line_configer = TestConfigsParser(cmd_line_cfgs)
        target_config.create_cfg_xml(
            [TestConfig.default_cfg_file] + cmd_line_configer.get_xml_configs()
        )
        # Values can be overriden with format: key=value in the --config arg
        target_config.apply_extra_config(cmd_line_configer.get_all_set_configs())
        target_config.parse_config()
        return target_config
