@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

echo Starting test suite for qEditor...
echo.

:: Set project directory
SET PROJECT_DIR=C:\Workspace\qEditor
SET CONDA_PATH=C:\Software\conda3
SET ENV_NAME=qeditor

:: Check if project directory exists
IF NOT EXIST "%PROJECT_DIR%" (
    echo ERROR: Project directory %PROJECT_DIR% not found.
    pause
    exit /b 1
)

:: Check if Conda is installed
IF NOT EXIST "%CONDA_PATH%\Scripts\conda.exe" (
    echo ERROR: Conda not found at %CONDA_PATH%.
    echo Please ensure Conda is installed.
    pause
    exit /b 1
)

:: Initialize Conda
call "%CONDA_PATH%\Scripts\activate.bat"

:: Activate Conda environment
call conda activate %ENV_NAME%
IF ERRORLEVEL 1 (
    echo ERROR: Failed to activate Conda environment '%ENV_NAME%'.
    echo Please ensure the '%ENV_NAME%' environment exists.
    pause
    exit /b 1
)

:: Navigate to project directory
cd /d "%PROJECT_DIR%"
IF ERRORLEVEL 1 (
    echo ERROR: Failed to navigate to %PROJECT_DIR%.
    pause
    exit /b 1
)

:: Check and install pytest-cov
echo Checking for pytest-cov...
pip show pytest-cov >nul 2>&1
IF ERRORLEVEL 1 (
    echo Installing pytest-cov...
    pip install pytest-cov
    IF ERRORLEVEL 1 (
        echo ERROR: Failed to install pytest-cov.
        pause
        exit /b 1
    )
)

:: Run tests with coverage
echo Running tests...
pytest tests/ -v --cov=app --cov=src > test_output.txt
IF ERRORLEVEL 1 (
    echo Tests completed with errors. Check test_output.txt for details.
) ELSE (
    echo Tests completed successfully. Results saved to test_output.txt.
)

:: Save coverage report
coverage report > coverage.txt
echo Coverage report saved to coverage.txt.

:: Display results
echo.
echo Test output:
type test_output.txt
echo.
echo Coverage report:
type coverage.txt
echo.

pause
ENDLOCAL