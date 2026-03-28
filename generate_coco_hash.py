#!/usr/bin/env python3
"""
generate_coco_hash.py

Generate MAME software list XML files for the TRS-80 Color Computer from
images downloaded from the Color Computer Archive (colorcomputerarchive.com).

  Disk games  → hash/coco_flop.xml   (uses decb to detect load command)
  Cartridges  → hash/coco_cart.xml   (no decb needed; carts just boot)

Requirements:
    Python 3.8+
    decb (ToolShed) in PATH — required for disk mode only
    ToolShed: https://sourceforge.net/projects/toolshed/

Usage:
    python generate_coco_hash.py [options]

Options:
    --carts         Process cartridges instead of disks
    --all           Process both disks and cartridges
    --no-download   Skip downloading; process existing archive folders
    --deploy        Copy output XML(s) to MAME hash directory
    --verbose       Show per-item detail during processing
    --output FILE   Output path override (single-mode only)
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

SCRIPT_DIR = Path(__file__).parent
HASH_DIR   = SCRIPT_DIR / 'hash'

# Disk paths
ARCHIVE_DIR      = SCRIPT_DIR / 'archive'
DOWNLOAD_DIR     = SCRIPT_DIR / 'downloads'
FLOP_OUTPUT_XML  = HASH_DIR / 'coco_flop.xml'
FLOP_SOFTWARE_DIR = SCRIPT_DIR / 'software' / 'coco_flop'

# Cart paths
CART_ARCHIVE_DIR  = SCRIPT_DIR / 'cart_archive'
CART_DOWNLOAD_DIR = SCRIPT_DIR / 'cart_downloads'
CART_OUTPUT_XML   = HASH_DIR / 'coco_cart.xml'
CART_SOFTWARE_DIR = SCRIPT_DIR / 'software' / 'coco_cart'

if IS_WINDOWS:
    MAME_HASH_DIR = Path(os.environ.get('USERPROFILE', Path.home())) / 'mame' / 'hash'
else:
    MAME_HASH_DIR = Path.home() / '.mame' / 'hash'

# ---------------------------------------------------------------------------
# Archive source URLs
# ---------------------------------------------------------------------------

GAMES_URL = 'https://colorcomputerarchive.com/repo/Disks/Games/'
CARTS_URL = 'https://colorcomputerarchive.com/repo/Cartridges/'

# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

DISK_EXCLUDE_PATTERNS = [
    'translations', 'protected', 'os-9', 'os9', 'disto', 'sdc',
    'burke', 'bible', 'cocovga', 'french', 'portuguese', 'dragon32',
]

CART_EXCLUDE_PATTERNS = [
    'french', 'cp-400', 'cp400',
]

def should_exclude(path_str, patterns):
    low = path_str.lower()
    return any(pat in low for pat in patterns)

# ---------------------------------------------------------------------------
# HTML link scraper
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


def _scrape(url, results, depth, verbose, extensions, exclude_patterns, max_depth=6):
    """Recursively scrape a directory listing for files with given extensions."""
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
        if should_exclude(decoded, exclude_patterns):
            continue
        full_url = urljoin(url, href)
        if href.endswith('/'):
            _scrape(full_url, results, depth + 1, verbose, extensions,
                    exclude_patterns, max_depth)
        elif any(decoded.lower().endswith(ext) for ext in extensions):
            results.append((full_url, decoded))


def scrape_games(verbose=False):
    """Return list of (url, filename) for all disk game files on the Archive."""
    results = []
    _scrape(GAMES_URL, results, depth=0, verbose=verbose,
            extensions=['.zip', '.dsk'], exclude_patterns=DISK_EXCLUDE_PATTERNS)
    return results


def scrape_carts(verbose=False):
    """Return list of (url, filename) for all cartridge files on the Archive."""
    results = []
    _scrape(CARTS_URL, results, depth=0, verbose=verbose,
            extensions=['.ccc', '.zip'], exclude_patterns=CART_EXCLUDE_PATTERNS,
            max_depth=3)
    return results

# ---------------------------------------------------------------------------
# Download / extract (disks)
# ---------------------------------------------------------------------------

def download_files(urls, dest_dir, verbose=False):
    """Download files into dest_dir, skipping files already present."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_count = 0
    for url, filename in urls:
        dest = dest_dir / Path(filename).name
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


def extract_disk_archives(verbose=False):
    """
    Extract ZIPs from DOWNLOAD_DIR into ARCHIVE_DIR.
    All DSK filenames are lowercased.
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for zpath in sorted(DOWNLOAD_DIR.glob('*.zip')):
        try:
            with zipfile.ZipFile(zpath) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
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


def extract_cart_archives(verbose=False):
    """
    Extract any ZIPs in CART_DOWNLOAD_DIR that contain .ccc files into CART_ARCHIVE_DIR.
    Bare .ccc files are copied directly.
    """
    CART_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for zpath in sorted(CART_DOWNLOAD_DIR.glob('*.zip')):
        try:
            with zipfile.ZipFile(zpath) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    if not member.filename.lower().endswith('.ccc'):
                        continue
                    target = CART_ARCHIVE_DIR / Path(member.filename).name
                    if target.exists():
                        if verbose:
                            print(f'  Exists:  {target.name}')
                        continue
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if verbose:
                        print(f'  Extract: {target.name}')
        except zipfile.BadZipFile as exc:
            print(f'  Bad ZIP {zpath.name}: {exc}')

    for ccc in sorted(CART_DOWNLOAD_DIR.glob('*.ccc')):
        dest = CART_ARCHIVE_DIR / ccc.name
        if not dest.exists():
            shutil.copy2(ccc, dest)
            if verbose:
                print(f'  Copy:    {ccc.name}')

# ---------------------------------------------------------------------------
# Disk inspection (decb)
# ---------------------------------------------------------------------------

FileEntry = namedtuple('FileEntry', ['name', 'ext', 'ftype'])

_FTYPE_BAS_TOKEN = '0'   # tokenized BASIC
_FTYPE_BAS_ASCII = '1'   # ASCII BASIC
_FTYPE_BINARY    = '2'   # machine language / binary


def run_decb_dir(dsk_path):
    """
    Run 'decb dir' on dsk_path.
    Returns (list[FileEntry], error_str).  On success error_str is None.

    decb error 215 occurs on paths with special characters (apostrophes, commas,
    brackets, etc.).  Workaround: copy DSK to a temp file with a clean name first.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.dsk', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        shutil.copy2(dsk_path, tmp_path)
        result = subprocess.run(
            ['decb', 'dir', str(tmp_path)],
            capture_output=True, timeout=10,
        )
        stdout = result.stdout.decode('latin-1')
        stderr = result.stderr.decode('latin-1')
    except FileNotFoundError:
        return None, "'decb' not found in PATH"
    except subprocess.TimeoutExpired:
        return None, 'decb timed out'
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if result.returncode != 0:
        msg = (stderr or stdout).strip()
        return None, msg or f'decb returned {result.returncode}'

    entries = []
    for line in stdout.splitlines():
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

ENTRY_NAMES = frozenset({
    'RUNME', 'AUTOEXEC', 'AUTO', 'AUTORUN',
    'START', 'MAIN', 'MENU', 'LOADER', 'LOAD', 'BOOT',
})


def _make_command(entry):
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

    for e in execs:
        if e.name.upper() in ENTRY_NAMES:
            return _make_command(e), 'sure'

    stem_up = dsk_stem.upper()
    for e in execs:
        if e.name.upper() == stem_up:
            return _make_command(e), 'sure'

    bas  = [e for e in execs if e.ext == 'BAS']
    bins = [e for e in execs if e.ext == 'BIN']

    if len(bas) == 1 and bins:
        return _make_command(bas[0]), 'guess'

    if len(bas) == 1:
        return _make_command(bas[0]), 'sure'

    if len(bins) == 1:
        return _make_command(bins[0]), 'sure'

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
# Metadata parsing
# ---------------------------------------------------------------------------

_COCO3_RE = re.compile(r'\(coco\s*3\)', re.IGNORECASE)
_YEAR_RE   = re.compile(r'\((1[89]\d\d|20\d\d)\)')
_PROD_RE   = re.compile(r'\(\s*26-\d+[^)]*\)', re.IGNORECASE)


def parse_folder_metadata(folder_name):
    """
    Parse 'Game Title (Publisher) (Coco 3)' disk folder names.
    Returns (description, publisher, compatibility).
    """
    is_coco3 = bool(_COCO3_RE.search(folder_name))
    name = _COCO3_RE.sub('', folder_name).strip()

    pub_match = re.search(r'\(([^)]+)\)\s*$', name)
    if pub_match:
        publisher   = pub_match.group(1).strip()
        description = name[:pub_match.start()].strip()
    else:
        publisher   = 'unknown'
        description = name.strip()

    compatibility = 'COCO3' if is_coco3 else 'COCO,COCO3'
    return description, publisher, compatibility


def parse_cart_filename(stem):
    """
    Parse a cart filename stem such as:
      'Polaris (1982) (26-3002) (Tandy) (Coco 1-2)'
      'Demon Attack (1983) (26-3090) (Imagic) (Coco 3)'

    Returns (title, year, publisher, compatibility).
    """
    s = stem

    # Detect and strip compatibility marker
    is_coco3 = bool(re.search(r'\(coco\s*3\)', s, re.IGNORECASE))
    s = re.sub(r'\s*\(coco[^)]*\)', '', s, flags=re.IGNORECASE).strip()

    # Extract year
    year_match = _YEAR_RE.search(s)
    year = year_match.group(1) if year_match else '19xx'
    if year_match:
        s = (s[:year_match.start()] + s[year_match.end():]).strip()

    # Strip product code (26-XXXX)
    s = _PROD_RE.sub('', s).strip()

    # Last parenthesized group = publisher
    pub_match = re.search(r'\(([^)]+)\)\s*$', s)
    if pub_match:
        publisher = pub_match.group(1).strip()
        title     = s[:pub_match.start()].strip()
    else:
        publisher = 'unknown'
        title     = s.strip()

    compatibility = 'COCO3' if is_coco3 else 'COCO,COCO3'
    return title, year, publisher, compatibility


def make_xml_name(stem):
    """Convert a filename stem into a valid MAME software name."""
    s = stem.lower()
    s = re.sub(r'[^a-z0-9]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or 'unknown'

# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _esc_text(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _esc_attr(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


_FLOP_XML_HEADER = (
    '<?xml version="1.0"?>\n'
    '<!DOCTYPE softwarelist SYSTEM "softwarelist.dtd">\n\n'
    '<softwarelist name="coco_flop" '
    'description="Tandy Radio Shack Color Computer disk images">\n'
)

_CART_XML_HEADER = (
    '<?xml version="1.0"?>\n'
    '<!DOCTYPE softwarelist SYSTEM "softwarelist.dtd">\n\n'
    '<softwarelist name="coco_cart" '
    'description="Tandy Radio Shack Color Computer cartridges">\n'
)

_XML_FOOTER = '\n</softwarelist>\n'


def build_flop_xml_entry(name, description, publisher, usage, compatibility,
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
        f'{t}{t}{t}{t}<rom name="{_esc_attr(dsk_filename)}" size="{filesize}" '
        f'crc="{crc32}" sha1="{sha1}" offset="0" />',
        f'{t}{t}{t}</dataarea>',
        f'{t}{t}</part>',
        f'{t}</software>',
        '',
    ]
    return '\n'.join(lines)


def build_cart_xml_entry(name, description, publisher, year, compatibility,
                          cart_filename, filesize, crc32, sha1):
    t = '\t'
    lines = [
        f'{t}<software name="{name}">',
        f'{t}{t}<description>{_esc_text(description)}</description>',
        f'{t}{t}<year>{year}</year>',
        f'{t}{t}<publisher>{_esc_text(publisher)}</publisher>',
        f'{t}{t}<sharedfeat name="compatibility" value="{compatibility}" />',
        f'{t}{t}<part name="cart" interface="coco_cart">',
        f'{t}{t}{t}<dataarea name="rom" size="{filesize}">',
        f'{t}{t}{t}{t}<rom name="{_esc_attr(cart_filename)}" size="{filesize}" '
        f'crc="{crc32}" sha1="{sha1}" />',
        f'{t}{t}{t}</dataarea>',
        f'{t}{t}</part>',
        f'{t}</software>',
        '',
    ]
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_dsk_files():
    """Yield (dsk_path, folder_name) for each DSK in ARCHIVE_DIR."""
    for folder in sorted(ARCHIVE_DIR.iterdir()):
        if not folder.is_dir():
            continue
        if should_exclude(folder.name, DISK_EXCLUDE_PATTERNS):
            continue
        for dsk in sorted(f for f in folder.iterdir() if f.suffix.lower() == '.dsk'):
            yield dsk, folder.name


def collect_ccc_files():
    """Yield ccc_path for each .ccc file in CART_ARCHIVE_DIR."""
    for ccc in sorted(CART_ARCHIVE_DIR.glob('*.ccc')):
        yield ccc

# ---------------------------------------------------------------------------
# Processing: disks
# ---------------------------------------------------------------------------

def process_disks(args, output_path):
    if not args.no_download:
        print(f'Scraping {GAMES_URL} ...')
        urls = scrape_games(verbose=args.verbose)
        print(f'  Found {len(urls)} file(s) on the Archive.')
        print('Downloading ...')
        download_files(urls, DOWNLOAD_DIR, verbose=args.verbose)
        print('Extracting archives ...')
        extract_disk_archives(verbose=args.verbose)
        print()
    else:
        print('Skipping download (--no-download).\n')

    if not ARCHIVE_DIR.exists() or not any(ARCHIVE_DIR.iterdir()):
        print(f'Error: {ARCHIVE_DIR} is empty or missing.')
        print('Run without --no-download to fetch files first.')
        return False

    print('Processing disks ...')
    dsk_files = list(collect_dsk_files())
    print(f'  Found {len(dsk_files)} DSK file(s).\n')

    entries_xml   = []
    seen_names    = {}
    ambiguous_log = []
    software_map  = []
    stats = {'sure': 0, 'guess': 0, 'ambiguous': 0, 'none': 0, 'error': 0}

    for dsk_path, folder_name in dsk_files:
        dsk_stem = dsk_path.stem
        xml_name = make_xml_name(dsk_stem)

        if xml_name in seen_names:
            seen_names[xml_name] += 1
            xml_name = f'{xml_name}_{seen_names[xml_name]}'
        else:
            seen_names[xml_name] = 0

        dir_entries, err = run_decb_dir(dsk_path)
        if dir_entries is None:
            print(f'  [ERROR] {dsk_path.name}: {err}')
            stats['error'] += 1
            continue

        command, confidence = determine_load_command(dir_entries, dsk_stem)
        stats[confidence] += 1

        if confidence == 'ambiguous':
            ambiguous_log.append((dsk_path.name, folder_name, command, dir_entries))

        sha1, crc32 = hash_file(dsk_path)
        filesize = dsk_path.stat().st_size

        description, publisher, compatibility = parse_folder_metadata(folder_name)

        entries_xml.append(build_flop_xml_entry(
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
        software_map.append((xml_name, dsk_path))

        if args.verbose or confidence in ('ambiguous', 'none'):
            tag = f'[{confidence.upper()}] ' if confidence != 'sure' else ''
            cmd_str = command or '(none)'
            print(f'  {tag}{dsk_path.name}: {cmd_str}')
            if confidence == 'ambiguous':
                files_str = ', '.join(f'{e.name}.{e.ext}' for e in dir_entries
                                      if e.ext in ('BAS', 'BIN'))
                print(f'    files: {files_str}')

    # Write XML
    HASH_DIR.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(_FLOP_XML_HEADER)
        for entry in entries_xml:
            fh.write('\n')
            fh.write(entry)
        fh.write(_XML_FOOTER)

    # Package DSKs
    print('\nPackaging DSK files for MAME software path ...')
    FLOP_SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
    expected_zips = {f'{xml_name}.zip' for xml_name, _ in software_map}
    for old_zip in FLOP_SOFTWARE_DIR.glob('*.zip'):
        if old_zip.name not in expected_zips:
            old_zip.unlink()
    packaged = 0
    for xml_name, dsk_path in software_map:
        zip_path = FLOP_SOFTWARE_DIR / f'{xml_name}.zip'
        if not zip_path.exists():
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(dsk_path, dsk_path.name)
            packaged += 1
    print(f'  {packaged} new zip(s) created, {len(software_map) - packaged} already present.')

    # Summary
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

    # Deploy
    if args.deploy:
        MAME_HASH_DIR.mkdir(parents=True, exist_ok=True)
        dest = MAME_HASH_DIR / output_path.name
        shutil.copy2(output_path, dest)
        print(f'\nDeployed → {dest}')

    return True

# ---------------------------------------------------------------------------
# Processing: carts
# ---------------------------------------------------------------------------

def process_carts(args, output_path):
    if not args.no_download:
        print(f'Scraping {CARTS_URL} ...')
        urls = scrape_carts(verbose=args.verbose)
        print(f'  Found {len(urls)} file(s) on the Archive.')
        print('Downloading ...')
        download_files(urls, CART_DOWNLOAD_DIR, verbose=args.verbose)
        print('Extracting archives ...')
        extract_cart_archives(verbose=args.verbose)
        print()
    else:
        print('Skipping download (--no-download).\n')

    if not CART_ARCHIVE_DIR.exists() or not any(CART_ARCHIVE_DIR.glob('*.ccc')):
        print(f'Error: no .ccc files found in {CART_ARCHIVE_DIR}.')
        print('Run without --no-download to fetch files first.')
        return False

    print('Processing cartridges ...')
    ccc_files = list(collect_ccc_files())
    print(f'  Found {len(ccc_files)} CCC file(s).\n')

    entries_xml  = []
    seen_names   = {}
    software_map = []

    for ccc_path in ccc_files:
        stem = ccc_path.stem
        title, year, publisher, compatibility = parse_cart_filename(stem)
        xml_name = make_xml_name(title) if title else make_xml_name(stem)

        if xml_name in seen_names:
            seen_names[xml_name] += 1
            xml_name = f'{xml_name}_{seen_names[xml_name]}'
        else:
            seen_names[xml_name] = 0

        sha1, crc32 = hash_file(ccc_path)
        filesize = ccc_path.stat().st_size

        entries_xml.append(build_cart_xml_entry(
            name=xml_name,
            description=title or stem,
            publisher=publisher,
            year=year,
            compatibility=compatibility,
            cart_filename=ccc_path.name,
            filesize=filesize,
            crc32=crc32,
            sha1=sha1,
        ))
        software_map.append((xml_name, ccc_path))

        if args.verbose:
            print(f'  {ccc_path.name}: {title} ({year}) [{publisher}] {compatibility}')

    # Write XML
    HASH_DIR.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(_CART_XML_HEADER)
        for entry in entries_xml:
            fh.write('\n')
            fh.write(entry)
        fh.write(_XML_FOOTER)

    # Package CCC files
    print('\nPackaging cartridge files for MAME software path ...')
    CART_SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
    expected_zips = {f'{xml_name}.zip' for xml_name, _ in software_map}
    for old_zip in CART_SOFTWARE_DIR.glob('*.zip'):
        if old_zip.name not in expected_zips:
            old_zip.unlink()
    packaged = 0
    for xml_name, ccc_path in software_map:
        zip_path = CART_SOFTWARE_DIR / f'{xml_name}.zip'
        if not zip_path.exists():
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(ccc_path, ccc_path.name)
            packaged += 1
    print(f'  {packaged} new zip(s) created, {len(software_map) - packaged} already present.')

    # Summary
    print(f'\nWrote {len(entries_xml)} entries → {output_path}')

    # Deploy
    if args.deploy:
        MAME_HASH_DIR.mkdir(parents=True, exist_ok=True)
        dest = MAME_HASH_DIR / output_path.name
        shutil.copy2(output_path, dest)
        print(f'Deployed → {dest}')

    return True

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Generate MAME software list XML from Color Computer Archive.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Default (no flags): generate coco_flop.xml from disk games.\n'
            '--carts: generate coco_cart.xml from cartridges.\n'
            '--all:   generate both.\n'
        ),
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--carts', action='store_true',
                      help='process cartridges (coco_cart.xml) instead of disks')
    mode.add_argument('--all',   action='store_true',
                      help='process both disks and cartridges')
    ap.add_argument('--no-download', action='store_true',
                    help='skip download; use existing archive folders')
    ap.add_argument('--deploy',      action='store_true',
                    help='copy output XML(s) to MAME hash directory')
    ap.add_argument('--verbose',     action='store_true',
                    help='show per-item detail')
    ap.add_argument('--output',      default=None, metavar='FILE',
                    help='output path override (single-mode only)')
    args = ap.parse_args()

    do_disks = not args.carts  # default or --all
    do_carts = args.carts or args.all
    do_disks = do_disks or args.all

    if args.output and do_disks and do_carts:
        ap.error('--output cannot be used with --all (would write both XMLs to same file)')

    if do_disks:
        if shutil.which('decb') is None:
            print("Error: 'decb' not found in PATH.")
            print('Install ToolShed: https://sourceforge.net/projects/toolshed/')
            sys.exit(1)
        flop_out = Path(args.output) if args.output else FLOP_OUTPUT_XML
        process_disks(args, flop_out)
        if do_carts:
            print('\n' + '─' * 60 + '\n')

    if do_carts:
        cart_out = Path(args.output) if args.output else CART_OUTPUT_XML
        process_carts(args, cart_out)


if __name__ == '__main__':
    main()
