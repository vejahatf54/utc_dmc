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
        @{name = "plotly"; import = "plotly" },
        @{name = "flask"; import = "flask" },
        @{name = "sqlalchemy"; import = "sqlalchemy" },
        @{name = "pyodbc"; import = "pyodbc" },
        @{name = "requests"; import = "requests" }
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
    
    # Verify config.json exists
    if (-not (Test-Path $ConfigFile)) {
        throw "Config file not found: $ConfigFile"
    }
    Write-Success "Config file found: $ConfigFile"
    
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
    $testResult = & $PythonExe -c "
import components.sidebar
import components.home_page
import components.fluid_id_page
import components.csv_to_rtu_page
import components.fetch_archive_page
import components.fetch_rtu_data_page
import components.sps_time_converter_page
import components.elevation_page
import components.linefill_page
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
    
    # Test services
    Write-Info "Testing DMC services..."
    $serviceTestResult = & $PythonExe -c "
import services.config_manager
import services.csv_to_rtu_service
import services.date_range_service
import services.elevation_data_service
import services.exceptions
import services.fetch_archive_service
import services.fetch_rtu_data_service
import services.sps_time_converter_service
import services.fluid_id_service
import services.linefill_service
import services.onesource_service
import services.pipe_analysis_service
print('All services imported successfully')
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

PACKAGE CONTENTS:
- DMC.exe - Main application ($(([math]::Round((Get-Item $exePath).Length / 1MB, 0)))MB)
- config.json - External configuration file (editable without rebuilding)
- Launch-DMC.bat - Simple batch launcher
- README.txt - This file

FEATURES INCLUDED:
- CSV to RTU file conversion
- Fluid ID converter (37-basis conversion system)
- Archive data fetching and management
- RTU data fetching and management
- SPS time converter utility
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
echo * Fluid ID converter service  
echo * Archive fetching service
echo * RTU data fetching service
echo * SPS time converter service
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
    Write-Host "NOTES:" -ForegroundColor $Yellow
    Write-Host "- config.json is external and can be modified without rebuilding" -ForegroundColor $Yellow
    Write-Host "- Application will detect config changes and reload automatically" -ForegroundColor $Yellow
    Write-Host "- No CDN dependencies - fully offline capable" -ForegroundColor $Yellow
}

# Execute main build process
Start-Build
