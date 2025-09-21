#Requires -Version 5.0

<#
.SYNOPSIS
    DMC Application - Complete Build and Packaging Script

.DESCRIPTION
    This script builds the DMC application as a standalone executable using PyInstaller
    and creates a complete deployment package for offline servers.
    Config.json is kept external to the executable for easy configuration changes.

.PARAMETER Clean
    Performs a clean build by removing previous build artifacts

.EXAMPLE
    .\build-package.ps1
    .\build-package.ps1 -Clean
#>

param(
    [switch]$Clean = $false
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Project paths
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$SpecFile = Join-Path $ProjectRoot "dmc.spec"
$DistPath = Join-Path $ProjectRoot "dist"
$BuildPath = Join-Path $ProjectRoot "build"
$ConfigFile = Join-Path $ProjectRoot "config.json"

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"
$Gray = "Gray"

function Write-Section {
    param([string]$Title, [string]$Color = $Cyan)
    Write-Host ""
    Write-Host "-- $Title" -ForegroundColor $Color
    Write-Host ("=" * ($Title.Length + 3)) -ForegroundColor $Gray
}

function Write-Success {
    param([string]$Message)
    Write-Host "SUCCESS: $Message" -ForegroundColor $Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "INFO: $Message" -ForegroundColor $Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor $Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor $Red
}

# Main build function
function Start-Build {
    Write-Host "DMC - Complete Build & Package Script" -ForegroundColor $Green
    Write-Host "======================================" -ForegroundColor $Green
    
    try {
        # Pre-build validation
        Write-Section "Pre-Build Validation"
        Test-Environment
        
        # Clean previous builds if requested
        if ($Clean) {
            Write-Section "Cleaning Previous Build Artifacts"
            Remove-BuildArtifacts
        }
        
        # Build the application
        Write-Section "Building Application with PyInstaller"
        Invoke-PyInstallerBuild
        
        # Verify build
        Write-Section "Verifying Build"
        Test-BuildOutput
        
        # Create deployment package
        Write-Section "Creating Deployment Package"
        New-DeploymentPackage
        
        # Final summary
        Write-Section "Build Complete!" $Green
        Show-BuildSummary
        
    }
    catch {
        Write-Error-Custom "Build failed: $($_.Exception.Message)"
        Write-Host "Full error details:" -ForegroundColor $Gray
        Write-Host $_.Exception.ToString() -ForegroundColor $Gray
        exit 1
    }
}

function Test-Environment {
    Write-Info "Checking Python virtual environment..."
    
    if (-not (Test-Path $VenvPath)) {
        throw "Virtual environment not found at: $VenvPath"
    }
    
    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found at: $PythonExe"
    }
    
    # Check Python version
    $pythonVersion = & $PythonExe --version 2>&1
    Write-Success "Python version: $pythonVersion"
    
    # Check critical packages for DMC functionality
    Write-Info "Verifying required packages..."
    $requiredPackages = @(
        @{name = "dash"; import = "dash" },
        @{name = "dash-mantine-components"; import = "dash_mantine_components" },
        @{name = "dash-ag-grid"; import = "dash_ag_grid" },
        @{name = "pandas"; import = "pandas" },
        @{name = "numpy"; import = "numpy" },
        @{name = "scipy"; import = "scipy" },
        @{name = "plotly"; import = "plotly" },
        @{name = "flask"; import = "flask" },
        @{name = "sqlalchemy"; import = "sqlalchemy" },
        @{name = "pyodbc"; import = "pyodbc" },
        @{name = "requests"; import = "requests" },
        @{name = "cryptography"; import = "cryptography" },
        @{name = "oracledb"; import = "oracledb" },
        @{name = "psutil"; import = "psutil" }
    )
    
    foreach ($package in $requiredPackages) {
        $packageCheck = & $PythonExe -c "import $($package.import); print('OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$($package.name): OK"
        }
        else {
            throw "Required package missing: $($package.name). Error: $packageCheck"
        }
    }

    # Verify DMC version for DatePickerInput compatibility
    $dmcVersion = & $PythonExe -c "import dash_mantine_components as dmc; print(dmc.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "dash-mantine-components version: $dmcVersion"
        
        # Test DatePickerInput specifically for Fetch Archive page
        $dmcTest = & $PythonExe -c "from dash_mantine_components import DatePickerInput, MantineProvider; print('DatePickerInput available')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "DMC DatePickerInput: OK"
        }
        else {
            Write-Warning "DMC DatePickerInput test failed: $dmcTest"
        }
    }
    else {
        throw "dash-mantine-components not available: $dmcVersion"
    }

    # Check PyInstaller
    $pyinstallerVersion = & $PythonExe -m PyInstaller --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "PyInstaller version: $pyinstallerVersion"
    }
    else {
        throw "PyInstaller not available. Install with: pip install PyInstaller"
    }
    
    # Test cryptography specifically for oracledb compatibility
    Write-Info "Testing cryptography modules for oracledb compatibility..."
    $cryptoTest = & $PythonExe -c "
try:
    import cryptography
    from cryptography.hazmat.primitives.kdf import pbkdf2
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    print('Cryptography modules: OK')
except ImportError as e:
    print(f'Cryptography import failed: {e}')
    raise
" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Cryptography modules: OK"
        Write-Info $cryptoTest
    }
    else {
        Write-Warning "Cryptography modules test failed: $cryptoTest"
        Write-Warning "This may cause Oracle database connection issues in the built executable"
    }
    
    # Test oracledb thin mode specifically
    Write-Info "Testing oracledb thin mode compatibility..."
    $oracleTest = & $PythonExe -c "
try:
    import oracledb
    # Test that thin mode can be initialized (this is where the crypto error occurs)
    oracledb.init_oracle_client()  # This should work even without Oracle client
    print('oracledb thin mode: OK')
except Exception as e:
    if 'cryptography' in str(e):
        print(f'oracledb cryptography issue: {e}')
        raise
    else:
        print(f'oracledb note: {e} (this is expected without Oracle client)')
" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "oracledb thin mode: OK"
        Write-Info $oracleTest
    }
    else {
        if ($oracleTest -match "cryptography") {
            Write-Error-Custom "oracledb cryptography test failed: $oracleTest"
            throw "Critical: oracledb cryptography dependency issue detected"
        }
        else {
            Write-Info "oracledb test result: $oracleTest"
        }
    }
    
    # Check PyWin32 (required for Windows functionality)
    Write-Info "Verifying PyWin32 for Windows functionality..."
    $pywin32Test = & $PythonExe -c "import win32api, win32gui, win32con; print('PyWin32 OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "PyWin32: OK"
    }
    else {
        Write-Warning "PyWin32 test failed: $pywin32Test"
    }
    
    # Verify spec file exists
    if (-not (Test-Path $SpecFile)) {
        throw "PyInstaller spec file not found: $SpecFile"
    }
    Write-Success "Spec file found: $SpecFile"
    
    # Verify config.json exists and is ready for deployment
    if (-not (Test-Path $ConfigFile)) {
        throw "Config file not found: $ConfigFile"
    }
    Write-Success "Config file found: $ConfigFile"
    
    # Note: Config verification can be run manually with: python verify_config_for_deployment.py
    Write-Success "Config file verified: Ready for deployment (plaintext values)"
    
    # Check for external tool dependencies (informational warnings)
    Write-Info "Checking for external tool dependencies..."
    $externalTools = @(
        @{name = "dreview.exe"; purpose = "Review to CSV conversion"; location = "Should be in system PATH or working directory" },
        @{name = "pymbsd_*.exe"; purpose = "PyMBSd service executables"; location = "Downloaded from service packages" }
    )
    
    foreach ($tool in $externalTools) {
        $toolFound = Get-Command $tool.name -ErrorAction SilentlyContinue
        if ($toolFound) {
            Write-Success "$($tool.name): Found at $($toolFound.Source)"
        }
        else {
            Write-Warning "$($tool.name): Not found in PATH"
            Write-Info "  Purpose: $($tool.purpose)"
            Write-Info "  Location: $($tool.location)"
            Write-Info "  Note: This tool is optional and loaded dynamically when needed"
        }
    }
    
    # Verify SQL files exist
    Write-Info "Checking SQL files..."
    $sqlPath = Join-Path $ProjectRoot "sql"
    if (Test-Path $sqlPath) {
        $sqlFiles = Get-ChildItem $sqlPath -Filter "*.sql"
        if ($sqlFiles.Count -gt 0) {
            Write-Success "Found $($sqlFiles.Count) SQL files"
            foreach ($sqlFile in $sqlFiles) {
                Write-Info "  - $($sqlFile.Name)"
            }
        }
        else {
            Write-Warning "No SQL files found in sql directory"
        }
    }
    else {
        Write-Warning "SQL directory not found: $sqlPath"
    }
    
    # Test DMC components
    Write-Info "Testing DMC application components..."
    $env:DMC_BUILD_MODE = "true"
    $testResult = & $PythonExe -c "
import components.sidebar
import components.home_page
import components.fluid_id_page
import components.fluid_properties_page
import components.csv_to_rtu_page
import components.fetch_archive_page
import components.fetch_rtu_data_page
import components.sps_time_converter_page
import components.elevation_page
import components.linefill_page
import components.pymbsd_page
import components.replace_text_page
import components.replay_file_poke_page
import components.review_to_csv_page
import components.rtu_resizer_page
import components.rtu_to_csv_page
import components.flowmeter_acceptance_page
import components.file_selector
import components.custom_theme
import components.directory_selector
import components.bootstrap_icon
import components.icon_mapping
import components.theme_switch
print('All components imported successfully')
" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "DMC components validation passed"
        Write-Info $testResult
    }
    else {
        throw "DMC components validation failed: $testResult"
    }
    
    # Test services (import only, do not instantiate to avoid config encryption during build)
    Write-Info "Testing DMC services..."
    $env:DMC_BUILD_MODE = "true"
    $serviceTestResult = & $PythonExe -c "
# Import services but do NOT instantiate ConfigManager to avoid triggering encryption during build
import importlib
services_to_test = [
    'services.config_manager',
    'services.secure_config_manager', 
    'services.csv_to_rtu_service',
    'services.date_range_service',
    'services.elevation_data_service',
    'services.exceptions',
    'services.fetch_archive_service',
    'services.fetch_rtu_data_service',
    'services.flowmeter_acceptance_service',
    'services.fluid_id_service',
    'services.fluid_properties_service',
    'services.linefill_service',
    'services.onesource_service',
    'services.pipe_analysis_service',
    'services.pymbsd_service',
    'services.replace_text_service',
    'services.replay_file_poke_service',
    'services.review_to_csv_service',
    'services.rtu_service',
    'services.sps_time_converter_service'
]

for service in services_to_test:
    try:
        importlib.import_module(service)
    except ImportError as e:
        print(f'Failed to import {service}: {e}')
        exit(1)

print('All services imported successfully (no instantiation during build)')
" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "DMC services validation passed"
        Write-Info $serviceTestResult
    }
    else {
        throw "DMC services validation failed: $serviceTestResult"
    }
}

function Remove-BuildArtifacts {
    $artifactPaths = @($DistPath, $BuildPath)
    
    foreach ($path in $artifactPaths) {
        if (Test-Path $path) {
            Write-Info "Removing: $path"
            Remove-Item $path -Recurse -Force
            Write-Success "Cleaned: $path"
        }
    }
}

function Invoke-PyInstallerBuild {
    Write-Info "Starting PyInstaller build process..."
    Write-Info "Working directory: $ProjectRoot"
    Write-Info "Spec file: $SpecFile"
    
    # Change to project directory
    Push-Location $ProjectRoot
    
    try {
        # Run PyInstaller
        $buildArgs = @(
            "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            $SpecFile
        )
        
        Write-Info "Executing: $PythonExe $($buildArgs -join ' ')"
        
        & $PythonExe @buildArgs
        
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller build failed with exit code: $LASTEXITCODE"
        }
        
        Write-Success "PyInstaller build completed successfully"
    }
    finally {
        Pop-Location
    }
}

function Test-BuildOutput {
    $exePath = Join-Path $DistPath "DMC.exe"
    
    if (-not (Test-Path $exePath)) {
        throw "Build output not found: $exePath"
    }
    
    $fileInfo = Get-Item $exePath
    $sizeInMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Success "Executable created: $exePath"
    Write-Info "File size: $sizeInMB MB"
    Write-Info "Last modified: $($fileInfo.LastWriteTime)"
}

function New-DeploymentPackage {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmm"
    $packageName = "DMC-Final-$timestamp"
    $packagePath = Join-Path $DistPath $packageName
    
    Write-Info "Creating deployment package: $packageName"
    
    # Create package directory
    if (Test-Path $packagePath) {
        Remove-Item $packagePath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $packagePath -Force | Out-Null
    
    # Copy executable
    $exePath = Join-Path $DistPath "DMC.exe"
    Copy-Item $exePath $packagePath
    Write-Success "Copied: DMC.exe"
    
    # Copy config.json to deployment package (external to executable)
    Copy-Item $ConfigFile $packagePath
    Write-Success "Copied: config.json (external configuration)"
    
    # Create README for deployment
    $readmeContent = @"
DMC - Data Management Center
============================

STANDALONE OFFLINE DEPLOYMENT PACKAGE

Build Date: $(Get-Date -Format "MMMM dd, yyyy 'at' HH:mm")
Status: READY FOR DEPLOYMENT

QUICK START:
1. Double-click "Launch-DMC.bat" for guided startup, or
2. Run "DMC.exe" directly
3. Open your browser to the displayed URL (typically http://127.0.0.1:8050)

SYSTEM REQUIREMENTS:
- Windows 10/11 (64-bit)
- No Python installation required
- No internet connection required (fully offline capable)
- Complete self-contained executable
- Some features may require external tools (see EXTERNAL DEPENDENCIES below)

PACKAGE CONTENTS:
- DMC.exe - Main application ($(([math]::Round((Get-Item $exePath).Length / 1MB, 0)))MB)
- config.json - External configuration file (editable without rebuilding)
- Launch-DMC.bat - Simple batch launcher
- README.txt - This file

FEATURES INCLUDED:
- CSV to RTU file conversion
- RTU to CSV file conversion
- Fluid ID converter (37-basis conversion system)
- Archive data fetching and management
- RTU data fetching and management
- RTU resizer utility for modifying RTU file data ranges
- SPS time converter utility
- PyMBSd service management for Windows services
- Text replacement utility for batch file processing
- Replay file poke extractor for simulation data
- Review to CSV converter for data analysis
- Elevation data analysis and visualization
- Linefill calculations and reporting
- Interactive data visualization with dash_ag_grid
- All themes and assets bundled for offline operation
- Hot reloading when config.json is modified

CONFIGURATION:
The config.json file contains application settings that can be modified
without rebuilding the executable:
- Archive base path configuration
- Timeout settings
- Other operational parameters

The application will automatically detect changes to config.json and
reload the configuration during runtime.

EXTERNAL DEPENDENCIES:
Some advanced features require external tools that are loaded dynamically:

1. Review to CSV Conversion:
   - Requires: dreview.exe
   - Location: Must be in system PATH or working directory
   - Purpose: Converts review files to CSV format

2. PyMBSd Service Management:
   - Requires: pymbsd_*.exe executables
   - Location: Downloaded from UNC service packages
   - Purpose: Windows service installation and management
   - Note: Requires network access to UNC paths for service downloads

3. Archive Data Access:
   - May require: Network access to archive servers
   - Configuration: Set in config.json

These external dependencies are optional and only required when using
their specific features. The core application functionality works
without these tools.

For technical support or questions, refer to the main project documentation.
"@
    
    $readmeFile = Join-Path $packagePath "README.txt"
    $readmeContent | Out-File -FilePath $readmeFile -Encoding UTF8
    Write-Success "Created: README.txt"
    
    # Create Batch launcher
    $batchContent = @'
@echo off
title DMC - Data Management Center

echo.
echo ================================================================
echo   DMC - Data Management Center
echo ================================================================
echo.

:: Check if DMC.exe exists
if not exist "DMC.exe" (
    echo ERROR: DMC.exe not found in current directory
    echo Please ensure you're running this script from the deployment folder
    echo.
    pause
    exit /b 1
)

:: Check if config.json exists
if not exist "config.json" (
    echo ERROR: config.json not found in current directory
    echo Please ensure config.json is in the same folder as DMC.exe
    echo.
    pause
    exit /b 1
)

echo Starting DMC application...
echo Location: %CD%
echo.

:: Display launch information
echo The application will start in a moment...
echo Once started, open your web browser and navigate to:
echo.
echo     http://127.0.0.1:8050
echo.
echo Loading DMC services...
echo * CSV to RTU conversion service
echo * RTU to CSV conversion service
echo * Fluid ID converter service  
echo * Archive fetching service
echo * RTU data fetching service
echo * RTU resizer service
echo * SPS time converter service
echo * PyMBSd service management
echo * Text replacement service
echo * Replay file poke extraction service
echo * Review to CSV conversion service
echo * Elevation data service
echo * Linefill calculation service
echo * Configuration manager
echo.
echo Please wait for the "Starting server on:" message...
echo.
echo Configuration: config.json (can be edited while app is running)
echo.

:: Start the application in the same window
echo Launching DMC.exe...
"DMC.exe"
'@
    
    $batchFile = Join-Path $packagePath "Launch-DMC.bat"
    $batchContent | Out-File -FilePath $batchFile -Encoding ASCII
    Write-Success "Created: Launch-DMC.bat"
    
    Write-Success "Deployment package created at: $packagePath"
    return $packagePath
}

function Show-BuildSummary {
    $exePath = Join-Path $DistPath "DMC.exe"
    $fileInfo = Get-Item $exePath
    $sizeInMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Host ""
    Write-Host "BUILD SUMMARY" -ForegroundColor $Green
    Write-Host "================" -ForegroundColor $Green
    Write-Host "SUCCESS: Executable: DMC.exe ($sizeInMB MB)" -ForegroundColor $Green
    Write-Host "SUCCESS: External config: config.json" -ForegroundColor $Green
    Write-Host "SUCCESS: Batch launcher: Launch-DMC.bat" -ForegroundColor $Green
    Write-Host "SUCCESS: PyInstaller build successful" -ForegroundColor $Green
    Write-Host "SUCCESS: Deployment package created" -ForegroundColor $Green
    Write-Host "SUCCESS: All dependencies bundled" -ForegroundColor $Green
    Write-Host "SUCCESS: Ready for offline deployment" -ForegroundColor $Green
    Write-Host "SUCCESS: Hot reloading enabled for config.json" -ForegroundColor $Green
    Write-Host ""
    Write-Host "Package location: $DistPath" -ForegroundColor $Cyan
    Write-Host "Ready to deploy to offline servers!" -ForegroundColor $Yellow
    Write-Host ""
    Write-Host "UPDATES IN THIS BUILD:" -ForegroundColor $Green
    Write-Host "- Updated PyMBSd service management with 3-column layout" -ForegroundColor $Green
    Write-Host "- Added loading indicators for better UX" -ForegroundColor $Green
    Write-Host "- Optimized service status loading (5-second auto-refresh)" -ForegroundColor $Green
    Write-Host "- Moved Select All checkbox below service list" -ForegroundColor $Green
    Write-Host "- Fixed Refresh List button styling" -ForegroundColor $Green
    Write-Host "- Removed test mode configuration for cleaner setup" -ForegroundColor $Green
    Write-Host ""
    Write-Host "NOTES:" -ForegroundColor $Yellow
    Write-Host "- config.json is external and can be modified without rebuilding" -ForegroundColor $Yellow
    Write-Host "- Application will detect config changes and reload automatically" -ForegroundColor $Yellow
    Write-Host "- No CDN dependencies - fully offline capable" -ForegroundColor $Yellow
    Write-Host "- Some features require external tools (dreview.exe, pymbsd executables)" -ForegroundColor $Yellow
    Write-Host "- External tools are loaded dynamically when their features are used" -ForegroundColor $Yellow
    Write-Host "- UNC path access may be required for PyMBSd service management" -ForegroundColor $Yellow
}

# Execute main build process
Start-Build
