"""!@package pytest_hardware Hardware fixtures.

Pytest fixtures for external test equipments and hardware.
"""
import pytest
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


## @defgroup hardwareFixtureGroup The fixture related to test equipments and hardware
# Any operation related to external target hardware should be here.
# @{
@pytest.fixture(scope="session")
def power_supply(request, read_config_default):
    """!Get the power supply object if configured.

    Control target power via hardware switch in test.

    Example:
    ~~~~~~~~~~~~~{.py}
    def L_ps_0001(power_supply):
        power_supply.cycle()
    ~~~~~~~~~~~~~

    @ref controller.controller
    """
    ret = None
    if read_config_default.findtext("hardware/power_supply") is not None:
        # get the power supply element
        xml_pwr_supply = read_config_default.find("hardware/power_supply")
        controller_type = xml_pwr_supply.findtext("type")
        ret = request.node.config.controller[controller_type](xml_pwr_supply)
    else:
        swilog.warning(
            "No hardware configuration supplied: reboot manually your target!"
        )
    yield ret


## @}
