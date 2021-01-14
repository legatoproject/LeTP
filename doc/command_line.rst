############
Command line
############

.. contents:: Table of Contents
    :depth: 3

LeTP command line
-----------------

.. code::

    letp run [LeTP options] test_selection [pytest options]

.. _letp_options:

LeTP options
^^^^^^^^^^^^
+-----------------------------+-------------------------------------------------------+
| LeTP Option                 | Description                                           |
+=============================+=======================================================+
| debug_level::               | swilog debug level from 0 to 4:                       |
|                             |  | 0    : DEBUG                                       |
|       -d or --dbg-lvl       |  | 1    : INFO (default)                              |
|                             |  | 2    : WARNING                                     |
|                             |  | 3    : ERROR                                       |
|                             |  | 4    : CRITICAL                                    |
+-----------------------------+-------------------------------------------------------+
| Log file::                  | Give the path and the name of the log file.           |
|                             | A timestamp will be automatically prepended.          |
|   --log-file                | If not set, the default log file will be::            |
|   path_and_name_of_log_file |                                                       |
|                             |     log/<timestamp>_<test name>.log                   |
|                             |                                                       |
|                             | Warning: set this option before the test path such as |
|                             | letp run –log_file /tmp/letp.log test_helloworld.py   |
+-----------------------------+-------------------------------------------------------+
| html report::               | Create a html report                                  |
|                             |                                                       |
|      --html                 | .. image:: img/test_report_html.png                   |
+-----------------------------+-------------------------------------------------------+
| HTML file::                 | The default name is the same as                       |
|                             | the log file with html extension.                     |
|   --html-file               | To change this name, use html_file :                  |
|   path_and_name_of_html_file| --html-file my_html_report.html.                      |
|                             | **Note:** The stdout is not shown with this option.   |
|                             | To see it, use --capture=no                           |
|                             |                                                       |
+-----------------------------+-------------------------------------------------------+

Test selection
^^^^^^^^^^^^^^

.. raw:: html

    <embed>
    <table border=1 rules=all>
    <tr><th> Test selection<th>Description
    <tr><td>test_selection</td>
    <td>test_selection can be a mix of these parameters:
    <br>
    <ul>
        <li>a folder:<br>
            The following command starts all the tests in legato/services/airvantage/host/ and its subfolders: <br>
            <code>letp run legato/services/airvantage/host/</code>
        <li>a python file:<br>
            The following command starts all the tests in legato/services/airvantage/host/test_atcmd.py: <br>
            <code>letp run legato/services/airvantage/host/test_atcmd.py</code>
        <li>a test function:<br>
            The following command starts the test L_AVC2_AtCommand_0001 in test_atcmd.py: <br>
            <code>letp run legato/services/airvantage/host/test_atcmd.py:: L_AVC2_AtCommand_0001 </code>
        <li>a test set in json format:<br>
            The following command starts all the tests referred in sandbox.json: <br>
            <code>letp  run  legato/security/sandbox/runtest/sandbox.json</code> <br>
            [ { "name": "legato/security/sandbox/host/test_basic.py" }, <br>
            { "name": "legato/security/sandbox/host/test_limitation.py" } ]
    </table>
    </embed>

Pytest options
^^^^^^^^^^^^^^

.. raw:: html

    <embed>
    <table border=1 rules=all>
    <tr><th> Pytest Option<th>Description
    <tr><td><code>--config [&lt;config_file.xml&gt;][,&lt;xml_key&gt;=&lt;val&gt;]</code></td>
    <td>XML configuration file of the target (IP address, Name, tty...).
        It is optional as it searches for config/testbench.xml by default. <br>
        It can be called multiple times: <br>
        <code>--config ar758x.xml --config fota.xml</code> <br> <br>
        or can be separated with comma:<br>
        <code>--config ar758x.xml,fota.xml</code><br> <br>
        It is also possible to set/override a specific value with this syntax:
        --config key="value". <br>
        key is the path of the element in the xml tree (xpath format): <br>
        <code>--config config/ima2.xml,config/tester.xml,tester/slink1/name=
            "/dev/ttyUSB1"</code> <br>  <br>

        The syntax to override the attribute is: <br> key(attribute)=value
        such as: <br> --config module/ssh(used)=1 to activate ssh <br>

        All the files declared with --config override the values in the default file testbench.xml.
    <tr><td><code>--ci</code></td>
    <td>For continuous integration. Do not start the tests. <br>
    Create a jenkins.json file containing the tests to execute and the xml configuration.

    <b>Note:</b> you can also use this command to check if you have correctly set all the xml parameters.
    <tr><td><code>--html path_and_name_of_html_file</code></td>
    <td>It generates a html report.<br>
    <b>Note:</b> To use with --capture=sys option to also show the stdout in the html report (--html log/test.html --capture=sys).
    <tr><td><code>--use_uart</code></td>
    <td>By default, ssh is used to communicate with the target with the IP address given in the config file.
        Use --use_uart to communicate with uart and also use the SSH link to update the target for example.
        it is also possible to do the same by setting the "main_link" parameter of ssh to 0 in target.xml.
    <tr><td>other pytest options</td>
    <td>Pass here all the standard pytest options.
    <br>To see the pytest options, type: letp run . --help
    <br>Here are some useful options:
    <ul>
    <li> <code>--collect-only</code> : do not execute tests. Simply see all the available tests.
    <li> <code>--junitxml or --junit-xml</code>: generate a junit xml file. Note:--junitxml is documented in pytest docs while --junit-xml is supported in pytest help page. Add --capture=sys to also put the stdout inside the report
    <li> <code>--tb=no</code> : no backtrace. It can be also auto/long/short/line/native/no
    </table>
    </embed>

Examples
^^^^^^^^

Log file to /tmp/letp.log::

    letp run --log-file /tmp/letp.log test_helloworld.py

Activation of the log debug level::

    letp run --dbg-lvl 0 /tmp/letp.log test_helloworld.py


Environment variables
---------------------

Some environment variables are read by LeTP and taken into account if they exist.
The environment variables have more priority than the values in the xml file.

.. raw:: html

    <embed>
    <table border=1 rules=all><tr><th>Variable<th>Description<th>corresponding xml element
    <tr><td><code>TARGET_IP</code><td>IP address of the target<td>module/ssh/ip_address
    <tr><td><code>TARGET_SSH_PORT</code><td>SSH port used by the target<td>module/ssh/port
    </table>
    </embed>
