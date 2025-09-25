#Requires -Version 5.0

<#
.SYNOPSIS
    WUTC Application - Nuitka Build Script

.DESCRIPTION
    This script builds the WUTC application as a standalone executable using Nuitka
    and creates a complete deployment package for offline servers.
    Config.json is kept external to the executable for easy configuration changes.

.PARAMETER Clean
    Performs a clean build by removing previous build artifacts

.PARAMETER Debug
    Builds with debug symbols and verbose output

.EXAMPLE
    .\build-nuitka.ps1
    .\build-nuitka.ps1 -Clean
    .\build-nuitka.ps1 -Clean -Debug
#>

param(
    [switch]$Clean = $false,
    [switch]$Debug = $false
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Project paths
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$DistPath = Join-Path $ProjectRoot "dist"
$BuildPath = Join-Path $ProjectRoot "build"
$NuitkaBuildPath = Join-Path $ProjectRoot "nuitka-build"
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
    Write-Host "✓ $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $Red
}

function Test-Prerequisites {
    Write-Section "Checking Prerequisites"
    
    # Check if virtual environment exists
    if (-not (Test-Path $VenvPath)) {
        Write-Error "Virtual environment not found at $VenvPath"
        Write-Host "Please create a virtual environment first:" -ForegroundColor $Yellow
        Write-Host "python -m venv .venv" -ForegroundColor $Gray
        Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor $Gray
        Write-Host "pip install -r requirements.txt" -ForegroundColor $Gray
        exit 1
    }
    Write-Success "Virtual environment found"
    
    # Check if Python executable exists
    if (-not (Test-Path $PythonExe)) {
        Write-Error "Python executable not found at $PythonExe"
        exit 1
    }
    Write-Success "Python executable found"
    
    # Check if Nuitka is installed
    try {
        & $PythonExe -c "import nuitka; print('Nuitka version:', nuitka.__version__)" 2>$null
        Write-Success "Nuitka is installed"
    }
    catch {
        Write-Warning "Nuitka not found, installing..."
        try {
            & $PipExe install nuitka
            Write-Success "Nuitka installed successfully"
        }
        catch {
            Write-Error "Failed to install Nuitka: $_"
            exit 1
        }
    }
    
    # Check if app.py exists
    if (-not (Test-Path (Join-Path $ProjectRoot "app.py"))) {
        Write-Error "app.py not found in project root"
        exit 1
    }
    Write-Success "app.py found"
    
    # Check if config.json exists
    if (-not (Test-Path $ConfigFile)) {
        Write-Error "config.json not found in project root"
        exit 1
    }
    Write-Success "config.json found"
}

function Clear-BuildArtifacts {
    Write-Section "Cleaning Build Artifacts"
    
    $pathsToClean = @($DistPath, $BuildPath, $NuitkaBuildPath)
    
    foreach ($path in $pathsToClean) {
        if (Test-Path $path) {
            Write-Host "Removing $path..." -ForegroundColor $Gray
            Remove-Item $path -Recurse -Force
            Write-Success "Removed $path"
        }
    }
    
    # Clean Python cache files
    Write-Host "Removing Python cache files..." -ForegroundColor $Gray
    Get-ChildItem -Path $ProjectRoot -Recurse -Name "__pycache__" -Directory | ForEach-Object {
        $fullPath = Join-Path $ProjectRoot $_
        Remove-Item $fullPath -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Get-ChildItem -Path $ProjectRoot -Recurse -Name "*.pyc" -File | ForEach-Object {
        $fullPath = Join-Path $ProjectRoot $_
        Remove-Item $fullPath -Force -ErrorAction SilentlyContinue
    }
    
    Write-Success "Python cache files cleaned"
}

function Build-WithNuitka {
    Write-Section "Building with Nuitka"
    
    # Create dist directory if it doesn't exist
    if (-not (Test-Path $DistPath)) {
        New-Item -ItemType Directory -Path $DistPath -Force | Out-Null
    }
    
    # Build Nuitka command
    $nuitkaArgs = @(
        "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--follow-imports",
        "--include-data-dir=assets=assets",
        "--include-data-dir=components=components",
        "--include-data-dir=services=services",
        "--include-data-dir=domain=domain",
        "--include-data-dir=controllers=controllers",
        "--include-data-dir=core=core",
        "--include-data-dir=validation=validation",
        "--include-data-dir=sql=sql",
        "--include-data-file=requirements.txt=requirements.txt",
        "--include-package=dash",
        "--include-package=dash_ag_grid",
        "--include-package=dash_mantine_components",
        "--include-package=dash_bootstrap_components",
        "--include-package=plotly",
        "--include-package=pandas",
        "--include-package=numpy",
        "--include-package=oracledb",
        "--include-package=cryptography",
        "--include-package=bcrypt",
        "--include-package=flask",
        "--include-package=flask_login",
        "--include-package=sqlalchemy",
        "--include-package=pyodbc",
        "--include-package=openpyxl",
        "--include-package=scipy",
        "--include-package=matplotlib",
        "--include-package=numba",
        "--include-package=llvmlite",
        "--plugin-enable=multiprocessing",
        "--plugin-enable=numpy",
        "--output-dir=$DistPath",
        "--output-filename=wutc.exe"
    )
    
    # Add debug flags if requested
    if ($Debug) {
        $nuitkaArgs += @(
            "--debug",
            "--verbose"
        )
    }
    else {
        $nuitkaArgs += @(
            "--quiet"
        )
    }
    
    # Add Windows-specific options
    if ($IsWindows -or $Env:OS -eq "Windows_NT") {
        $nuitkaArgs += @(
            "--windows-console-mode=disable",
            "--windows-icon-from-ico=assets/logo.png"
        )
    }
    
    # Add the main script
    $nuitkaArgs += "app.py"
    
    Write-Host "Running Nuitka with the following command:" -ForegroundColor $Gray
    Write-Host "python $($nuitkaArgs -join ' ')" -ForegroundColor $Gray
    Write-Host ""
    
    try {
        $buildStartTime = Get-Date
        & $PythonExe @nuitkaArgs
        $buildEndTime = Get-Date
        $buildDuration = $buildEndTime - $buildStartTime
        
        Write-Success "Nuitka build completed in $($buildDuration.TotalMinutes.ToString('F1')) minutes"
    }
    catch {
        Write-Error "Nuitka build failed: $_"
        exit 1
    }
}

function Copy-ConfigurationFiles {
    Write-Section "Copying Configuration Files"
    
    # Copy config.json to the dist directory (next to the executable)
    $configDestination = Join-Path $DistPath "config.json"
    Copy-Item $ConfigFile $configDestination -Force
    Write-Success "Copied config.json to dist directory"
    
    # Copy requirements.txt for reference
    $reqDestination = Join-Path $DistPath "requirements.txt"
    Copy-Item (Join-Path $ProjectRoot "requirements.txt") $reqDestination -Force
    Write-Success "Copied requirements.txt to dist directory"
    
    # Create a simple README for the distribution
    $readmeContent = @"
WUTC Application - Nuitka Build
===============================

This is a standalone executable built with Nuitka.

Files:
- wutc.exe: The main application executable
- config.json: Configuration file (can be edited)
- requirements.txt: List of Python dependencies (for reference)

To run the application:
1. Ensure config.json is properly configured
2. Double-click wutc.exe or run from command line

Build Information:
- Build Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
- Build Tool: Nuitka
- Python Version: $((& $PythonExe --version) 2>&1)

"@
    
    $readmePath = Join-Path $DistPath "README.txt"
    $readmeContent | Out-File -FilePath $readmePath -Encoding UTF8
    Write-Success "Created README.txt in dist directory"
}

function Test-Executable {
    Write-Section "Testing Executable"
    
    $exePath = Join-Path $DistPath "wutc.exe"
    
    if (-not (Test-Path $exePath)) {
        Write-Error "Executable not found at $exePath"
        return $false
    }
    
    Write-Success "Executable found at $exePath"
    
    # Get file size
    $fileSize = (Get-Item $exePath).Length
    $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
    Write-Host "Executable size: $fileSizeMB MB" -ForegroundColor $Gray
    
    # Quick test - try to run the executable with --help (if supported)
    # Note: This might not work for all Dash applications
    Write-Host "Executable appears to be built successfully" -ForegroundColor $Green
    Write-Warning "Manual testing recommended - run the executable to verify it works correctly"
    
    return $true
}

function Show-Summary {
    Write-Section "Build Summary" $Green
    
    $exePath = Join-Path $DistPath "wutc.exe"
    $configPath = Join-Path $DistPath "config.json"
    
    Write-Host "Build completed successfully!" -ForegroundColor $Green
    Write-Host ""
    Write-Host "Output files:" -ForegroundColor $Cyan
    Write-Host "  Executable: $exePath" -ForegroundColor $Gray
    Write-Host "  Configuration: $configPath" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor $Cyan
    Write-Host "  1. Test the executable by running it" -ForegroundColor $Gray
    Write-Host "  2. Verify all functionality works as expected" -ForegroundColor $Gray
    Write-Host "  3. Deploy the dist folder contents to target systems" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "Note: The executable includes all Python dependencies but requires" -ForegroundColor $Yellow
    Write-Host "      config.json to be present in the same directory." -ForegroundColor $Yellow
}

# Main execution
try {
    Write-Host "WUTC Application - Nuitka Build Script" -ForegroundColor $Cyan
    Write-Host "=====================================" -ForegroundColor $Gray
    
    Test-Prerequisites
    
    if ($Clean) {
        Clear-BuildArtifacts
    }
    
    Build-WithNuitka
    Copy-ConfigurationFiles
    
    if (Test-Executable) {
        Show-Summary
    }
    else {
        Write-Error "Build completed but executable testing failed"
        exit 1
    }
}
catch {
    Write-Error "Build failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor $Red
    exit 1
}