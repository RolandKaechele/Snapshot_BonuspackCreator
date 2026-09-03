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


REM ── Install torch with the correct backend for the detected GPU ──────────────
REM   RTX 5080 (Blackwell / sm_120) requires CUDA 12.8.
REM   Other NVIDIA cards use CUDA 12.1.  Everything else gets the CPU-only wheel.
REM nvidia-smi is authoritative for NVIDIA; CIM may return virtual adapters first
set GPU_NAME=
where nvidia-smi >nul 2>&1
if not errorlevel 1 (
    nvidia-smi -L >"%TEMP%\spc_gpu.tmp" 2>nul
    set /p GPU_NAME=<"%TEMP%\spc_gpu.tmp"
    del "%TEMP%\spc_gpu.tmp" >nul 2>&1
    REM strip trailing " (UUID: ...)" appended by nvidia-smi -L
    for /f "tokens=1* delims=(" %%A in ("!GPU_NAME!") do set GPU_NAME=%%A
)
REM Fall back to CIM (filters out virtual/remote adapters) if nvidia-smi unavailable
if not defined GPU_NAME (
    for /f "delims=" %%G in ('powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notlike ''*Remote*'' -and $_.Name -notlike ''*Virtual*'' } | Select-Object -First 1 -ExpandProperty Name" 2^>nul') do (
        if not defined GPU_NAME set GPU_NAME=%%G
    )
)

set TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
REM RTX 50xx = Blackwell, requires CUDA 12.8
echo !GPU_NAME! | findstr /I "RTX 50" >nul 2>&1
if not errorlevel 1 (
    set TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
    echo Detected Blackwell GPU -- installing torch with CUDA 12.8
) else (
    echo !GPU_NAME! | findstr /I "NVIDIA" >nul 2>&1
    if not errorlevel 1 (
        set TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
        echo Detected NVIDIA GPU -- installing torch with CUDA 12.1
    ) else (
        echo No NVIDIA GPU detected -- installing CPU-only torch
    )
)

set TORCH_HASH_FILE=%VENV_DIR%\.torch.hash
set TORCH_HASH=!TORCH_INDEX_URL!
set OLD_TORCH_HASH=
if exist "!TORCH_HASH_FILE!" set /p OLD_TORCH_HASH=<"!TORCH_HASH_FILE!"
if /i "!TORCH_HASH!" == "!OLD_TORCH_HASH!" (
    echo torch already installed for this backend, skipping.
) else (
    "%VENV_DIR%\Scripts\python.exe" -m pip install torch torchvision --index-url "!TORCH_INDEX_URL!"
    echo !TORCH_HASH!>"!TORCH_HASH_FILE!"
)


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

REM ─────────────────────────────────────────────────────────────────────────────

REM Show contents of cli.txt if it exists (usage instructions)
if exist "%~dp0cli.txt" (
    type "%~dp0cli.txt"
)

REM Activate the virtual environment and show help
cmd /K "call "!VENV_DIR!\Scripts\activate.bat" 
