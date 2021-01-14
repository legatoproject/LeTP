"""Legato related fixtures.

Pytest fixtures for Legato system or applications.
"""
import os
import types

import pytest

from pytest_letp.lib import app
from pytest_letp.lib import modules

__copyright__ = "Copyright (C) Sierra Wireless Inc."


# Any operation related to LEGATO_ROOT should be here.
def app_leg_main(request, target, read_config, tmpdir):
    """Fixture to build, install and clean a Legato application.

    The application name is given in the python module: APP_NAME_xxx
    where xxx is the name of the test ie,
    APP_NAME_test_L_AtomicFile_Operation_0012     APP_NAME if the
    application is shared for all the tests
    """
    assert read_config
    target_type = target.target_name
    try:
        # Try to download the application of a particular test
        app_name = getattr(
            request.module, "APP_NAME_%s" % request.node.name.split("[")[0]
        )
        app_path = getattr(
            request.module, "APP_PATH_%s" % request.node.name.split("[")[0]
        )
    except AttributeError:
        try:
            # Download generic application
            app_name = request.module.APP_NAME
            app_path = request.module.APP_PATH
        except AttributeError:
            assert 0, "APP_NAME and APP_PATH must be defined in the python test file"

    try:
        # get make options if they exist
        make_options = getattr(
            request.module, "MAKE_OPTIONS_%s" % request.node.name.split("[")[0]
        )
    except AttributeError:
        try:
            # get make options if they exist
            make_options = request.module.MAKE_OPTIONS
        except AttributeError:
            # No option defined
            make_options = ""

    # Go to temp directory
    os.chdir(str(tmpdir))
    app.make(target_type, app_name, app_path, option=make_options)
    app.clear_target_log(target)
    app.install(target_type, target.target_ip, app_name)
    return app_name


@pytest.fixture()
def app_leg(request, target, read_config, tmpdir):
    """Fixture to build, install and clean a Legato application.

    This fixture builds and installs the Legato application.

    At the end, remove the application and clean the build on host.
    The application name and path should be declared at
    the beginning of the python test file:

    .. code-block:: python

        APP_NAME_xxx = "foo"             # Note:  The ".adef" will be appended.
        APP_PATH_xxx  = "yy/zz/..."      # Path of the adef.
            By default, the adef file is APP_NAME_xxx.adef.
                                        #where xxx is the name of the test.

        APP_NAME_L_AtomicFile_Operation_0001 = "atomOpen"
        APP_PATH_L_AtomicFile_Operation_0001 = \
"%s/atomicFileAccess/atomOpen"% QA_RUNALL_ROOT
        APP_NAME_L_AtomicFile_Operation_0002 = "atomOpen2"
        APP_PATH_L_AtomicFile_Operation_0002 = \
"%s/atomicFileAccess/atomOpen2"% QA_RUNALL_ROOT


    Do not indicate the application name in APP_NAME and APP_PATH
    if you have only one application or if the application is shared
    for all the tests in the python file.
    This will be the default application to build and install.
    The search rule is the following for a test:
    first find APP_NAME_xxx. If it was not found, search for APP_NAME

    .. code-block:: python

        APP_NAME = "sbBasicTest"
        APP_PATH = QA_RUNALL_ROOT + "/sandbox"
    """
    app_name = app_leg_main(request, target, read_config, tmpdir)
    yield
    app.clean(target, app_name)


@pytest.fixture()
def app_leg2(request, target2, read_config, tmpdir):
    """App Fixture for a second target (target2).

    It can build, install and clean a Legato application.

    | The application name is given in the python module: APP_NAME_xxx
    | where xxx is the name of the test ie,
    | APP_NAME_test_L_AtomicFile_Operation_0012 APP_NAME if the
    | application is shared for all the tests
    """
    app_name = app_leg_main(request, target2, read_config, tmpdir)
    yield
    app.clean(target2, app_name)


def _logread_main(target):
    """Fixture to get the logread data on a separate ssh link.

    :returns pexpect object on ssh_logread link
    :returns log_off, log_on and flush functions added
    """
    # pylint: disable=unused-argument
    # Add a ssh link to the target
    target.links["ssh_logread"] = modules.ModuleLink(target, "ssh_logread")
    target.links["ssh_logread"].init_cb = target.init_ssh_link
    target.links["ssh_logread"].add_alias("ssh_logread")
    target.ssh_logread.login()
    save_logfile = target.ssh_logread.logfile

    def log_off(self):
        """Turn off the ssh_logread stdout."""
        target.ssh_logread.logfile = None

    def log_on(self):
        """Turn on the ssh_logread stdout."""
        target.ssh_logread.logfile = save_logfile

    def flush(self):
        """Read all the data in the pexpect buffer."""
        target.ssh_logread.expect(r".+")

    target.ssh_logread.sendline("logread -f")
    target.ssh_logread.log_off = types.MethodType(log_off, target)
    target.ssh_logread.log_on = types.MethodType(log_on, target)
    target.ssh_logread.flush = types.MethodType(flush, target)


@pytest.fixture(scope="function")
def logread(target):
    """Read logs from the target.

    Get the logread data on a dedicated SSH link.
    It runs a "logread -f" on a ssh pexpect link.
    Use logread.expect to expect some patterns.

    3 functions added to the pexpect interface (run, expect, send...):

    - log_off(): deactivate the logs on the logread SSH link
    - log_on(): activate the logs on the logread SSH link (default)
    - flush(): flush the current pexpect buffer. \
        It does not delete the logs on target.

    .. code-block:: python

        def L_comp_0001(target, logread):
            # Deactivate the output of logread
            logread.log_off()
            # Wait for "Read event" in the logs
            id = logread.expect([pexpect.TIMEOUT, "Read event"], 30)
            assert id == 1, "TIMEOUT: 'Read event' not received"
            # flush the log buffer
            logread.flush()

    .. note::

        When created, the logread link is added to the
        target fixture. Another way to address is is to use target.logread.
    """
    _logread_main(target)
    yield target.ssh_logread


@pytest.fixture(scope="function")
def logread2(target2):
    """Read logs from the target2."""
    _logread_main(target2)
    yield target2.ssh_logread


@pytest.fixture(scope="function")
def ssh2(target):
    """Fixture to open a second ssh link.

    Returns: pexpect object on ssh link
    Open a second SSH connection
    It is the same interface as target.ssh

    .. code-block:: python

        def L_comp_0001(target, ssh2):
            # Send a command on the second SSH link
            ssh2.run("ls /")
    """
    target.links["ssh2"] = modules.ModuleLink(target, "ssh2")
    target.links["ssh2"].init_cb = target.init_ssh_link
    target.links["ssh2"].add_alias("ssh2")
    # Add a ssh link to the target
    target.ssh2.login()
    yield target.ssh2


@pytest.fixture(scope="function")
def legato(target):
    """Fixture to manage legato commands.

    Access to the functions related to Legato.
    See the :ref:`fixtures`.

    Example:
    Legato fixture usage

    .. code-block:: python

        def L_leg_0001(target, legato):
            assert legato.is_app_exist("my_app") == True, \
                "The application does not exist"
            legato.start("my_app")

    .. note::

        It is the same functions as in the library app.py.
        The advantage is that the function prototypes are
        simplified (no need to indicate target, target_type and target_ip)

    Build, install and clean

    :py:func:`~lib.app.make`

    :py:func:`~lib.app.install`

    :py:func:`~lib.app.make_install`

    :py:func:`~lib.app.install_legato`

    :py:func:`~lib.app.make_sys`

    :py:func:`~lib.app.install_sys`

    :py:func:`~lib.app.make_install_sys`

    :py:func:`~lib.app.remove`

    :py:func:`~lib.app.remove_all`

    :py:func:`~lib.app.clean`

    :py:func:`~lib.app.update_legato_cwe`


    Function related to the Legato applications

    :py:func:`~lib.app.is_app_exist`

    :py:func:`~lib.app.is_app_running`

    :py:func:`~lib.app.start`

    :py:func:`~lib.app.stop`

    :py:func:`~lib.app.runProc`

    :py:func:`~lib.app.restart`

    :py:func:`~lib.app.verify_app_version`

    :py:func:`~lib.app.version_validity`

    :py:func:`~lib.app.ssh_to_target`

    :py:func:`~lib.app.wait_for_system_to_start`

    :py:func:`~lib.app.get_current_system_index`

    :py:func:`~lib.app.get_current_system_status`

    :py:func:`~lib.app.get_legato_status`

    :py:func:`~lib.app.get_legato_version`

    :py:func:`~lib.app.restore_golden_legato`

    :py:func:`~lib.app.get_app_status`

    :py:func:`~lib.app.get_app_info`

    :py:func:`~lib.app.set_probation_timer`

    :py:func:`~lib.app.reset_probation_timer`

    :py:func:`~lib.app.full_legato_restart`

    :py:func:`~lib.app.check_current_system_info`

    Logging functionalities

    .. note::
        For the log functions,
        the recommended way is to use the
        :py:func:`~pytest_letp.pytest_legato.logread` fixture.

    :py:func:`~lib.app.clear_target_log`

    :py:func:`~lib.app.display_target_log`

    :py:func:`~lib.app.find_in_target_log`

    :py:func:`~lib.app.wait_for_log_msg`
    """
    yield app.LegatoManager(target)


@pytest.fixture(scope="function")
def legato2(target2):
    """Fixture to manage legato commands for target2.

    Similar to pytest_legato.legato, but it's for target2.
    """
    yield app.LegatoManager(target2)


## @}
