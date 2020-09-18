# Introduction

LeTP stands for Legato Test Project and it tests the
<A HREF="https://github.com/legatoproject/legato-af">Legato framework</a>,
as well as applications on your devices in full automation
under any circumstance.<br>

LeTP, based on the python testing framework
<a HREF="https://docs.pytest.org/en/stable/">pytest</a>, uses
<a HREF="https://pexpect.readthedocs.io/en/stable/">Pexpect</a>,
to validate the outputs of applications running on your target machine.

Being based on a free, open source testing framework, LeTP is highly extendible,
since you can implement 315+ pytest plugins into it. <br>

# Why LeTP?
It facilitates Legato team's CI/CD, share test libraries.
It also helps customer to verify legato functionalities in
their environment easily with LeTP.

LeTP has these features to automate manual testing chores:

- Configure and manage the target and test equipments
- build legato apps
- load the app to the target
- send commands to the target
- read test results from CLI ar AT port
- verify test results
- powercycle the target machine
- conduct a data transfer

Users will also have these bonuses:

- keeping target device online during testing with uninterrupted connections.
- Fully integrated with Sierra Wireless project, reduce the integration workload.
- No need for physical access to the target device,
  test and manage remotely deployed hardware.
- A rich set of fixtures and test libraries allows users to spend less time
  writing tests and more time improving their systems.
- Extensible to customized scripts to monitor and manage other test equipments

# Prerequisites
python 3.6+ <br>

# Run LeTP with system tests
If you use Legato manifest to clone the repo. <br>
```
cd legato/apps/leTP
. ./configLeTP.sh testing_target
cd testing_target
letp run public/runtest/full_campaign.json
```

# Run unit tests
Commands:
Run
```
pip3 install tox
tox
```

***
Test logs, test xml and html reports can be found in the /log directory. <br>
Test coverage record is in coverage-report/index.html.***

# More documents and tutorials
**The documents are work in progress.** <br>
Install doxygen 1.8.11 version <br>
```
cd doc
make
```
See doc on leTP/doc/html/index.html

* * *
Copyright (C) Sierra Wireless Inc.
