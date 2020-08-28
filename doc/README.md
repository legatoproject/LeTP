# Introduction

LeTP stands for Legato Test Project.

It tests <A HREF="https://github.com/legatoproject/legato-af">
Legato framework</A>, or your application by sending commands from host to your target
and using <A HREF="https://pexpect.readthedocs.io/en/stable/">Pexpect</A>
to validate the expected returned output.

It also manages the target and other test equipments configuration,
drive also your those equipments if needed. <br>

It is based on the python test framework
 <A HREF="https://docs.pytest.org/en/stable/">pytest</A>,
provides an open Source test framework provided along with the Legato solution.

Users can also easily extend the LeTP framework with 315+ pytest plugins.

# Prerequisites
python 3.5+ <br>
```
pip3 install -r requirements.txt
```

# Run unit tests
Commands:
```
cd test
export LETP_TESTS=./
../letp run --log_file log/test_json_report.log . -x --capture=sys --junitxml log/test_results_letp.qa.xml --html log/test_report.html
```

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
