$ErrorActionPreference = "Stop"

Write-Host "1/4 - Executando testes"
pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "2/4 - Limpando build anterior"
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

Write-Host "3/4 - Gerando aplicação portátil"
pyinstaller packaging/financeiro_dr.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:LOCALAPPDATA = "$env:TEMP\financeiro-local-smoke"
$env:APPDATA = "$env:TEMP\financeiro-roaming-smoke"
& ".\dist\FinanceiroPessoalDr\FinanceiroPessoalDr.exe" --smoke-test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "4/4 - Gerando instalador"
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { throw "Inno Setup 6 não encontrado." }
& $iscc "packaging\installer.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Build concluído: dist\installer\FinanceiroPessoalDr-Setup.exe"
