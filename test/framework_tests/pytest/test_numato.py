"""Test numato relay module.

Using mock module to simulate connections.
"""
# pylint:disable=no-member
import xml.etree.ElementTree as ET
from unittest.mock import Mock, MagicMock, patch

from pytest_letp.lib import controller
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


COMMAND_SENT = None


def io_send(cmd):
    """Mock for io send function."""
    global COMMAND_SENT
    COMMAND_SENT = cmd


def test_numato_on():
    """Test numato on method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert numato.inverted == 0
        assert numato.port_nb == 0
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.on()
        assert COMMAND_SENT == "relay on 0\r"


def test_numato_off():
    """Test numato off method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert numato.inverted == 0
        assert numato.port_nb == 0
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.off()
        assert COMMAND_SENT == "relay off 0\r"


def test_numato_alt_config_port():
    """Test setting an alternative port for numato on."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>1</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert numato.inverted == 0
        assert numato.port_nb == 1
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.on()
        assert COMMAND_SENT == "relay on 1\r"


def test_numato_alt_port():
    """Test passing in alternative port for numato on."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert numato.inverted == 0
        assert numato.port_nb == 0
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.on(1)
        assert COMMAND_SENT == "relay on 1\r"


def test_numato_map_ports_no_ports():
    """Test map ports functionality when no ports are in config."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        swilog.info(dir(numato))


def test_numato_map_ports_one_port():
    """Test map ports functionality when one relay port is set in config."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <ports>
        <power inverted="0">0</power>
    </ports>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert "power" in dir(numato)
        assert numato.power.inverted is False
        assert numato.power.port_nb == 0


def test_numato_map_ports_two_ports():
    """Test map ports functionality when two relay ports are set in config."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <ports>
        <power inverted="0">0</power>
        <sim inverted="1">1</sim>
    </ports>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert "power" in dir(numato)
        assert numato.power.inverted is False
        assert numato.power.port_nb == 0
        assert "sim" in dir(numato)
        assert numato.sim.inverted is True
        assert numato.sim.port_nb == 1


def test_numato_port_on():
    """Test numato port on method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <ports>
        <power inverted="0">0</power>
    </ports>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.power.on()
        assert COMMAND_SENT == "relay on 0\r"


def test_numato_alt_port_on():
    """Test numato alternative port on method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <ports>
        <power inverted="0">1</power>
    </ports>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.power.on()
        assert COMMAND_SENT == "relay on 1\r"


def test_numato_map_ports_gpio_not_used():
    """Test map ports functionality when gpio port is set but not used."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <gpio used="0">
        <ports>
            <gpio1 inverted="0">0</gpio1>
        </ports>
    </gpio>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert "gpio1" not in dir(numato)


def test_numato_map_ports_gpio_one_port():
    """Test map ports functionality when one gpio port is set in config."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <gpio used="1">
        <ports>
            <gpio1 inverted="0">0</gpio1>
        </ports>
    </gpio>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert "gpio1" in dir(numato)
        assert numato.gpio1.inverted is False
        assert numato.gpio1.port_nb == 0


def test_numato_map_ports_gpio_two_port():
    """Test map ports functionality when two gpio ports are set in config."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <gpio used="1">
        <ports>
            <gpio1 inverted="0">0</gpio1>
            <gpio2 inverted="1">1</gpio2>
        </ports>
    </gpio>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        assert "gpio1" in dir(numato)
        assert numato.gpio1.inverted is False
        assert numato.gpio1.port_nb == 0
        assert "gpio2" in dir(numato)
        assert numato.gpio2.inverted is True
        assert numato.gpio2.port_nb == 1


def test_numato_gpio_on():
    """Test numato port gpio method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <gpio used="1">
        <ports>
            <gpio1 inverted="0">0</gpio1>
        </ports>
    </gpio>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        numato.io.send = MagicMock(side_effect=io_send)
        numato.io.expect = Mock(return_value=">")
        numato.gpio1.on()
        assert COMMAND_SENT == "gpio set 0\r"


def test_numato_alt_gpio_on():
    """Test numato alternative gpio on method."""
    config_string = """
<power_supply>
    <type>numato</type>
    <port_nb>0</port_nb>
    <inverted>0</inverted>
    <com>
        <port>/dev/ttyACM0</port>
        <speed>115200</speed>
    </com>
    <gpio used="1">
        <ports>
            <gpio1 inverted="0">1</gpio1>
        </ports>
    </gpio>
</power_supply>
"""
    with patch("pytest_letp.lib.com.target_serial_at.open"):
        config = ET.fromstring(config_string)
        controller.numato.serial = Mock()
        numato = controller.numato(config)
        numato.gpio1.io.send = MagicMock(side_effect=io_send)
        numato.gpio1.io.expect = Mock(return_value=">")
        numato.gpio1.on()
        assert COMMAND_SENT == "gpio set 1\r"
