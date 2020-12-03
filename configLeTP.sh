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
DEFAULT_TEST_DIR="$LETP_PATH/test"
letp_tests=$1

if [ -z "$LEGATO_ROOT" ]; then
    echo -e "\e[31mWARNING\e[0m: LEGATO_ROOT is not defined.You won't be able to compile a legato application"
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
if [[ $letp_tests == *"qa/letp"* ]]; then
    export QA_ROOT=${letp_tests/qa*/qa}
    echo "Set QA_ROOT to $QA_ROOT"
fi

chmod +x $LETP_PATH/pytest_letp/tools/letp.py
# Add letp in the system path
export PATH=$PATH:$LETP_PATH
export PYTHONPATH=$LETP_PATH:$LETP_PATH/letp-internal:$LETP_PATH/pytest_letp/tools/html_report
echo "Set PYTHONPATH to $PYTHONPATH"

export LETP_INTERNAL_PATH="$LETP_PATH/letp-internal"
echo "Set LETP_INTERNAL_PATH to $LETP_INTERNAL_PATH"

REQ_CACHE=${REQ_CACHE:-"$LETP_PATH/.requirements"}

pip_install() {
    local req_txt="$1"

    local req_hash=$(sha1sum "$req_txt" | awk '{print $1}')

    if [ -n "$req_hash" ] && [ -e "$REQ_CACHE/$req_hash" ]; then
        # Skipping, hash is already known and installed
        return
    fi

    echo "LeTP dependencies: install $req_txt"

    python3 -m pip install --user -r "$req_txt"

    # Not failing on purpose in case the source folder is read-only
    mkdir -p "$REQ_CACHE" 2>/dev/null || true
    touch "$REQ_CACHE/$req_hash" || true
}

# Install LeTP dependencies
pip_install "$LETP_PATH/requirements.txt"

if [ -f "$LETP_TESTS/requirements.txt" ]; then
    # Install test dependencies
    pip_install "$LETP_TESTS/requirements.txt"
fi

# Go back to the initial directory
cd $INITIAL_DIR
