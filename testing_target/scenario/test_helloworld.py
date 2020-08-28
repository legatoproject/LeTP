"""!@package test_helloworld Test hello world."""
import os
import pytest
import pexpect

__copyright__ = "Copyright (C) Sierra Wireless Inc."

# The application name and path should be declared at the beginning of
# the python test file APP_NAME = "helloWorld"
# so that those will be used by the fixture app_leg.
APP_NAME = "helloWorld"
APP_PATH = os.path.join(os.environ["LEGATO_ROOT"], "apps/sample/helloWorld")


@pytest.mark.usefixtures("app_leg")
def test_helloworld(legato, logread):
    """!Check that "Hello, world" is printed in the legato logs.

    @param app_leg Pytest fixture pytest_legato.app_leg <br>
                    It clears the logs, builds and installs the application
                    referred by APP_NAME and located at APP_PATH.
                    At the end, it cleans the application build on host
                    and removes the application on target.
    @param legato  Pytest fixture pytest_legato.legato <br>
                    It supplies some useful Legato functions, such as
                    starting an application.
    @param logread Pytest fixture pytest_legato.logread <br>
                    It reads and expects some patterns in the Legato logs.

    Test code steps explanation:

    - Before calling:
        - Initialization of the communication links by the fixture pytest_target.target.
          The app_leg, legato, logread fixtures all uses pytest_target.target so that
          the fixture will be called before these three fixtures.
        - Clear of the target log by app_leg fixture
        - Build and install of the HelloWorld application by app_leg

    - This function executing:
        - Start of the HelloWorld application with legato.start
        - Check that the string "Hello, world" is received in the logs
            with logread.expect

    - After calling:
        - Removal of the application and clean of the application build on
        host by the app_leg cleanup
    """
    # Stop the app if it is running
    if legato.is_app_running(APP_NAME):
        legato.stop(APP_NAME)

    # Start app
    legato.start(APP_NAME)

    error_msg = "No 'Hello, world' in the logs"
    cmd_timeout = 10

    _id = logread.expect(["Hello, world", pexpect.TIMEOUT], cmd_timeout)
    # id is 0 if the pattern "Hello, world" is found. Id is 1 if timeout
    assert _id == 0, error_msg
