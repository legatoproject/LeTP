###############
Windows support
###############

.. contents:: Table of Contents
    :depth: 3

Required Tools
--------------

Windows Command Prompt.

`Git Bash on Windows <https://gitforwindows.org/>`_

Python 3.6+.

Download, install and setup environment for Git:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
1. Download and install `Git <https://gitforwindows.org/>`_

2. Add Git paths to Environment Variables::

    setx path /m "%path%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin;C:\Program Files\Git\mingw64\bin"

Download and setup the framework:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
1. Get the framework with git clone::

    git clone https://github.com/legatoproject/LeTP.git

2. Config Windows LeTP environment::

    cd letp
    configLeTP.bat

3. Command to run LeTP test on Command Prompt Windows:

- Use the module's com port::

    python pytest_letp\tools\letp.py run <PATH_TO_THE_TEST_SCRIPT::TEST_CASE>  --config module/name=NAME_OF_MODULE --config module/slink1(used)=1 --config module/slink1/name=<DEVICE_CLI_PORT> --config module/slink2(used)=1 --config module/slink2/name=<DEVICE_AT_PORT>

- Use SSH::

    python pytest_letp\tools\letp.py run <PATH_TO_THE_TEST_SCRIPT::TEST_CASE> --config module/name=NAME_OF_MODULE  --config module/ssh(used)=1 --config module/ssh/ip_address=IP_ADDRESS

Also, you can edit that configuration at pytest_letp\config\target.xml before running tcs. Then you can run tcs with the command::

    python pytest_letp\tools\letp.py run <PATH_TO_THE_TEST_SCRIPT::TEST_CASE>
