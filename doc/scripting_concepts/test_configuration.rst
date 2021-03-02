.. _test_configuration:

###################
Test configurations
###################

There are four configuration ways.

- Configuration xml file
- module/slink2(used)=1 in test campaign json
- pytest.mark.config("$LETP_TESTS/scenario/config/target_wp750x.xml")
- letp command with ``--config module/slink2(used)=1``

Configuration files
-------------------

The configuration files are in xml format and located in $LETP_TESTS/config.

Select a configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are 2 possibilities to use a configuration file:

    - The configuration files can be passed as an argument of letp with option ``--config``. A specific parameter can also be set with this option.

    - They can also be added in testbench.xml in the include_xml tag.

Priority of the files
^^^^^^^^^^^^^^^^^^^^^

All the files declared with --config override the values in the default file testbench.xml (and all the included files).
Priorities of configuration options (From highest to lowest priority):

    1. Environment variables (TARGET_IP, TARGET_SSH_PORT)
    2. Command line using ``--config``
    3. XML files

Common files
------------

testbench.xml
^^^^^^^^^^^^^

LeTP loads a default file named testbench.xml in $LETP_TESTS/config. By default, it includes host.xml (host IP, NFS, ...) and target.xml (module name, SSH, UART config...).
You can add more files, or comment all the files to only rely on the command line parameters.

 `testbench.xml <../../../../test/config/testbench.xml>`_

target.xml
^^^^^^^^^^

.. list-table::
    :header-rows: 1

    * - parameter
      - Description

    * - module/name
      - module name (wp7502, wp7607, ...). It should correspond to a file in config/module/specific.

    * - module/ssh/ip_address
      - ip address of the target

- At least change the value of the module name (wp7502, wp7607, ...). It should correspond to a file in config/module/specific.
- Change used=0 to used=1 for all the communication links you want to use (ssh, serial link 1 or 2).

When available, SSH is the default link.

- For ssh, set the network interface (eth0 or usb0) as well as the ip address

- For slink, /dev/ttyxxx or IP address+port (for telnet access on Moxa eth to uart) are supported.


Note for linux For Linux Legato users:

The eth ip address can change after reboot because the mac address changes.
There are several solutions:

-    Set the mac address with module/ssh/mac_add
-    If you set it to "auto", it will be set to an address based on the FSN of your module. It could be done once.
-    Use slink1 with SSH (recommended).
-    The new ip address will be read and eth/ecm configuration will be done by uart at init and after each reboot.

`target.xml <../../../../test/config/target.xml>`_

host.xml
^^^^^^^^

Specify the host ip address, interface, root password,  nfs mount, ... if needed in the test.

`host.xml <../../../../test/config/host.xml>`_

test_run.xml
^^^^^^^^^^^^
We may want to have some run time setting shared by test.
e.g. test campaign id, context id, host name, etc.

`test_run.xml <../../../../test/config/test_run.xml>`_

Specific test files
^^^^^^^^^^^^^^^^^^^

:meth:`Configs from Marker. <pytest_letp.pytest_test_config.TestConfig.build>`

xml inclusion
-------------

:meth:`XML inclusion <pytest_letp.pytest_test_config.TestConfig.create_cfg_xml>`

Parameter access
----------------

See the :meth:`read_config fixture <pytest_letp.__init__.read_config>` to access the xml tree.
