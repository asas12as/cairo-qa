param(
    [string]$Config = "config.yaml",
    [switch]$Ingest
)

$projectRoot = Split-Path -Path $PSScriptRoot -Parent
Set-Location $projectRoot

if ($Ingest) {
    $csvPath = Join-Path $projectRoot "data\raw"
    $csvFile = Get-ChildItem $csvPath -Filter *.csv | Select-Object -First 1
    if (-not $csvFile) {
        Write-Host "No CSV files found in data\raw" -ForegroundColor Red
        exit 1
    }
    Write-Host "Ingesting: $($csvFile.FullName)" -ForegroundColor Green
    python main.py --config $Config --ingest $csvFile.FullName
} else {
    python main.py --config $Config
}
