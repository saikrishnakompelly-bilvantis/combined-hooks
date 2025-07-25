@echo off
REM APIGenie CLI wrapper for Windows
REM This script allows you to use APIGenie from the command line

setlocal EnableDelayedExpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Remove trailing backslash if present
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

REM Path to the APIGenie executable
set "APIGENIE_EXE=!SCRIPT_DIR!\APIGenie.exe"

REM Check if the executable exists
if not exist "!APIGENIE_EXE!" (
    echo Error: APIGenie.exe not found in !SCRIPT_DIR!
    echo Make sure APIGenie is properly installed.
    exit /b 1
)

REM Pass all arguments to APIGenie
"!APIGENIE_EXE!" %* 