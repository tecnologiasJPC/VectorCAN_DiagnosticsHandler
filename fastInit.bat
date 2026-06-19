@echo off
title Setting up Python Virtual Environment...

:: 1. Define the virtual environment directory name
set "VENV_DIR=.venv"

:: 2. Check if the virtual environment exists, if not, create it
if not exist "%VENV_DIR%" (
    echo Creating a new virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

:: 3. Activate the virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"

if exist "requirements.txt" (
    echo Installing libraries from requirements.txt...
    pip install -r requirements.txt
    echo Dependencies installed successfully.
) else (
    echo WARNING: requirements.txt file was not found in the current directory.
)

@echo off
:: Verifica si el comando 'code' existe en el sistema
where code >nul 2>nul

if %errorlevel% equ 0 (
    code .
) else (
    Visual Studio Code no esta instalado en este sistema.
    pause
)