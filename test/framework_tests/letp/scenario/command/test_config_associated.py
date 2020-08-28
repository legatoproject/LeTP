"""Test associated config."""
import pytest

from test_config_stub import check_config

__copyright__ = "Copyright (C) Sierra Wireless Inc."

pytestmark = pytest.mark.config(
    "$LETP_TESTS/scenario/config/target_wp750x.xml,$LETP_TESTS/scenario/config/foo.xml"
)


def test_config_xml_module_scope(request, read_config):
    """Test with xml file associated for entire module."""
    check_config(request, read_config)
