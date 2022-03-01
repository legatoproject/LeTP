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
        adduser --disabled-password --gecos "" letp                      && \
        adduser letp dialout                                             && \
        adduser letp tty                                                 && \
        adduser letp sudo                                                && \
        printf '\nsource ~/.letp/env.sh\n' >> /home/letp/.profile           \
    )
# New added for disable sudo password
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

COPY contents/90-letp-user /etc/sudoers.d/90-letp-user

# Add host to host file for sudo
RUN printf 'if ! grep -q "127.0.1.1 letp" /etc/hosts; then echo "127.0.1.1 letp" | sudo tee -a /etc/hosts; fi' >> /home/letp/.profile

# Set default shell to /bin/bash
RUN echo "dash dash/sh boolean false" | sudo debconf-set-selections
RUN sudo DEBIAN_FRONTEND=noninteractive dpkg-reconfigure dash

# Install the CMUX daemon.
COPY contents/gsmMuxd /usr/local/sbin/gsmMuxd

# Install the initialization scripts.
COPY --chown=letp:letp contents/letp /home/letp
RUN (                                                                       \
        if [ -f "/home/letp/container_tools/apt-requirements.txt" ]; then             \
            cat /home/letp/container_tools/apt-requirements.txt | grep "#" -v         \
                | xargs sudo apt-get install --yes || exit 0;               \
        fi                                                                  \
    )
RUN sudo dpkg -i /home/letp/container_tools/deb/*.deb || exit 0
RUN sudo apt-get install -f || exit 0

# Switch to the new non-root user.
WORKDIR /home/letp
USER letp

# Install the Python dependencies for the local user.
RUN pip3 install --user configparser

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
