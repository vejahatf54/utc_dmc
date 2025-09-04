# Test script to verify package dependencies
$PythonExe = ".\.venv\Scripts\python.exe"

Write-Host "Testing package verification..." -ForegroundColor Cyan

$requiredPackages = @(
    @{name="dash"; import="dash"},
    @{name="dash-mantine-components"; import="dash_mantine_components"},
    @{name="dash-ag-grid"; import="dash_ag_grid"},
    @{name="pandas"; import="pandas"},
    @{name="watchdog"; import="watchdog"}
)

foreach ($package in $requiredPackages) {
    $packageCheck = & $PythonExe -c "import $($package.import); print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: $($package.name): OK" -ForegroundColor Green
    } else {
        Write-Host "ERROR: $($package.name) failed: $packageCheck" -ForegroundColor Red
    }
}

Write-Host "Package verification complete!" -ForegroundColor Cyan
