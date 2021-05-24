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

3. Command to run LeTP test on Command Prompt Windows::

    python pytest_letp\tools\letp.py run <PATH_TO_THE_TEST_SCRIPT::TEST_CASE> --config 'module\slink1(used)=1' --config 'module\slink1\name='<DEVICE_CLI_PORT>' --config 'module\slink2(used)=1' --config 'module\slink2\name=<DEVICE_AT_PORT>'
