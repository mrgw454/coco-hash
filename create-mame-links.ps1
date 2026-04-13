# create-mame-links.ps1 (CoCo)
#
# Creates individual symlinks/junctions for CoCo hash XMLs and software subdirs
# inside %USERPROFILE%\mame\hash\ and %USERPROFILE%\mame\software\ so multiple
# projects can coexist.
#
# Safe to run multiple times.  Converts old whole-directory junctions
# (created by earlier versions of this script) to real directories automatically.
# Will not remove real files or real directories at the destination — reports
# an error and skips them so you can decide what to do.
#
# File symlinks require Windows Developer Mode or admin rights; falls back to
# hard link, then plain copy with a warning.
# MAME folder: %USERPROFILE%\mame\

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$MameDir     = Join-Path $env:USERPROFILE "mame"
$HashSrc     = Join-Path $ScriptDir "hash"
$SoftSrc     = Join-Path $ScriptDir "software"
$MameHash    = Join-Path $MameDir "hash"
$MameSoft    = Join-Path $MameDir "software"
$script:Errors = 0

if (-not (Test-Path $MameDir)) {
    Write-Error "MAME folder not found: $MameDir"
    exit 1
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Err($msg) {
    Write-Host "  ERROR: $msg" -ForegroundColor Red
    $script:Errors++
}

function Write-Warn($msg) {
    Write-Host "  Warning: $msg" -ForegroundColor Yellow
}

# Ensure $path is a real directory (not a junction or symlink).
# Converts an existing junction/symlink to a real directory.
# Returns $false on failure.
function Ensure-RealDir($path) {
    $item = Get-Item $path -ErrorAction SilentlyContinue
    if ($item) {
        if ($item.LinkType) {
            Write-Host "  Converting $($item.LinkType) to real directory: $path"
            try {
                Remove-Item $path -Force -ErrorAction Stop
            } catch {
                Write-Err "Could not remove $($item.LinkType): $path — $_"
                return $false
            }
        } elseif (-not $item.PSIsContainer) {
            Write-Err "$path exists but is not a directory — cannot proceed."
            return $false
        } else {
            # Already a real directory — nothing to do
            return $true
        }
    }
    try {
        New-Item -ItemType Directory -Path $path -ErrorAction Stop | Out-Null
    } catch {
        Write-Err "Could not create directory: $path — $_"
        return $false
    }
    return $true
}

# Create a file link $destDir\<name> -> $src.
# Replaces an existing symlink or hard link (idempotent).
# Refuses to remove a real file.
# Falls back: SymbolicLink -> HardLink -> Copy (with warning).
function Link-XmlFile($src, $destDir) {
    $name = Split-Path $src -Leaf
    $dest = Join-Path $destDir $name
    $item = Get-Item $dest -ErrorAction SilentlyContinue
    if ($item) {
        if ($item.LinkType) {
            try { Remove-Item $dest -Force -ErrorAction Stop } catch {
                Write-Err "Could not remove existing link: $dest — $_"
                return
            }
        } else {
            Write-Err "$dest exists as a real file — skipping. Remove it manually to let this script manage it."
            return
        }
    }
    try {
        New-Item -ItemType SymbolicLink -Path $dest -Target $src -ErrorAction Stop | Out-Null
        Write-Host "  Linked: $name"
        return
    } catch {}
    try {
        New-Item -ItemType HardLink -Path $dest -Target $src -ErrorAction Stop | Out-Null
        Write-Host "  Hard-linked: $name"
        return
    } catch {}
    try {
        Copy-Item $src $dest -ErrorAction Stop
        Write-Warn "Copied (no symlink/hardlink support): $name — re-run this script after regenerating XML."
    } catch {
        Write-Err "Could not link or copy: $dest — $_"
    }
}

# Create a junction $destDir\<name> -> $src.
# Replaces an existing junction or symlink (idempotent).
# Refuses to remove a real directory.
function Link-SoftDir($src, $destDir) {
    $name = Split-Path $src -Leaf
    $dest = Join-Path $destDir $name
    $item = Get-Item $dest -ErrorAction SilentlyContinue
    if ($item) {
        if ($item.LinkType) {
            try { Remove-Item $dest -Force -ErrorAction Stop } catch {
                Write-Err "Could not remove existing link: $dest — $_"
                return
            }
        } elseif ($item.PSIsContainer) {
            Write-Err "$dest exists as a real directory — skipping. Remove it manually to let this script manage it."
            return
        } else {
            Write-Err "$dest exists but is not a directory or link — skipping."
            return
        }
    }
    try {
        New-Item -ItemType Junction -Path $dest -Target $src -ErrorAction Stop | Out-Null
        Write-Host "  Junction: $name\"
    } catch {
        Write-Err "Could not create junction: $dest -> $src — $_"
    }
}

# ---------------------------------------------------------------------------
# hash\
# ---------------------------------------------------------------------------

Write-Host "=== CoCo MAME links ==="
Write-Host ""
Write-Host "Hash directory: $MameHash"

if (Ensure-RealDir $MameHash) {
    $found = $false
    if (Test-Path $HashSrc) {
        foreach ($xml in Get-ChildItem -Path $HashSrc -Filter "*.xml" -ErrorAction SilentlyContinue) {
            Link-XmlFile $xml.FullName $MameHash
            $found = $true
        }
    }
    if (-not $found) { Write-Warn "No XML files found — run generate_coco_hash.py first." }
}
Write-Host ""

# ---------------------------------------------------------------------------
# software\
# ---------------------------------------------------------------------------

Write-Host "Software directory: $MameSoft"

if (Ensure-RealDir $MameSoft) {
    $found = $false
    if (Test-Path $SoftSrc) {
        foreach ($sub in Get-ChildItem -Path $SoftSrc -Directory -ErrorAction SilentlyContinue) {
            Link-SoftDir $sub.FullName $MameSoft
            $found = $true
        }
    }
    if (-not $found) { Write-Warn "No subdirs found — run generate_coco_hash.py first." }
}
Write-Host ""

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

if ($script:Errors -gt 0) {
    Write-Host "Completed with $($script:Errors) error(s) — review messages above." -ForegroundColor Red
    exit 1
}
Write-Host "Done."
