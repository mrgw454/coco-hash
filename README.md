# coco-hash

Generates MAME-compatible software list XML files for the TRS-80 Color Computer
from images downloaded from the [Color Computer Archive](https://colorcomputerarchive.com).

| Output | Source | Tool needed |
|---|---|---|
| `hash/coco_flop.xml` | `Disks/Games/` — DSK images | **decb** (ToolShed) |
| `hash/coco_cart.xml` | `Cartridges/` — CCC images | none |

For disk games, **decb** is used to inspect each DSK and determine the correct BASIC
load command (`RUN` vs `LOADM`) rather than blindly assuming one type.

---

## Requirements

- **Python 3.8+** (pyenv on Linux, pyenv-win on Windows both work)
- **decb** from [ToolShed](https://sourceforge.net/projects/toolshed/) in your PATH
  - Required for disk mode only; not needed for `--carts`
  - Linux: build from source or install package
  - Windows: pre-built binary available from the ToolShed project page

No third-party Python packages required — stdlib only.

---

## Usage

```
python generate_coco_hash.py [options]
```

| Option | Description |
|---|---|
| *(no options)* | Generate `coco_flop.xml` from disk games |
| `--carts` | Generate `coco_cart.xml` from cartridges |
| `--all` | Generate both disk and cart XML files |
| `--no-download` | Skip downloading; process existing archive folders |
| `--deploy` | Copy output XML(s) to MAME hash directory after generating |
| `--verbose` | Show per-item detail during processing |
| `--output FILE` | Override output path (single-mode only) |

### Typical first run

```bash
# Disks only
python generate_coco_hash.py

# Carts only
python generate_coco_hash.py --carts

# Both at once
python generate_coco_hash.py --all
```

### Subsequent runs (already have the files)

```bash
python generate_coco_hash.py --no-download
python generate_coco_hash.py --carts --no-download
python generate_coco_hash.py --all --no-download
```

### Generate and deploy directly to MAME

```bash
python generate_coco_hash.py --deploy
python generate_coco_hash.py --all --deploy
```

Copies the output to:
- **Linux:** `~/.mame/hash/coco_flop.xml` and/or `coco_cart.xml`
- **Windows:** `%USERPROFILE%\mame\hash\coco_flop.xml` and/or `coco_cart.xml`

---

## MAME setup

### Step 1 — Link project folders into MAME

Run the appropriate script **once** to create symlinks (Linux) or junctions (Windows)
from your MAME directory into this project. After that, regenerating the XML is
immediately live in MAME with no copy step needed.

**Linux** — creates symlinks into `~/.mame/`:
```bash
./create-mame-links.sh
```

**Windows** — creates directory junctions into `%USERPROFILE%\mame\`:
```powershell
.\create-mame-links.ps1
```

This creates:
- `~/.mame/hash` → `<project>/hash/` — so MAME finds `coco_flop.xml` and `coco_cart.xml`
- `~/.mame/software` → `<project>/software/` — so MAME finds the zipped media

### Step 2 — Edit mame.ini

Two settings in `mame.ini` need updating (`~/.mame/mame.ini` on Linux,
`%USERPROFILE%\mame\mame.ini` on Windows).

> **Important:** Use **absolute paths** — MAME does not expand `$HOME`, `~`,
> or `%USERPROFILE%` in mame.ini settings.

**`hashpath`** — MAME uses the first matching XML it finds left to right.
Your user hash directory must come **before** the MAME install's `hash` directory
or MAME will use the official (incomplete) list and ignore yours:

Linux:
```
hashpath    /home/<user>/.mame/hash;hash;/opt/mame/hash
```

Windows:
```
hashpath    C:\Users\<user>\mame\hash;hash
```

**`rompath`** — This is what MAME uses to find software list zip files.
Your user software directory must appear here (not just in `swpath`):

Linux:
```
rompath    software;roms;chds;/media/share1/roms;/media/share1/software
```

Windows:
```
rompath    C:\Users\<user>\mame\software;roms
```

> **Note:** `swpath` is only for loose (unzipped) files. Software list zip archives
> are always located via `rompath`.

### Using the software lists in MAME

**Disk games** — appears in the file manager:

TAB → File Manager → FloppyDisk1 → software list →
**Tandy Radio Shack Color Computer disk images**

Or launch directly:
```
mame coco3 -flop1 coco_flop:gamename
```

Each disk entry shows the correct BASIC load command (e.g. `RUN"GAME"` or
`LOADM"GAME":EXEC`) — select the title, then type the shown command at the CoCo BASIC prompt.

**Cartridges** — launch directly:
```
mame coco3 -cart coco_cart:gamename
```

Or use the file manager: TAB → File Manager → Cartridge → software list →
**Tandy Radio Shack Color Computer cartridges**

---

## How it works — disks

1. **Download** — scrapes `Disks/Games/` and downloads ZIP files to `downloads/`.
   Previously downloaded files are skipped.

2. **Extract** — unzips each archive into `archive/`, preserving folder structure.
   DSK filenames are lowercased.

3. **Inspect** — runs `decb dir` on each DSK to get the file listing.
   Each file has a name, extension (`BAS` / `BIN` / data), and type code.

4. **Load command detection** — determines the correct BASIC command to launch
   the program (see below).

5. **Hash** — computes SHA1 and CRC32 for each DSK file.

6. **XML** — generates `hash/coco_flop.xml` with description, publisher, platform
   compatibility, hashes, and load command per entry.

7. **Package** — zips each DSK into `software/coco_flop/<name>.zip`.

## How it works — carts

1. **Download** — scrapes `Cartridges/` and downloads `.ccc` files to `cart_downloads/`.

2. **Extract** — copies to `cart_archive/` (handles any ZIP bundles automatically).

3. **Parse** — extracts title, year, publisher, and CoCo 3 compatibility from
   the filename (e.g. `Polaris (1982) (26-3002) (Tandy) (Coco 1-2).ccc`).

4. **Hash** — computes SHA1 and CRC32.

5. **XML** — generates `hash/coco_cart.xml`.

6. **Package** — zips each CCC into `software/coco_cart/<name>.zip`.

---

## Load command detection (disks only)

| Disk file type | BASIC command |
|---|---|
| Tokenized BASIC (type 0) | `RUN"FILENAME"` |
| ASCII BASIC (type 1) | `RUN"FILENAME"` |
| Binary / machine code (type 2) | `LOADM"FILENAME":EXEC` |

### Entry point selection

When a disk has multiple files, the script uses these rules in order:

1. Known entry-point names: `RUNME`, `BOOT`, `AUTOEXEC`, `AUTO`, `AUTORUN`,
   `START`, `MAIN`, `MENU`, `LOADER`, `LOAD`
2. File whose name matches the DSK filename
3. Single BAS file (even if BIN files also present — BAS is the loader)
4. Single BIN file
5. First BAS or BIN found — flagged **ambiguous**

### Confidence levels

| Level | Meaning |
|---|---|
| `Sure` | Single file, known entry point, or disk-name match |
| `Guess` | One BAS loader + one or more BIN data files |
| `Ambiguous` | Multiple candidates; first used — review recommended |
| `None` | No executable files (picture/data disks) |
| `Error` | `decb` failed — likely OS-9, copy-protected, or corrupt |

Ambiguous entries are listed at the end of the run with the candidate files shown.

---

## Folder/filename naming conventions

**Disk folders:**
```
Game Title (Publisher)
Game Title (Publisher) (Coco 3)
```

**Cart filenames:**
```
Game Title (Year) (26-XXXX) (Publisher) (Coco 1-2).ccc
Game Title (Year) (26-XXXX) (Publisher) (Coco 3).ccc
```

Both formats populate:
- **description** — game title
- **publisher** — text in the last relevant set of parentheses
- **compatibility** — `COCO3` if `(Coco 3)` is present; otherwise `COCO,COCO3`

Cart filenames also provide a real **year** (e.g. `1982`) rather than `19xx`.

---

## Excluded content

**Disks:** `translations`, `protected`, `os-9`, `os9`, `disto`, `sdc`, `burke`,
`bible`, `cocovga`, `french`, `portuguese`, `dragon32`

**Carts:** `french`, `cp-400`, `cp400`

---

## Project layout

```
generate_coco_hash.py   Main script
create-mame-links.sh    One-time symlink setup (Linux)
create-mame-links.ps1   One-time junction setup (Windows)
downloads/              Downloaded disk ZIPs (created on first run)
archive/                Extracted DSK images, one subfolder per game
cart_downloads/         Downloaded cart CCC/ZIP files
cart_archive/           Extracted CCC files
hash/                   Generated output (coco_flop.xml, coco_cart.xml)
software/coco_flop/     Zipped DSKs for MAME rompath
software/coco_cart/     Zipped CCCs for MAME rompath
```

---

## Troubleshooting

### MAME shows only a handful of entries

- Check that `hashpath` has your user hash directory listed **first** (before `hash`
  or `/opt/mame/hash`). MAME stops at the first matching XML it finds.
- Validate the XML: `xmllint --noout hash/coco_flop.xml` — any parse error will
  cause MAME to silently fall back to the official list.
- Confirm the symlinks exist: `ls -la ~/.mame/hash ~/.mame/software`

### MAME can't find the disk/cart images

- Confirm `rompath` (not `swpath`) contains the path to `software/coco_flop/`
  or `software/coco_cart/`.
- Zip filenames must exactly match the software name in the XML
  (the script handles this automatically).

---

Special thanks to **Guillaume Major** for hosting the Color Computer Archive.
