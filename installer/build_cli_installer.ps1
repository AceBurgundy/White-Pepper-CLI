<#
.SYNOPSIS
    Compiles the Inno Setup installer for the White Pepper CLI standalone engine.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    White Pepper Headless CLI — Installer Builder         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate Inno Setup Compiler (ISCC.exe)
Write-Host "`n[1/2] Searching for Inno Setup 6 compiler (ISCC.exe)..." -ForegroundColor Yellow
$IsccCandidatePaths = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles (x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$IsccPath = $null
foreach ($Path in $IsccCandidatePaths) {
    if ($Path -and (Test-Path $Path)) {
        $IsccPath = $Path
        break
    }
}

if (-not $IsccPath) {
    Write-Error "Could not find Inno Setup 6 compiler (ISCC.exe). Please install Inno Setup 6 or add it to PATH."
}
Write-Host "Found Inno Setup compiler: $IsccPath" -ForegroundColor Green

# 2. Compile Installer
Write-Host "`n[2/2] Compiling CLI installer wizard via Inno Setup..." -ForegroundColor Yellow
$IssPath = "$ProjectRoot\installer\white_pepper_cli_setup.iss"
$OutputDir = "$ProjectRoot\installer\output"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

& $IsccPath $IssPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

$InstallerFile = Get-ChildItem -Path $OutputDir -Filter "WhitePepper-CLI-Setup-*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($InstallerFile) {
    $SizeKb = [math]::Round($InstallerFile.Length / 1KB, 2)
    Write-Host "`n[SUCCESS] CLI Installer successfully compiled!" -ForegroundColor Green
    Write-Host "  File : $($InstallerFile.FullName)" -ForegroundColor Cyan
    Write-Host "  Size : $SizeKb KB" -ForegroundColor Cyan
} else {
    Write-Error "Installer file was not generated in $OutputDir"
}
