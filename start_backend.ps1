$env:DATABASE_URL = "postgresql://admin_user:admin_lozinka@localhost:5432/numeracija"
$env:CORS_ALLOW_ORIGINS = "*"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

& "$root\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
