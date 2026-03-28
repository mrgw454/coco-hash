#!/usr/bin/env python3
"""
generate_coco_hash.py

Generate a MAME coco_flop.xml software list from Color Computer Archive disk games.
Downloads DSK images from the Games section of colorcomputerarchive.com, inspects
each disk using 'decb' (ToolShed) to determine the correct BASIC load command,
hashes the files, and writes a MAME-compatible software list XML.

Requirements:
    Python 3.8+, decb (ToolShed) in PATH
    ToolShed: https://sourceforge.net/projects/toolshed/

Usage:
    python generate_coco_hash.py [options]

Options:
    --no-download   Skip downloading; process existing archive/ folder
    --deploy        Copy output XML to MAME hash directory
    --verbose       Show per-disk detail during processing
    --output FILE   Output path (default: hash/coco_flop.xml)
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from collections import namedtuple
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import unquote, urljoin
from urllib.request import urlopen, urlretrieve

# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------

IS_WINDOWS = sys.platform == 'win32'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR   = Path(__file__).parent
ARCHIVE_DIR  = SCRIPT_DIR / 'archive'
DOWNLOAD_DIR = SCRIPT_DIR / 'downloads'
HASH_DIR     = SCRIPT_DIR / 'hash'
OUTPUT_XML   = HASH_DIR / 'coco_flop.xml'

if IS_WINDOWS:
    _appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    MAME_HASH_DIR = _appdata / 'MAME' / 'hash'
else:
    MAME_HASH_DIR = Path.home() / '.mame' / 'hash'

# ---------------------------------------------------------------------------
# Archive source
# ---------------------------------------------------------------------------

GAMES_URL = 'https://colorcomputerarchive.com/repo/Disks/Games/'

# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

EXCLUDE_PATTERNS = [
    'translations', 'protected', 'os-9', 'os9', 'disto', 'sdc',
    'burke', 'bible', 'cocovga', 'french', 'portuguese', 'dragon32',
]

def should_exclude(path_str):
    low = path_str.lower()
    return any(pat in low for pat in EXCLUDE_PATTERNS)

# ---------------------------------------------------------------------------
# Download / extract
# ---------------------------------------------------------------------------

class _LinkParser(HTMLParser):
    """Collect href links from an Apache directory listing."""
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href and not href.startswith('?') and not href.startswith('/') and href != '../':
                self.links.append(href)


def scrape_games(verbose=False):
    """
    Recursively scrape GAMES_URL for ZIP and DSK file URLs.
    Returns list of (url, filename) tuples.
    """
    results = []
    _scrape(GAMES_URL, results, depth=0, verbose=verbose)
    return results


def _scrape(url, results, depth, verbose, max_depth=6):
    if depth > max_depth:
        return
    if verbose:
        print(f'  Scanning: {url}')
    try:
        with urlopen(url, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except URLError as exc:
        print(f'  Warning: could not fetch {url}: {exc}')
        return

    parser = _LinkParser()
    parser.feed(html)

    for href in parser.links:
        decoded = unquote(href)
        if should_exclude(decoded):
            continue
        full_url = urljoin(url, href)
        if href.endswith('/'):
            _scrape(full_url, results, depth + 1, verbose, max_depth)
        elif decoded.lower().endswith('.zip') or decoded.lower().endswith('.dsk'):
            results.append((full_url, decoded))


def download_archives(urls, verbose=False):
    """Download ZIP/DSK files into DOWNLOAD_DIR, skipping files already present."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    new_count = 0
    for url, filename in urls:
        dest = DOWNLOAD_DIR / Path(filename).name
        if dest.exists():
            if verbose:
                print(f'  Cached:  {dest.name}')
            continue
        print(f'  Download: {dest.name}')
        try:
            urlretrieve(url, dest)
            new_count += 1
        except URLError as exc:
            print(f'  Error downloading {dest.name}: {exc}')
    print(f'  {new_count} new file(s) downloaded.')


def extract_archives(verbose=False):
    """
    Extract ZIPs from DOWNLOAD_DIR into ARCHIVE_DIR (flat, preserving internal structure).
    Also handles bare DSK files.  All DSK filenames are lowercased.
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for zpath in sorted(DOWNLOAD_DIR.glob('*.zip')):
        try:
            with zipfile.ZipFile(zpath) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    # Preserve internal path structure (game folder inside ZIP)
                    target = ARCHIVE_DIR / member.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        if verbose:
                            print(f'  Exists:  {member.filename}')
                        continue
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if verbose:
                        print(f'  Extract: {member.filename}')
        except zipfile.BadZipFile as exc:
            print(f'  Bad ZIP {zpath.name}: {exc}')

    # Bare DSK files downloaded directly
    for dsk in sorted(DOWNLOAD_DIR.glob('*.dsk')):
        dest = ARCHIVE_DIR / dsk.stem / dsk.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(dsk, dest)

    # Lowercase all DSK filenames
    for dsk in ARCHIVE_DIR.rglob('*'):
        if dsk.is_file() and dsk.suffix.lower() == '.dsk' and dsk.name != dsk.name.lower():
            dsk.rename(dsk.parent / dsk.name.lower())

# ---------------------------------------------------------------------------
# Disk inspection (decb)
# ---------------------------------------------------------------------------

FileEntry = namedtuple('FileEntry', ['name', 'ext', 'ftype'])

# DECB file type codes
_FTYPE_BAS_TOKEN = '0'   # tokenized BASIC
_FTYPE_BAS_ASCII = '1'   # ASCII BASIC
_FTYPE_BINARY    = '2'   # machine language / binary


def run_decb_dir(dsk_path):
    """
    Run 'decb dir' on dsk_path.
    Returns (list[FileEntry], error_str).  On success error_str is None.
    """
    try:
        result = subprocess.run(
            ['decb', 'dir', str(dsk_path)],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        return None, "'decb' not found in PATH"
    except subprocess.TimeoutExpired:
        return None, 'decb timed out'

    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip()
        return None, msg or f'decb returned {result.returncode}'

    entries = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith('Directory of'):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        entries.append(FileEntry(name=parts[0], ext=parts[1], ftype=parts[2]))

    return entries, None

# ---------------------------------------------------------------------------
# Load command determination
# ---------------------------------------------------------------------------

# File names (no extension) that are known program entry points
ENTRY_NAMES = frozenset({
    'RUNME', 'AUTOEXEC', 'AUTO', 'AUTORUN',
    'START', 'MAIN', 'MENU', 'LOADER', 'LOAD', 'BOOT',
})


def _make_command(entry):
    """Build the BASIC command string to launch a FileEntry."""
    if entry.ext == 'BAS' or entry.ftype in (_FTYPE_BAS_TOKEN, _FTYPE_BAS_ASCII):
        return f'RUN"{entry.name}"'
    else:
        return f'LOADM"{entry.name}":EXEC'


def determine_load_command(entries, dsk_stem):
    """
    Pick the best load command for a disk given its file listing.

    Returns (command_str, confidence) where confidence is one of:
        'sure'       — single file, known entry point, or disk-name match
        'guess'      — one BAS among BINs (BAS is the loader)
        'ambiguous'  — multiple candidates; used first, flag for review
        'none'       — no executable files on disk
    """
    execs = [e for e in entries if e.ext in ('BAS', 'BIN')]

    if not execs:
        return None, 'none'

    if len(execs) == 1:
        return _make_command(execs[0]), 'sure'

    # Known entry-point name
    for e in execs:
        if e.name.upper() in ENTRY_NAMES:
            return _make_command(e), 'sure'

    # File whose name matches the DSK stem
    stem_up = dsk_stem.upper()
    for e in execs:
        if e.name.upper() == stem_up:
            return _make_command(e), 'sure'

    bas  = [e for e in execs if e.ext == 'BAS']
    bins = [e for e in execs if e.ext == 'BIN']

    # One BAS with any BINs → BAS is the loader program
    if len(bas) == 1 and bins:
        return _make_command(bas[0]), 'guess'

    if len(bas) == 1:
        return _make_command(bas[0]), 'sure'

    if len(bins) == 1:
        return _make_command(bins[0]), 'sure'

    # Multiple of same type — use first, flag ambiguous
    first = bas[0] if bas else bins[0]
    return _make_command(first), 'ambiguous'

# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def hash_file(path):
    """Return (sha1_hex, crc32_8hex) for a file."""
    sha1 = hashlib.sha1()
    crc  = 0
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            sha1.update(chunk)
            crc = zlib.crc32(chunk, crc)
    return sha1.hexdigest(), f'{crc & 0xFFFFFFFF:08x}'

# ---------------------------------------------------------------------------
# Folder metadata
# ---------------------------------------------------------------------------

_COCO3_RE = re.compile(r'\(coco\s*3\)', re.IGNORECASE)


def parse_folder_metadata(folder_name):
    """
    Parse 'Game Title (Publisher) (Coco 3)' folder names.
    Returns (description, publisher, compatibility).
    """
    is_coco3 = bool(_COCO3_RE.search(folder_name))

    # Strip CoCo 3 marker
    name = _COCO3_RE.sub('', folder_name).strip()

    # Last parenthesized group = publisher
    pub_match = re.search(r'\(([^)]+)\)\s*$', name)
    if pub_match:
        publisher   = pub_match.group(1).strip()
        description = name[:pub_match.start()].strip()
    else:
        publisher   = 'unknown'
        description = name.strip()

    compatibility = 'COCO3' if is_coco3 else 'COCO,COCO3'
    return description, publisher, compatibility


def make_xml_name(dsk_stem):
    """Convert a DSK filename stem into a valid MAME software name."""
    s = dsk_stem.lower()
    s = re.sub(r'[^a-z0-9]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or 'unknown'

# ---------------------------------------------------------------------------
# XML generation
# ---------------------------------------------------------------------------

_XML_HEADER = (
    '<?xml version="1.0"?>\n'
    '<!DOCTYPE softwarelist SYSTEM "softwarelist.dtd">\n\n'
    '<softwarelist name="coco_flop" '
    'description="Tandy Radio Shack Color Computer disk images">\n'
)
_XML_FOOTER = '\n</softwarelist>\n'


def _esc_text(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _esc_attr(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def build_xml_entry(name, description, publisher, usage, compatibility,
                    dsk_filename, filesize, crc32, sha1):
    t = '\t'
    lines = [
        f'{t}<software name="{name}">',
        f'{t}{t}<description>{_esc_text(description)}</description>',
        f'{t}{t}<year>19xx</year>',
        f'{t}{t}<publisher>{_esc_text(publisher)}</publisher>',
    ]
    if usage:
        lines.append(f'{t}{t}<info name="usage" value="{_esc_attr(usage)}" />')
    lines += [
        f'{t}{t}<sharedfeat name="compatibility" value="{compatibility}" />',
        f'{t}{t}<part name="flop0" interface="floppy_5_25">',
        f'{t}{t}{t}<dataarea name="flop" size="{filesize}">',
        f'{t}{t}{t}{t}<rom name="{dsk_filename}" size="{filesize}" '
        f'crc="{crc32}" sha1="{sha1}" offset="0" />',
        f'{t}{t}{t}</dataarea>',
        f'{t}{t}</part>',
        f'{t}</software>',
        '',
    ]
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
# DSK file collection
# ---------------------------------------------------------------------------

def collect_dsk_files():
    """
    Walk ARCHIVE_DIR and yield (dsk_path, folder_name) for each DSK found
    in a game subfolder, skipping excluded folders.
    """
    for folder in sorted(ARCHIVE_DIR.iterdir()):
        if not folder.is_dir():
            continue
        if should_exclude(folder.name):
            continue
        dsks = sorted(f for f in folder.iterdir() if f.suffix.lower() == '.dsk')
        for dsk in dsks:
            yield dsk, folder.name

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Generate MAME coco_flop.xml from Color Computer Archive disk games.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--no-download', action='store_true',
                    help='skip download; use existing archive/ folder')
    ap.add_argument('--deploy',      action='store_true',
                    help='copy output XML to MAME hash directory')
    ap.add_argument('--verbose',     action='store_true',
                    help='show per-disk detail')
    ap.add_argument('--output',      default=str(OUTPUT_XML), metavar='FILE',
                    help=f'output path (default: {OUTPUT_XML})')
    args = ap.parse_args()

    output_path = Path(args.output)

    # Verify decb is available
    if shutil.which('decb') is None:
        print("Error: 'decb' not found in PATH.")
        print('Install ToolShed: https://sourceforge.net/projects/toolshed/')
        sys.exit(1)

    # --- Download ---
    if not args.no_download:
        print(f'Scraping {GAMES_URL} ...')
        urls = scrape_games(verbose=args.verbose)
        print(f'  Found {len(urls)} file(s) on the Archive.')
        print('Downloading ...')
        download_archives(urls, verbose=args.verbose)
        print('Extracting archives ...')
        extract_archives(verbose=args.verbose)
        print()
    else:
        print('Skipping download (--no-download).\n')

    if not ARCHIVE_DIR.exists() or not any(ARCHIVE_DIR.iterdir()):
        print(f'Error: {ARCHIVE_DIR} is empty or missing.')
        print('Run without --no-download to fetch files first.')
        sys.exit(1)

    # --- Process ---
    print('Processing disks ...')
    dsk_files = list(collect_dsk_files())
    print(f'  Found {len(dsk_files)} DSK file(s).\n')

    entries_xml   = []
    seen_names    = {}
    ambiguous_log = []
    stats = {'sure': 0, 'guess': 0, 'ambiguous': 0, 'none': 0, 'error': 0}

    for dsk_path, folder_name in dsk_files:
        dsk_stem = dsk_path.stem
        xml_name = make_xml_name(dsk_stem)

        # Deduplicate XML name
        if xml_name in seen_names:
            seen_names[xml_name] += 1
            xml_name = f'{xml_name}_{seen_names[xml_name]}'
        else:
            seen_names[xml_name] = 0

        # Inspect disk with decb
        dir_entries, err = run_decb_dir(dsk_path)
        if dir_entries is None:
            print(f'  [ERROR] {dsk_path.name}: {err}')
            stats['error'] += 1
            continue

        command, confidence = determine_load_command(dir_entries, dsk_stem)
        stats[confidence] += 1

        if confidence == 'ambiguous':
            ambiguous_log.append((dsk_path.name, folder_name, command, dir_entries))

        # Hash
        sha1, crc32 = hash_file(dsk_path)
        filesize = dsk_path.stat().st_size

        # Metadata
        description, publisher, compatibility = parse_folder_metadata(folder_name)

        entries_xml.append(build_xml_entry(
            name=xml_name,
            description=description,
            publisher=publisher,
            usage=command or '',
            compatibility=compatibility,
            dsk_filename=dsk_path.name,
            filesize=filesize,
            crc32=crc32,
            sha1=sha1,
        ))

        if args.verbose or confidence in ('ambiguous', 'none', 'error'):
            tag = f'[{confidence.upper()}] ' if confidence != 'sure' else ''
            cmd_str = command or '(none)'
            print(f'  {tag}{dsk_path.name}: {cmd_str}')
            if confidence == 'ambiguous':
                files_str = ', '.join(f'{e.name}.{e.ext}' for e in dir_entries
                                      if e.ext in ('BAS', 'BIN'))
                print(f'    files: {files_str}')

    # --- Write XML ---
    HASH_DIR.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(_XML_HEADER)
        for entry in entries_xml:
            fh.write('\n')
            fh.write(entry)
        fh.write(_XML_FOOTER)

    # --- Summary ---
    print(f'\nWrote {len(entries_xml)} entries → {output_path}')
    print()
    print('Load command confidence:')
    print(f'  Sure      : {stats["sure"]}')
    print(f'  Guess     : {stats["guess"]}  (one BAS loader + BIN data files)')
    print(f'  Ambiguous : {stats["ambiguous"]}  (review recommended)')
    print(f'  None      : {stats["none"]}  (no executable files — data/picture disks)')
    print(f'  Error     : {stats["error"]}  (decb failed — likely OS-9 or corrupt)')

    if ambiguous_log:
        print(f'\nAmbiguous entries — manual review recommended:')
        for dsk_name, folder, cmd, entries in ambiguous_log:
            execs = [e for e in entries if e.ext in ('BAS', 'BIN')]
            print(f'  {dsk_name}  →  used: {cmd}')
            print(f'    candidates: {", ".join(f"{e.name}.{e.ext}" for e in execs)}')

    # --- Deploy ---
    if args.deploy:
        if MAME_HASH_DIR.exists():
            dest = MAME_HASH_DIR / output_path.name
            shutil.copy2(output_path, dest)
            print(f'\nDeployed → {dest}')
        else:
            print(f'\nWarning: MAME hash dir not found at {MAME_HASH_DIR}')
            print(f'  Copy {output_path} there manually.')


if __name__ == '__main__':
    main()
