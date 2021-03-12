# Introduction

LeTP stands for Legato Test Project and
provides the ability to perform full test automation
for Sierra Wireless embedded systems under any circumstances.<br>

LeTP, based on the python testing framework
<a HREF="https://docs.pytest.org/en/stable/">pytest</a>, uses
<a HREF="https://pexpect.readthedocs.io/en/stable/">Pexpect</a>
to run any application on your device. It then compares the output with the expected output,
provided in the test script. This makes sure that any app installed on your device is functioning as expected.

Being based on a free, open source testing framework, LeTP is highly extendable,
allowing you to implement 315+ pytest plugins into it. <br>

# Why LeTP?
It facilitates Legato team's CI/CD, share test libraries
and helps customers verify legato functionalities in
their environment easily with LeTP.

LeTP has the following features to automate manual testing procedures:

- Configure and manage the target and test equipments
- Build legato apps
- Load apps onto the target
- Send commands to the target
- Read test results from CLI or AT port
- Verify test results
- Power cycle the target device
- Conduct data transfers

Users will also have these bonuses:

- Target device is kept online during testing with uninterrupted connections.
- Fully integrated with Sierra Wireless project to reduce the integration workload.
- Test and manage remotely deployed hardware.
- A rich set of fixtures and test libraries allows users to spend less time
  writing tests and more time improving their systems.
- Extensible with customized scripts that can monitor and manage other test equipment.

# Prerequisites
python 3.6+ and pip3 <br>

# Running your first tests

1. Clone the repo:
```
git clone https://github.com/legatoproject/LeTP.git
```
2. Go into the directory:
```
cd LeTP
```
3. Run the configuration script to setup the environment variables:
```
source configLeTP.sh testing_target
```
4. Go to the directory where your tests are:
```
cd testing_target/scenario/commands
```
5. Run your tests:
```
letp run test_at.py --config 'module/ssh(used)=1' --config 'module/slink1(used)=1' --config 'module/slink1/name=<DEVICE_CLI_PORT>' --config 'module/slink2(used)=1' --config 'module/slink2/name=<DEVICE_AT_PORT>'
```
Change the fields with your device's CLI port and AT port. For example: "/dev/ttyUSB0"
"slink1" and "slink2" refers to your device's CLI and AT ports respectively.

# More documents and tutorials
Install sphinx: <br>
```
pip3 install sphinx
```
set your environment variables: <br>
```
cd LeTP
source configLeTP.sh testing_target
```
and then run: <br>
```
cd doc
make html
```
See doc on letp/doc/_sphinx/html/index.html

# Run unit tests
```
pip3 install tox
tox test
```

***
Test logs, test xml and html reports can be found in the /log directory. <br>
Test coverage record is in coverage-report/index.html.

* * *
Copyright (C) Sierra Wireless Inc.
