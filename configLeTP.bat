@REM Configure LeTP Windows environment
@REM Copyright (C) Sierra Wireless Inc.
@ECHO OFF

set "LETP_PATH="
set "LETP_TESTS="
set "PYTHONPATH="
set "LETP_INTERNAL_PATH="
set "QA_ROOT="
set "testPath="

set LETP_PATH=%CD%

IF "%LEGATO_ROOT%"=="" ECHO WARNING: LEGATO_ROOT is not defined.You won't be able to compile a legato application
set defaultTestPath=%LETP_PATH%\testing_target
ECHO Enter your root test directory (default: %defaultTestPath%):
set /p testPath=

IF "%testPath%" equ "" set testPath=%defaultTestPath%

set LETP_TESTS=%testPath%
set PYTHONPATH=%LETP_PATH%;%LETP_PATH%\letp-internal;%LETP_PATH%\pytest_letp\tools\html_report
IF exist %LETP_PATH%\letp-internal\ set LETP_INTERNAL_PATH=%LETP_PATH%\letp-internal

@REM Find a way to set QA_ROOT
ECHO LETP_PATH is set to "%LETP_PATH%"
ECHO LETP_TESTS is set to "%LETP_TESTS%"
ECHO LETP_INTERNAL_PATH is set to "%LETP_INTERNAL_PATH%"
ECHO QA_ROOT is set to "%QA_ROOT%"

python --version | findstr -r "3\.[6-9].*" >nul
IF %errorlevel% neq 0 (
    ECHO ERROR LeTP requires python3.6+ to be installed
    exit /b
)

py -m pip --version >nul
IF %errorlevel% neq 0 (
    ECHO ERROR LeTP requires pip to be installed
    exit /b
)

python package.py --install -p %LETP_PATH%

set windowsLETP=letpWin.py
set letp=%LETP_PATH%\pytest_letp\tools\letp.py

del %windowsLETP% >nul
mklink %windowsLETP% %letp%