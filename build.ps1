# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '请先建立 .venv 并安装 requirements.txt。' }
$ffmpegPath = (Get-Command ffmpeg -ErrorAction Stop).Source
$ffprobePath = (Get-Command ffprobe -ErrorAction Stop).Source
$supportPath = Join-Path $PSScriptRoot '.build-support'
$licensePath = Join-Path $supportPath 'licenses'
New-Item -ItemType Directory -Path $licensePath -Force | Out-Null
foreach ($documentName in @('LICENSE', 'NOTICE', 'README.md', '使用说明.md', 'THIRD_PARTY_NOTICES.txt')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $documentName) -Destination $supportPath
}
$ffmpegRoot = Split-Path (Split-Path $ffmpegPath -Parent) -Parent
Copy-Item -LiteralPath (Join-Path $ffmpegRoot 'LICENSE') -Destination (Join-Path $licensePath 'FFmpeg-LICENSE.txt')
Get-ChildItem -LiteralPath '.venv\Lib\site-packages' -Directory -Filter '*.dist-info' | ForEach-Object {
    $packagePath = $_.FullName
    Get-ChildItem -LiteralPath $packagePath -Recurse -File | Where-Object { $_.Name -match '^(LICENSE|COPYING)' } | ForEach-Object {
        $relativePath = $_.FullName.Substring($packagePath.Length + 1)
        $destinationPath = Join-Path (Join-Path $licensePath (Split-Path $packagePath -Leaf)) $relativePath
        New-Item -ItemType Directory -Path (Split-Path $destinationPath -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destinationPath
    }
}
$basePythonPath = & $pythonPath -c 'import sys; print(sys.base_prefix)'
foreach ($licenseName in @('LICENSE.txt', 'LICENSE')) {
    $pythonLicense = Join-Path $basePythonPath $licenseName
    if (Test-Path -LiteralPath $pythonLicense) {
        Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licensePath 'Python-LICENSE.txt')
        break
    }
}
& $pythonPath -m PyInstaller --noconfirm --clean --windowed --onefile --name '视频倍速工坊' --collect-all customtkinter --add-binary "${ffmpegPath};tools" --add-binary "${ffprobePath};tools" --add-data "${supportPath};notices" app.py
if ($LASTEXITCODE -ne 0) { throw '打包失败。' }
$executablePath = Join-Path $PSScriptRoot 'dist\视频倍速工坊.exe'
Compress-Archive -LiteralPath $supportPath -DestinationPath (Join-Path $PSScriptRoot 'dist\许可证与说明.zip') -Force
Write-Output "单文件版已生成：$executablePath"
