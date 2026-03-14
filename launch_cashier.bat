@echo off
setlocal
REM Set this to your project folder on Windows (option 2: run from anywhere)
set "APP_DIR=C:\CafeBilling\cafe_billing_system"
cd /d "%APP_DIR%"
set "SETUP_MARKER=.setup_complete"
set "PY_EXE="

echo.
echo ==========================================
echo   CafeBilling - Cashier Launcher
echo ==========================================
echo.

if not exist "app.py" (
  echo ERROR: app.py not found in this folder.
  echo Check APP_DIR in this BAT file:
  echo   %APP_DIR%
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found.
  pause
  exit /b 1
)

if exist "venv\Scripts\python.exe" (
  set "PY_EXE=venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    echo First-time setup: creating Python virtual environment...
    py -3 -m venv venv
  ) else (
    where python >nul 2>&1
    if not errorlevel 1 (
      echo First-time setup: creating Python virtual environment...
      python -m venv venv
    ) else (
      echo ERROR: Python is not installed or not in PATH.
      echo Install Python 3.10+ and re-run this launcher.
      pause
      exit /b 1
    )
  )
  if not exist "venv\Scripts\python.exe" (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
  )
  set "PY_EXE=venv\Scripts\python.exe"
)

if not exist "%SETUP_MARKER%" (
  echo.
  echo First-time setup: installing required packages...
  "%PY_EXE%" -m pip install --upgrade pip
  if errorlevel 1 (
    echo ERROR: pip upgrade failed.
    pause
    exit /b 1
  )
  "%PY_EXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
  )
  echo ok>"%SETUP_MARKER%"
  echo Setup complete. Next launches will be fast.
)

echo.
echo Starting server on port 8510...
start "" http://localhost:8510
echo.
echo Local URL: http://localhost:8510
echo LAN URL:   http://YOUR_LAPTOP_IP:8510
echo.
echo Keep this window open while the cafe is using the system.
echo Press Ctrl+C in this window to stop.
echo.

"%PY_EXE%" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8510

echo.
echo Server stopped.
pause
