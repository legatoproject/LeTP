.. _installation:

############
Installation
############

.. contents:: Table of Contents
    :depth: 3

Get LeTP from Github
--------------------
Standalone installation
^^^^^^^^^^^^^^^^^^^^^^^
These steps are for getting a standalone LeTP:

Get the framework with git clone::

    git clone git://github/Legato/LeTP

Then create (see :ref:`Create test repository<create_test_repo>`) or get a test repository.
And configure your environment see :ref:`the configuration section.<env_configuration>`

Installation with repo
^^^^^^^^^^^^^^^^^^^^^^

Follow the instructions for Legato "Clone for Github":
`Instructions <https://docs.legato.io/latest/basicBuildLegato.html#basicBuildLegato_Download>`_

But add the groups default and letp in the repo command with "-g"::

    repo init -u git://github.com/legatoproject/manifest -m legato/releases/17.07.1.xml -g letp,default

Then configure your environment see :ref:`the configuration section.<env_configuration>`

.. _create_test_repo:

Create test repository
^^^^^^^^^^^^^^^^^^^^^^

If a new test repository is needed, copy the content of test/host in it.::

    # Copy test/host in a new test directory (my_tests)
    cp -r LeTP/test/host <PATH>/my_tests

.. _env_configuration:

Environment configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

Source LeTP configuration scripts to configure LETP_TESTS variable (test scripts location) and add LeTP binary to the system path.
LETP_TESTS can also be given as the first argument of configLeTP.sh::

    # Go to the LeTP root directory
    cd legato/apps/leTP
    or
    cd LeTP

    # Without argument, configLeTP.sh will ask you for the LeTP test path (first conftest.py or pytest.ini):
    source configLeTP.sh
                Usage: source configLeTP.sh [path of LETP tests]
                Enter your root test directory (<path-to-your-root-test-directory>):
                Set LETP_TESTS to <PATH>/qa/letp
                Create symbolic link for LeTP

    # or set directly the path of the LeTP tests as an argument of configLeTP:
    source configLeTP.sh <PATH>/qa/letp
                Usage: source configLeTP.sh [path of LETP tests]
                Set LETP_TESTS to <PATH>/qa/letp
                Create symbolic link for LeTP

Install Prerequisite packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Python 3.6+. Check with::

    python3 --version

Install python modules in requirements.txt required by LeTP.::

    pip3 install -r requirements.txt


In order to communicate with the device, the host user needs the necessary permissions to read and write to the /dev/ttyXYZ device. On most distributions the user just needs to be in the 'dialout' group.::

    sudo usermod -a -G dialout $USER

Installation with leaf
----------------------

The benefits to use leaf are:

* to install Legato/Legato tests/LeTP in one operation.
* after installation, LeTP is already configured and working. No extra steps needed. LETP_TESTS points to the root directory of the tests.
* you can change easily the Legato version you use by changing your profile

The steps:

1. Install leaf. See leaf Reference Guide

2. Set the remotes::

    leaf remote add getlegato-all http://github/leaf/index.json --insecure

3. Create a folder which will be your leaf workspace and create a profile with both legato tests and a Legato SDK::

    leaf setup -p legato-qa-src -p int-wp76_18.08.0.rc1 MY_NEW_PROFILE

4. Go the the folder legato-qa-src and start a leaf shell::

    cd legato-qa-src
    leaf shell

5. Now letp can be called inside the leaf workspace::

    letp run your_test.py

6. You can "repo sync" your repository as usual::

    repo sync

