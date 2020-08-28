"""!@package runpy_adapter Have a adapter to use runpy for command.

Sometimes, we may want to call a test or file with __name__ ==
"__main__". This modules facilitates it.
"""
import sys
import shlex
import io
import runpy
import codecs
from contextlib import redirect_stdout

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def exec_command(command):
    """Execute command with sys.argv arguments."""
    commands = shlex.split(command)
    assert commands
    sys.argv = commands
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as sys_exit:
        # Some module returns sys.exit(0). e.g. letp.py
        if sys_exit.code != 0:
            raise


def run_python_with_command(command):
    """Run python file with args. Capture output.

    Using runpy because it can run python modules in modules' own namespaces.

    Not using subprocess because it cannot use debugger.

    Not using exec or execfile because it cannot use module's namespace.
    e.g. __file__ will be the caller script, not the script being called.
    """
    output = io.StringIO()
    with redirect_stdout(output):
        exec_command(command)
    return output.getvalue()


if __name__ == "__main__":
    # Adapter to support wrapped arguments.

    # e.g.
    # runpy_adapter.py test_report.py
    # "--json-path hl7802:wip --title \'Legato Test :: Nightly\'
    # --output /ws/delivery/test_report.html"
    # will become
    # test_report.py --json-path hl7802:wip --title 'Legato Test :: Nightly'
    # --output /ws/delivery/test_report.html
    #
    ESCAPED_WRAPPED_CMD = " ".join(sys.argv[1:])
    wrapped_cmd = codecs.decode(ESCAPED_WRAPPED_CMD, "unicode_escape")
    exec_command(wrapped_cmd)
