$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "未找到 .venv。请先运行：python scripts/bootstrap_dev.py --install"
}
& $Python scripts/bootstrap_dev.py
exit $LASTEXITCODE
