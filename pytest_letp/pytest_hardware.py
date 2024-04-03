"""Hardware fixtures.

Pytest fixtures for external test equipments and hardware.
"""
import pytest
from pytest_letp.lib import swilog
from pytest_letp.lib import controller

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.hookimpl
def pytest_configure(config):
    """Register numato and dli and returns controller."""
    controller.register("numato", controller.numato)
    config.controller = controller.get_ctrl()


# Any operation related to external target hardware should be here.
@pytest.fixture(scope="session")
def power_supply(request, read_config_default):
    """Get the power supply object if configured.

    Control target power via hardware switch in test.

    Example:
    Power supply management

    .. code-block:: python

        def L_ps_0001(power_supply):
            power_supply.cycle()
    """
    ret = None
    if read_config_default.findtext("hardware/power_supply") is not None:
        # get the power supply element
        xml_pwr_supply = read_config_default.find("hardware/power_supply")
        controller_type = xml_pwr_supply.findtext("type")
        ret = request.node.config.controller[controller_type](xml_pwr_supply)
    else:
        swilog.warning("No hardware configuration supplied: reboot target manually!")
    yield ret


## @}
