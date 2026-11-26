$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc)) {
    throw "csc.exe not found at $csc"
}
$icon = Join-Path $root 'assets\app_icon.ico'
$out = Join-Path $root 'AzurPromiliaSwitcher.exe'
$src = Join-Path $root 'Launcher.cs'

& $csc /nologo /target:winexe /optimize+ /win32icon:$icon /out:$out /reference:System.Windows.Forms.dll $src
if ($LASTEXITCODE -ne 0) {
    throw "csc.exe failed with exit code $LASTEXITCODE"
}
Write-Output "Built: $out"
