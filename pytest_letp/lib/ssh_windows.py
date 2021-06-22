"""SSH communictaion link for windows environment."""
import os
from contextlib import suppress
import socket
import re
import paramiko
from paramiko_expect import SSHClientInteraction
from pexpect import TIMEOUT
import swilog
from pytest_letp.lib.com_exceptions import ComException
from pytest_letp.lib.com import QctAttr

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class TargetSSH:
    """Class to connect with ssh based on Paramiko."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=no-member
    def __init__(self, server, username="root", password="", port=22):
        home = os.path.expanduser("~")
        self.pkey_filename = os.path.join(home, ".ssh", "id_rsa")
        # used to match the command-line prompt
        self.PROMPT = QctAttr().prompt
        self.timeout = 10
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.chan = ""

    def get_ssh_key(self):
        """Fetch locally stored SSH key."""
        ssh_key = None
        try:
            ssh_key = paramiko.RSAKey.from_private_key_file(self.pkey_filename)
            swilog.debug(f"Found SSH key at self {self.pkey_filename}")
        except paramiko.auth_handler.SSHException as e:
            swilog.error(e)
        return ssh_key

    def login(self):
        """Log user into the given server."""
        result_flag = False
        try:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.password is None:
                self.ssh.connect(
                    self.server,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                )
            else:
                with suppress(paramiko.ssh_exception.AuthenticationException):
                    self.ssh.connect(
                        self.server,
                        username=self.username,
                        password=self.password,
                        port=self.port,
                        pkey=self.get_ssh_key(),
                    ).auth_none("root")
                self.ssh.get_transport().auth_none("root")
            self.chan = SSHClientInteraction(self.ssh, self.timeout, display=True)
            swilog.info("Connected to {} {}".format(self.server, self.port))
        except paramiko.auth_handler.AuthenticationException as e:
            swilog.error(
                "Authentication failed, please verify your credentials {}".format(e)
            )
        except ComException as e:
            swilog.error("Could not establish SSH connection: {}".format(e))
        else:
            result_flag = True
        return result_flag

    def logout(self):
        """Send exit to the remote shell."""
        self.ssh.send("exit")
        self.close()

    def close(self):
        """Close connection to server."""
        try:
            self.ssh.close()
            swilog.info("Connection to {} closed.".format(self.server))
        except paramiko.SSHException as e:
            swilog.warning("Can't close ssh session !!! \n {}".format(e))

    def is_at_le_prompt(self, timeout=-1):
        """Match the next shell prompt."""
        if timeout == -1:
            timeout = self.timeout
        i = self.ssh.expect([self.PROMPT, TIMEOUT], timeout=timeout)
        if i == 1:
            return False
        return True

    def send(self, command):
        """Run a command, check the exit status by default."""
        try:
            self.chan.send(command)
        except paramiko.SSHException as e:
            swilog.debug("Can't send command to module by {}".format(e))

    def expect(self, expect_msg, timeout=10):
        """Expect function from the pexpect library."""
        status = None
        try:
            status = self.chan.expect(expect_msg, timeout)
        except paramiko.SSHException as e:
            swilog.debug(
                "Cannot receive {} from the module by {}".format(expect_msg, e)
            )
        return status

    def execute_command(self, command, timeout=10, expect=None):
        """Execute a command on the remote host."""
        ssh_output = None
        result_flag = True
        try:
            swilog.info("Executing command --> {} \n".format(command))
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout)
            ssh_output = stdout.read()
            ssh_error = stderr.read()
            if ssh_error:
                swilog.debug(
                    "Problem occurred while running command"
                    "The error is {} ".format(ssh_error)
                )
                result_flag = False
            else:
                swilog.debug(
                    "Command {} execution completed successfully\n {} \n".format(
                        command, stdin
                    )
                )
                swilog.info(
                    "The output of the command is \n {}".format(
                        ssh_output.decode().strip()
                    )
                )
                if expect is not None:
                    rsp = re.search(expect, ssh_output.decode().strip())
                    return rsp
            self.close()

        except socket.timeout:
            swilog.debug("Command {} timed out.".format(command))
            self.close()
            result_flag = False
        except paramiko.SSHException:
            swilog.debug("Failed to execute the command {} !".format(command))
            self.close()
            result_flag = False
        return result_flag
