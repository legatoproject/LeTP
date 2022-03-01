# LeTP Docker user environment initialization.
#
# Set up the environment variables which are needed by LeTP and various tools.  This file is sourced
# by the "letp" user's .profile file.
#
# SPDX-License-Identifier: MPL-2.0
#
# Copyright (C) Sierra Wireless Inc.

# @brief    Extract the module name from the generated name.xml.
#
# @return   Module name, or an empty string if the name is unavailable.
function _get_module_name() {
    sed -nE 's:<test><module><name>([^<]+)</name></module></test>$:\1: p' \
        "${LETP_USER_CONFIG_DIR}/name.xml" 2>/dev/null
}

# @brief    List the directories from which environment files may be sourced.
#
# @return   List of paths (may be empty).
function _get_env_mounts() {
    cat "${LETP_USER_CONFIG_DIR}/mount.txt" 2>/dev/null
}

if [ -d "/ws/work" ]
then
    export LETP_PATH=/ws/work/letp
    export LETP_TESTS=/ws/work/qa
    export LEGATO_ROOT=/ws/work/legato
    if [ -d /ws/work/modem ]; then
        sudo chown -R letp:letp /ws/work/modem
    fi
else
    export LETP_PATH=~/letp
    export LETP_TESTS=~/tests
    export LEGATO_ROOT=~/legato
fi
export ARTIFACTS_DIR=~/artifacts
export LETP_USER_CONFIG_DIR=~/.letp
export TOOLS_DIR=~/tools

export LETP_CONFIG_XML="${LETP_USER_CONFIG_DIR}/testbench.xml"
export LETP_MODULE="$(_get_module_name)"

export PATH="${PATH}:${LETP_PATH}"
export PYTHONPATH="${LETP_PATH}:${LETP_PATH}/pytest_letp/tools/html_report"

if [[ -d "${LETP_PATH}/letp-internal" ]]; then
    export LETP_INTERNAL_PATH="${LETP_PATH}/letp-internal"
    export PYTHONPATH="${PYTHONPATH}:${LETP_INTERNAL_PATH}"
fi

for p in $(_get_env_mounts); do
    if [[ -r "${p}/letp-env.sh" ]]; then
        source "${p}/letp-env.sh"
    fi
done
