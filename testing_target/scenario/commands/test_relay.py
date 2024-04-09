"""AT-test samples.

Set of tests showing how to use the relay interface
"""
import pytest

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.fixture(autouse=True)
def reset_relay(power_supply):
    """Read relay state before test and reset at end."""
    starting_state = power_supply.state()
    yield
    if starting_state == "on":
        power_supply.on()
    else:
        power_supply.off()


# ======================================================================
# Test functions
# ======================================================================
def test_numato_on_off(power_supply):
    """Set relay off and on.

    Args:
        power_supply: fixture to communicate with the relay
    """
    power_supply.on()
    power_supply.off()
    assert power_supply.state() == "off"
    power_supply.on()
    assert power_supply.state() == "on"


def test_numato_cycle(power_supply):
    """Cycle relay.

    Args:
        power_supply: fixture to communicate with the relay
    """
    power_supply.on()
    assert power_supply.state() == "on"
    power_supply.cycle()
    assert power_supply.state() == "on"
