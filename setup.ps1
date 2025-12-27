# Setup script for Verdi Desouk POS on Windows PowerShell
# - Creates a virtual environment .venv
# - Upgrades pip
# - Installs requirements
# Usage: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

# Detect python (require 3.12 for Pillow wheel on Windows)
$python = "python"
try {
    $verStr = & $python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
} catch {
    Write-Error "Python is not installed or not in PATH. Install Python 3.12 first."; exit 1
}

if ($verStr -ne "3.12") {
    Write-Error "Detected Python $verStr. Please use Python 3.12 to install Pillow from wheels."; exit 1
}

Write-Host "Using Python executable: $python (version $verStr)" -ForegroundColor Cyan

# Create venv if missing
if (-not (Test-Path .venv)) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $python -m venv .venv
} else {
    Write-Host ".venv already exists, skipping creation." -ForegroundColor Yellow
}

# Activate venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "Activation script not found: $venvActivate"; exit 1
}
. $venvActivate

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements (force binary for Pillow)
Write-Host "Installing requirements..." -ForegroundColor Cyan
python -m pip install --only-binary=:all: -r requirements.txt

Write-Host "Setup complete. To run the app:" -ForegroundColor Green
Write-Host "`t.\\.venv\\Scripts\\activate" -ForegroundColor Gray
Write-Host "`tpython app.py" -ForegroundColor Gray
