# =========================================================
# GOOD DEEDS - NEW USER TEST MODE
# =========================================================

# Always work from the folder containing this script
Set-Location $PSScriptRoot

$dataFile = Join-Path $PSScriptRoot "good_deeds_data.json"
$appFile = Join-Path $PSScriptRoot "app.py"

# Make sure the saved data exists
if (!(Test-Path $dataFile)) {
    Write-Host "ERROR: good_deeds_data.json was not found." -ForegroundColor Red
    Write-Host "Make sure newuser.ps1 is in the same folder as app.py."
    pause
    exit
}

# Load existing data
$data = Get-Content $dataFile -Raw | ConvertFrom-Json

# Reset ONLY the onboarding/login setup.
# Everything else stays untouched.
$data.onboarding_replay_version = 0

# Save the data back
$json = $data | ConvertTo-Json -Depth 20

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $dataFile,
    $json,
    $utf8
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " GOOD DEEDS - NEW USER TEST MODE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your saved data has NOT been deleted." -ForegroundColor Cyan
Write-Host ""
Write-Host "Preserved:" -ForegroundColor Yellow
Write-Host "  Points"
Write-Host "  Good-deed history"
Write-Host "  Custom good deeds"
Write-Host "  Custom rewards"
Write-Host "  Reward history"
Write-Host "  Child details"
Write-Host "  Settings"
Write-Host ""
Write-Host "The app will now start as a new user." -ForegroundColor Green
Write-Host ""

# Start Streamlit
streamlit run $appFile
