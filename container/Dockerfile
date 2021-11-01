# syntax=docker/dockerfile:1
FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install vim -y

RUN apt-get install -y python3
RUN python3 --version
RUN apt-get install -y python3-pip
RUN apt-get install -y python3-setuptools
RUN pip3 install --upgrade pip

RUN pip3 install pytest==6.1.0 lxml==4.6.2 pytest-json-report==1.2.4 pytest-timeout==1.4.2 pytest-cov==2.11.1 colorama==0.4.4 pyserial==3.5 pexpect==4.8.0 ptyprocess==0.7.0 colorlog==4.7.2 future==0.18.2 jinja2==2.11.3 requests==2.25.1 junitparser==2.0.0 setuptools-scm==5.0.1 paramiko==2.7.2 paramiko-expect==0.3.0 openpyxl pyOpenSSL matplotlib pandas ConfigParser logfile

RUN apt-get install -y mosquitto-clients iputils-ping libncurses5-dev libncursesw5-dev bc

## wp7x
RUN apt-get install -y bison build-essential chrpath cifs-utils cmake coreutils curl desktop-file-utils diffstat docbook-utils doxygen fakeroot flex g++ gawk gcc git gitk graphviz help2man libgmp3-dev libmpfr-dev libncurses5-dev libreadline-dev libsdl1.2-dev libtool libxml2-dev libxml-libxml-perl make m4 ninja-build python-jinja2 python-pip python-pyparsing python-pysqlite2 quilt samba scons sed subversion texi2html texinfo unzip wget android-tools-fastboot android-tools-adb openssh-server dh-autoreconf gperf libssl-dev

## rc76
RUN apt-get install -y lib32stdc++6

## hl78
RUN apt-get install -y gcc-multilib git-lfs libc6-dev-i386 p7zip-full python3-crypto python3-pyelftools rsync jq

## Clean
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
