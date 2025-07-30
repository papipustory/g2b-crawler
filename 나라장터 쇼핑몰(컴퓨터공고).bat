@echo off
setlocal

:: Check if Python is installed, define download path
set PYTHON_INSTALL_PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe
set PYTHON_DOWNLOAD_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
set PYTHON_INSTALLER=python310_installer.exe

:: If Python is not installed, download and install it
if not exist "%PYTHON_INSTALL_PATH%" (
    echo [INFO] Python 3.10 is not installed. Starting installation...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_DOWNLOAD_URL%' -OutFile '%PYTHON_INSTALLER%'"
    start /wait %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del %PYTHON_INSTALLER%
)

:: Set Python executable path
set PYTHON_EXE="%PYTHON_INSTALL_PATH%"

:: Virtual environment setup
set VENV_DIR=venv
if not exist %VENV_DIR%\Scripts\activate.bat (
    echo [INFO] Creating virtual environment...
    %PYTHON_EXE% -m venv %VENV_DIR%
)

:: Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat

:: Date check for locking mechanism
for /f %%i in ('powershell -Command "Get-Date -Format yyyyMMdd"') do set CURRENT_DATE=%%i
if %CURRENT_DATE% LSS 20250101 goto expired
if %CURRENT_DATE% GTR 20251231 goto expired

:: Install required packages
echo [INFO] Installing required packages...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
playwright install >nul 2>&1

:: Run crawler
echo [INFO] Starting crawler. LOADING...
python run_crawler.py

:: Exit after completion
exit

:expired
echo [ERROR] Please contact Manager KIM SEHOON..
pause
exit /b
