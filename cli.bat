@echo off

REM =============================================
REM Python Launcher
REM --------------------------------------------
REM - Creates a virtual environment if needed
REM - Installs/updates dependencies from
REM   requirements.txt (skipped if unchanged)
REM - Activates the venv and shows help
REM Usage: Double-click or run from command line
REM =============================================

setlocal enabledelayedexpansion

set VENV_DIR=%~dp0venv

if exist "%VENV_DIR%" (
    echo Virtual environment already exists at %VENV_DIR%
    goto :venvready
)

echo Creating virtual environment at %VENV_DIR% ...
%~dp0temp\Python_3.12.6_64bit\python.exe -m venv "%VENV_DIR%"


:venvready

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip

if exist "%~dp0requirements.txt" (
    set REQ_FILE=%~dp0requirements.txt
    set HASH_FILE=%VENV_DIR%\.requirements.hash

    REM Compute current hash of requirements.txt (grab only the hash line)
    for /f "skip=1 tokens=*" %%H in ('certutil -hashfile "!REQ_FILE!" SHA256 2^>nul') do (
        if not defined CUR_HASH set CUR_HASH=%%H
    )

    set OLD_HASH=
    if exist "!HASH_FILE!" set /p OLD_HASH=<"!HASH_FILE!"

    if /i "!CUR_HASH!" == "!OLD_HASH!" (
        echo Requirements already up to date, skipping pip install.
    ) else (
        "%VENV_DIR%\Scripts\python.exe" -m pip install -r "!REQ_FILE!"
        echo !CUR_HASH!>"!HASH_FILE!"
    )
)

REM Show contents of cli.txt if it exists (usage instructions)
if exist "%~dp0cli.txt" (
    type "%~dp0cli.txt"
)

REM Activate the virtual environment and show help
cmd /K "call "!VENV_DIR!\Scripts\activate.bat" 
