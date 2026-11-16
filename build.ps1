# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '请先建立 .venv 并安装 requirements.txt。' }
$ffmpegPath = (Get-Command ffmpeg -ErrorAction Stop).Source
$ffprobePath = (Get-Command ffprobe -ErrorAction Stop).Source
& $pythonPath -m PyInstaller --noconfirm --clean --windowed --onedir --name '视频倍速工坊' --collect-all customtkinter --add-binary "${ffmpegPath};tools" --add-binary "${ffprobePath};tools" app.py
if ($LASTEXITCODE -ne 0) { throw '打包失败。' }
$releasePath = Join-Path $PSScriptRoot 'dist\视频倍速工坊'
foreach ($documentName in @('LICENSE', 'NOTICE', 'README.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $documentName) -Destination $releasePath
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '使用说明.md') -Destination $releasePath
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD_PARTY_NOTICES.txt') -Destination $releasePath
$licensePath = Join-Path $releasePath 'licenses'
New-Item -ItemType Directory -Path $licensePath -Force | Out-Null
$ffmpegRoot = Split-Path (Split-Path $ffmpegPath -Parent) -Parent
Copy-Item -LiteralPath (Join-Path $ffmpegRoot 'LICENSE') -Destination (Join-Path $licensePath 'FFmpeg-LICENSE.txt')
Get-ChildItem -LiteralPath '.venv\Lib\site-packages' -Directory -Filter '*.dist-info' | ForEach-Object {
    $packagePath = $_.FullName
    Get-ChildItem -LiteralPath $packagePath -Recurse -File | Where-Object { $_.Name -match '^(LICENSE|COPYING)' } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $licensePath ($_.Directory.Parent.Name + '-' + $_.Name))
    }
}
Write-Output "便携版已生成：$releasePath"
