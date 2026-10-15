param([switch]$Install)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($Install -or !(Test-Path backend/.venv/Scripts/python.exe)) {
    py -3.12 -m venv backend/.venv
    if ($LASTEXITCODE -ne 0) { throw 'ติดตั้ง Python 3.12 และ Python Launcher ก่อน' }
    & ./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'ติดตั้ง Python dependencies ไม่สำเร็จ' }
}
if ($Install -or !(Test-Path frontend/dist/index.html)) {
    Push-Location frontend
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci ไม่สำเร็จ' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Build ไม่สำเร็จ' }
    Pop-Location
}
Write-Host 'Smart PDF Editor: http://127.0.0.1:8000 (Ctrl+C เพื่อหยุด)'
Push-Location backend
try { & ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log }
finally { Pop-Location }
