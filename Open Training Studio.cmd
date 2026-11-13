@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-visualizer\Scripts\python.exe" (
    ".venv-visualizer\Scripts\python.exe" -m transit_rl.visualizer %*
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m transit_rl.visualizer %*
) else (
    python -m transit_rl.visualizer %*
)
if errorlevel 1 (
    echo.
    echo Could not start Training Studio. See docs\VISUALIZER.md for setup.
    pause
)
endlocal
