.. _introduction:

############
Introduction
############

LeTP stands for Legato Test Project and
provides the ability to perform full test automation
for embedded devices under any circumstances.

LeTP, based on the python testing framework
`pytest <https://docs.pytest.org/en/stable/>`_, uses
`Pexpect <https://pexpect.readthedocs.io/en/stable/>`_,
to validate the outputs of applications running on your target machine.

Being based on a free, open source testing framework, LeTP is highly extendable,
allowing you to implement 315+ pytest plugins into it.

Why LeTP?
---------

It facilitates Legato team's CI/CD, share test libraries
and helps customers verify legato functionalities in
their environment easily with LeTP.

LeTP has the following features to automate manual testing procedures:

- Configure and manage the target and test equipments
- Build legato apps
- Load appS onto the target
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

Prerequisites
-------------

python 3.6+


Run LeTP with system tests
--------------------------

If you use Legato manifest to clone the repo::

    cd legato/apps/leTP
    ./configLeTP.sh testing_target
    cd testing_target
    letp run public/runtest/full_campaign.json

Commands to run unit tests::

    pip3 install tox
    tox test

| Test logs, test xml and html reports can be found in the /log directory.
| Test coverage record is in coverage-report/index.html.

More documents and tutorials
""""""""""""""""""""""""""""
Install sphinx::

    pip install sphinx

and then::

    cd doc
    make html

See doc on *letp/doc/_sphinx/html/index.html*

Copyright (C) Sierra Wireless Inc.
