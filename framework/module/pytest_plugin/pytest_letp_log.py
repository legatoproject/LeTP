"""Handling letp log setup.

Have a tee to save the terminal output into a log file.
"""
import codecs
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from _pytest.config import Config


class Tee:
    """!Class to write in 2 different files.

    Typically replace sys.stdout/stderr to write both in stdout/stderr
    and in a log file.
    """

    def __init__(self, _fd1, _fd2):
        self.fd1 = _fd1
        self.fd2 = _fd2
        self.encoding = "ascii"

    def __del__(self):
        """Nothing to do here.

        _pytest/capture.py suspend and resume this object.
        setattr(sys, self.name, self._old) will call __del__.

        In this case, no need to delete the buffer because we
        will resume later.
        """

    def _write(self, fd, text):
        try:
            t = str(text)
            fd.write(t)
        except BlockingIOError as ex:
            # Retry writting but deduce the characters already written
            self._write(fd, text[ex.characters_written :])
        except UnicodeEncodeError:
            t = text.encode(self.encoding, errors="replace")
            t = t.decode(self.encoding)
            fd.write(t)
        except UnicodeDecodeError:
            t = text.decode(self.encoding, errors="replace")
            fd.write(t)

    def write(self, text):
        """Write to the file."""
        self._write(self.fd1, text)
        self._write(self.fd2, text)

    def flush(self):
        """Clean out the file."""
        self.fd1.flush()
        self.fd2.flush()

    def isatty(self):
        """Return true always."""
        assert self
        return True


class LogFileNameBuilder:
    """!Build a log file name."""

    def __init__(self, file_or_dir):
        self.file_or_dir = file_or_dir

    @staticmethod
    def _get_underscore_name(path):
        if path:
            if "::" in path:
                path = path.split("::")[0]
            return os.path.basename(path).replace(".", "_")
        return ""

    def get_named_tests(self):
        """Get any extra tests in the pytest args and split the test name."""
        named_tests = []
        test_folder_exists = False
        for path in self.file_or_dir:
            if "test_dummy.py" in path:
                # Ignore the dummy test.
                continue
            if ".py" in path or ".json" in path:
                named_tests.append(self._get_underscore_name(path))
            else:
                test_folder_exists = True
        return named_tests, test_folder_exists

    def _get_base_log_name(self):
        named_tests, test_folder_exists = self.get_named_tests()
        if test_folder_exists:
            # mixed test path types.
            return "letp"
        return "_".join(named_tests)

    def build(self):
        """Build a log file path based on input names."""
        default_log_file = self._get_base_log_name()
        log_dir_name = "log"

        dt = datetime.now()
        timestamp = "%02d%02d%02d_%02d%02d%02d_%06d" % (
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
        )
        log_file_name = "%s_%s.log" % (timestamp, default_log_file)
        log_file = os.path.join(log_dir_name, log_file_name)
        return log_file


def _build_log_file_name(args):
    """Create the log file name from the test given to the script."""
    if not args.log_file:
        test_log_file_name_builder = LogFileNameBuilder(args.file_or_dir)
        log_file = test_log_file_name_builder.build()
        return log_file
    else:
        return args.log_file


class LeTPTerminalLogManager:
    """It manages the Tee object to write terminal logs into a file."""

    def __init__(self, log_file_path) -> None:
        self.outputlog, self.stderrsav, self.stdoutsav = None, None, None
        self.log_file_path = log_file_path
        self._init_logging(log_file_path)

    def _init_logging(self, log_file):
        """Begin logging."""
        # Ensure the "log" directory exists
        Path(os.path.dirname(log_file)).mkdir(parents=True, exist_ok=True)
        self.stderrsav = sys.stderr
        self.stdoutsav = sys.stdout
        self.outputlog = codecs.open(log_file, "w", encoding="utf-8")
        # # Write also sdtout/stderr in the log file
        sys.stderr = Tee(self.stderrsav, self.outputlog)
        sys.stdout = Tee(self.stdoutsav, self.outputlog)
        print("Create the log file %s" % log_file)

    def restore(self):
        """Restore the system buffer."""
        print("!!!!! Logs can be found here %s!!!!!" % self.log_file_path)
        self.outputlog.flush()
        # Somehow close triggers Exception ignored in sys.unraisablehook
        # We are relying on python to close the file after the session.
        # self.outputlog.close()
        sys.stderr = self.stderrsav
        sys.stdout = self.stdoutsav


log_manager_key = "LeTPTerminalLogManager"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_load_initial_conftests(early_config, args):
    """Put this the first hook implementation.

    Even earlier than CaptureManager and start_global_capturing.
    """
    assert args
    known_args = early_config.known_args_namespace
    log_file = _build_log_file_name(known_args)
    known_args.log_file = log_file
    log_manager = LeTPTerminalLogManager(log_file)
    early_config._store[log_manager_key] = log_manager
    early_config.pluginmanager.register(log_manager)
    yield


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: Config) -> None:
    """Unconfigure the terminal logger."""
    log_manager = config._store.get(log_manager_key, None)
    if log_manager:
        log_manager.restore()
        del config._store[log_manager_key]
        config.pluginmanager.unregister(log_manager)
