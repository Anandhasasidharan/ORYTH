$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m PyInstaller --clean --noconfirm ORYTH.spec
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
$package = Join-Path (Get-Location) 'dist/ORYTH-Windows-x64'
New-Item -ItemType Directory -Force -Path $package | Out-Null
Copy-Item 'dist/ORYTH.exe' $package
Copy-Item 'packaging/WINDOWS-START-HERE.txt' $package
Copy-Item 'THIRD_PARTY.md' $package
Compress-Archive -Path "$package/*" -DestinationPath 'dist/ORYTH-Windows-x64.zip' -Force
(Get-FileHash 'dist/ORYTH-Windows-x64.zip' -Algorithm SHA256).Hash.ToLower() + '  ORYTH-Windows-x64.zip' | Set-Content -Encoding ascii 'dist/SHA256SUMS.txt'
Write-Host 'Built dist/ORYTH-Windows-x64.zip'
