###############
Getting Started
###############

`Getting started <https://legato.io/quickstart>`_ with Legato

Prerequisite
^^^^^^^^^^^^

The Legato development environment must be functional in order to build the helloWorld application.

1. Install Toolchain:

    Toolchains include all the tools and libraries needed to build the runtime environment for a target device. The toolchain is specific to the Linux Distribution and the Module so each module that you are building must have its own toolchain installed. `Install the Toolchain  <https://docs.legato.io/20_04/basicBuildToolchain.html>`_ can be downloaded from your vendor, or are automatically installed and configured with `Leaf Workspace Manager <https://docs.legato.io/latest/confLeaf.html>`_

2. Add environment variable:

    Set the path of toolchain for different platform into environment variable, so that source code for specific hardware can be compile properly.
    Example toolchain for wp76xx::

        export WP76XX_TOOLCHAIN_DIR=/opt/swi/SWI9X07Y_02.18.06.00/sysroots/x86_64-pokysdk-linux/usr/bin/arm-poky-linux-gnueabi

3. Make legato for Target:

    The Legato build tools rely on a Linux environment to make the system and app images for your target.
    Go to your legato repository::

        cd legato

    Run make to build the framework for the target::

        make wp76xx // Replace wp76xx with the target type ID you're building (eg: wp77xx, wp85,...).

    Then you need to set up your shell environment to use the Legato command-line tools::

        bin/legs

4. Install and configure LeTP as described in :ref:`installation`.

Test scripts creation
^^^^^^^^^^^^^^^^^^^^^

1. Go to your test repository::

        cd $LETP_TESTS

2. Copy the tutorial test_helloworld source file (letp/testing_target/scenario/test_helloworld.py) to $LETP_TESTS

.. literalinclude:: ../testing_target/scenario/test_helloworld.py

Test execution
^^^^^^^^^^^^^^

1. Set the name of your module in config/target.xml:

        .. code-block:: xml

                <name>wp7607</name>


2. Set SSH setting

    The SSH link will be used for the test.
    The serial link is optional but if SSH and serial link are
    used together, the serial link is used to determine the ip
    address at startup or after each reboot.
    This is useful when the IP address changes after reboot.
    Moreover, it removes the firewall rules at startup.

    Always in config/target.xml, set at least the target ip
    address in the SSH section. Activate it by setting "used=1"

    SSH settings:

        .. code-block:: xml

                <ssh used="1" main_link="1">
                    <ip_address>192.168.2.2</ip_address>
                    <network_if>ecm0</network_if>

3. Set up Serial link for CLI in slink1 section

    Fill the port name (/dev/ttyxxx), the baudrate in speed (default 115200).
    Activate it by setting "used=1".

    Serial settings:

        .. code-block:: xml

                <slink1 used="0">
                    <name>/dev/ttyS1</name>
                    <rtscts>0</rtscts>
                    <speed>115200</speed>
                </slink1>

    Ssh is used to send commands by default.

4. Start the test::

    letp run $LETP_TESTS/test_helloworld.py

5. The result is displayed at the end with the number of PASSED/FAILED/ERROR. ERROR means that the test failed at setup or in the teardown.
   The name of the created log file is also found in the last lines.

Copyright (C) Sierra Wireless Inc.

