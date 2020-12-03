"""Shared test steps for both public and internal."""
import re
from pytest_letp.lib.modules import SwiModule
from pytest_letp.lib.versions import TargetVersions


def validate_legato_pattern(version_dict):
    """Validate legato pattern in SwiModule."""
    pattern = SwiModule.legato_pattern["parsed"]
    for version_str, expected_version in version_dict.items():
        match_obj = re.search(pattern, version_str)
        version = TargetVersions._match_version(match_obj)
        assert (
            version == expected_version
        ), "{} doesn't match the expected version: {}".format(version, expected_version)
