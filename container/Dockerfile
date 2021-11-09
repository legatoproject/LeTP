# syntax=docker/dockerfile:1
# Docker image for official LeTP runtime environment.
#
# SPDX-License-Identifier: MPL-2.0
#
# Copyright (C) Sierra Wireless Inc.
FROM ubuntu:18.04
ARG DEBIAN_FRONTEND=noninteractive

# Install and update general system dependencies.
RUN apt-get update --yes && apt-get upgrade --yes
RUN (                           \
        apt-get install --yes   \
            git                 \
            iproute2            \
            iputils-ping        \
            minicom             \
            nano                \
            python3             \
            python3-pip         \
            python3-setuptools  \
            sudo                \
            vim                 \
    )
RUN pip3 install --upgrade pip
COPY contents/swi.pub swi.pub
COPY contents/legato-tools.list /etc/apt/sources.list.d/legato-tools.list
RUN (                               \
        apt-key add - < swi.pub &&  \
        rm swi.pub              &&  \
        apt-get update --yes        \
    )

# Clean up after the package installations.
RUN apt-get clean

# Create a non-root user with sudo access for normal operations.
RUN (                                                                       \
        adduser --disabled-password --gecos "LeTP,,," letp               && \
        adduser letp dialout                                             && \
        adduser letp tty                                                 && \
        printf '\nsource ~/.letp/env.sh\n' >> /home/letp/.profile           \
    )
COPY contents/90-letp-user /etc/sudoers.d/90-letp-user

# Install the CMUX daemon.
COPY contents/gsmMuxd /usr/local/sbin/gsmMuxd

# Switch to the new non-root user.
WORKDIR /home/letp
USER letp

# Install the Python dependencies for the local user.
RUN pip3 install --user configparser

# Install the initialization scripts.
COPY --chown=letp:letp contents/letp /home/letp

# Install the internal copy of the public LeTP source.
ARG LETP_VERSION=master
ARG LETP_REMOTE=https://github.com/legatoproject/LeTP.git
RUN (                                                                                   \
        mkdir -p /home/letp/letp                                                     && \
        git clone ${LETP_REMOTE} /tmp/letp                                           && \
        cd /tmp/letp                                                                 && \
        git archive ${LETP_VERSION} | tar -xC /home/letp/letp                        && \
        git describe --tags > /home/letp/letp/pytest_letp/tools/.version 2>/dev/null && \
        rm -R /tmp/letp                                                                 \
    )

# Install the internal copy of the public LeTP test source.
ARG TESTS_VERSION=master
ARG TESTS_REMOTE=https://github.com/legatoproject/Qa-LeTP.git
RUN (                                                               \
        mkdir -p /home/letp/tests                               &&  \
        git clone ${TESTS_REMOTE} /tmp/tests                    &&  \
        cd /tmp/tests                                           &&  \
        git archive ${TESTS_VERSION} | tar -xC /home/letp/tests &&  \
        rm -R /tmp/tests                                            \
    )
