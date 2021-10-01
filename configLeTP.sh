#!/bin/bash

# Copyright (C) Sierra Wireless Inc.
echo "Usage: source configLeTP.sh [path of LETP tests]"

if ! python3 -m pip help >/dev/null 2>&1; then
    echo -e "\e[ERROR\e[0m: pip not available for python3"
    if hash apt-get 2>/dev/null; then
        echo -e "\e[ERROR\e[0m: install with:"
        echo "sudo apt-get install python3-pip"
    fi
fi

INITIAL_DIR=$PWD
# Checked that it is bash
if [ -n "$BASH_SOURCE" ]; then
    # Not $0 if it is called from a script
    [ -n "$SCRIPT_NAME" ] || declare -r SCRIPT_NAME=$(readlink -f ${BASH_SOURCE[0]})
    # Go to LeTP root dir
    cd $(dirname $SCRIPT_NAME)
fi

export LETP_PATH=$PWD

# Point to the test samples
DEFAULT_TEST_DIR="$LETP_PATH/testing_target"
letp_tests=$1


if [ -z "$LEGATO_ROOT" ]; then
    if [ -d "$LETP_PATH/../legato" ]; then
        export LEGATO_ROOT=$(cd "$LETP_PATH/../legato" && pwd)

        echo "Set LEGATO_ROOT to $LEGATO_ROOT"
    else
        echo -e "\e[31mWARNING\e[0m: LEGATO_ROOT is not defined.You won't be able to compile a legato application"
    fi
else
    echo "Using LEGATO_ROOT is $LEGATO_ROOT"
fi

if [ "$letp_tests" = "" ]; then
    echo "Enter your root test directory (default: $DEFAULT_TEST_DIR): "
    read letp_tests
fi
[ "$letp_tests" = "" ] && letp_tests=$DEFAULT_TEST_DIR
# Be sure that it is the absolute path
export LETP_TESTS=$(cd $letp_tests; pwd)
echo "Set LETP_TESTS to $LETP_TESTS"

# try to find qa testbase with relative path
if [[ $LETP_TESTS == *"qa/letp"* ]]; then
    export QA_ROOT=${LETP_TESTS%/qa*}/qa
    echo "Set QA_ROOT to $QA_ROOT"
fi

chmod +x $LETP_PATH/pytest_letp/tools/letp.py
# Add letp in the system path
export PATH=$PATH:$LETP_PATH
export PYTHONPATH=$LETP_PATH:$LETP_PATH/letp-internal:$LETP_PATH/pytest_letp/tools/html_report
echo "Set PYTHONPATH to $PYTHONPATH"

# Set LETP_INTERNAL_PATH if the diectory for it exists.
if [ -d "$LETP_PATH/letp-internal" ]; then
    export LETP_INTERNAL_PATH="$LETP_PATH/letp-internal"
    echo "Set LETP_INTERNAL_PATH to $LETP_INTERNAL_PATH"
fi

# Install LeTP dependencies
python3 package.py --install -p $LETP_PATH

# Go back to the initial directory
cd $INITIAL_DIR
