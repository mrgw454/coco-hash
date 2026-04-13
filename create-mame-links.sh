#!/bin/bash
# create-mame-links.sh (CoCo)
#
# Creates individual symlinks for CoCo hash XMLs and software subdirs inside
# ~/.mame/hash/ and ~/.mame/software/ so multiple projects can coexist.
#
# Safe to run multiple times.  Converts old whole-directory symlinks
# (created by earlier versions of this script) to real directories automatically.
# Will not remove real files or real directories at the destination — reports
# an error and skips them so you can decide what to do.

SCRIPTPATH=$(dirname -- "$(readlink -f -- "$0")")
MAME_HASH="$HOME/.mame/hash"
MAME_SOFTWARE="$HOME/.mame/software"
ERRORS=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

err()  { echo "  ERROR: $*" >&2; ERRORS=$((ERRORS + 1)); }
warn() { echo "  Warning: $*"; }

# Ensure a path is a real directory (not a symlink).
# If it is a directory symlink, remove the symlink and create a real dir.
# Returns 1 on failure so the caller can abort that section.
ensure_real_dir() {
    local dir="$1"
    if [ -L "$dir" ]; then
        echo "  Converting directory symlink to real directory: $dir"
        if ! rm "$dir"; then
            err "Could not remove symlink: $dir"
            return 1
        fi
    elif [ -e "$dir" ] && [ ! -d "$dir" ]; then
        err "$dir exists but is not a directory — cannot proceed."
        return 1
    fi
    if ! mkdir -p "$dir"; then
        err "Could not create directory: $dir"
        return 1
    fi
    return 0
}

# Create a symlink $MAME_HASH/<name> -> $src.
# Replaces an existing symlink (idempotent).
# Refuses to remove a real file — reports error and skips.
link_xml() {
    local src="$1"
    local name
    name=$(basename "$src")
    local dest="$MAME_HASH/$name"

    if [ -L "$dest" ]; then
        rm "$dest" || { err "Could not remove existing symlink: $dest"; return 1; }
    elif [ -e "$dest" ]; then
        err "$dest exists as a real file — skipping. Remove it manually to let this script manage it."
        return 1
    fi

    if ln -s "$src" "$dest"; then
        echo "  Linked: $name"
    else
        err "Could not create symlink: $dest -> $src"
        return 1
    fi
}

# Create a symlink $MAME_SOFTWARE/<name> -> $src.
# Replaces an existing symlink (idempotent).
# Refuses to remove a real directory — reports error and skips.
link_softdir() {
    local src="${1%/}"
    local name
    name=$(basename "$src")
    local dest="$MAME_SOFTWARE/$name"

    if [ -L "$dest" ]; then
        rm "$dest" || { err "Could not remove existing symlink: $dest"; return 1; }
    elif [ -d "$dest" ]; then
        err "$dest exists as a real directory — skipping. Remove it manually to let this script manage it."
        return 1
    elif [ -e "$dest" ]; then
        err "$dest exists but is not a symlink or directory — skipping."
        return 1
    fi

    if ln -s "$src" "$dest"; then
        echo "  Linked: $name/"
    else
        err "Could not create symlink: $dest -> $src"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# hash/
# ---------------------------------------------------------------------------

echo "=== CoCo MAME links ==="
echo

echo "Hash directory: $MAME_HASH"
if ensure_real_dir "$MAME_HASH"; then
    found=0
    for xml in "$SCRIPTPATH/hash/"*.xml; do
        [ -f "$xml" ] || continue
        link_xml "$xml"
        found=1
    done
    [ "$found" -eq 0 ] && warn "No XML files found in $SCRIPTPATH/hash/ — run generate_coco_hash.py first."
fi
echo

# ---------------------------------------------------------------------------
# software/
# ---------------------------------------------------------------------------

echo "Software directory: $MAME_SOFTWARE"
if ensure_real_dir "$MAME_SOFTWARE"; then
    found=0
    for subdir in "$SCRIPTPATH"/software/*/; do
        [ -d "$subdir" ] || continue
        link_softdir "$subdir"
        found=1
    done
    [ "$found" -eq 0 ] && warn "No subdirs found in $SCRIPTPATH/software/ — run generate_coco_hash.py first."
fi
echo

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

if [ "$ERRORS" -gt 0 ]; then
    echo "Completed with $ERRORS error(s) — review messages above." >&2
    exit 1
fi
echo "Done!"
echo
