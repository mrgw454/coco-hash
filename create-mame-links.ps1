# create-mame-links.ps1
# Creates directory junctions from the MAME install folder into this project,
# so the generated hash file and software folder are live in MAME immediately
# after each run of generate_coco_hash.py with no copy step needed.
#
# MAME folder: %USERPROFILE%\mame\

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$MameDir    = Join-Path $env:USERPROFILE "mame"
$HashSrc    = Join-Path $ScriptDir "hash"
$SoftSrc    = Join-Path $ScriptDir "software"
$HashDest   = Join-Path $MameDir "hash"
$SoftDest   = Join-Path $MameDir "software"

if (-not (Test-Path $MameDir)) {
    Write-Host "MAME folder not found: $MameDir"
    exit 1
}

foreach ($pair in @(($HashSrc, $HashDest), ($SoftSrc, $SoftDest))) {
    $src, $dest = $pair

    if (-not (Test-Path $src)) {
        Write-Host "Source folder not found: $src  (run generate_coco_hash.py first)"
        continue
    }

    if (Test-Path $dest) {
        Write-Host "Removing existing: $dest"
        Remove-Item $dest -Recurse -Force
    }

    New-Item -ItemType Junction -Path $dest -Target $src | Out-Null
    Write-Host "Junction created: $dest -> $src"
}

Write-Host ""
Write-Host "Done."
