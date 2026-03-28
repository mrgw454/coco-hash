# coco-hash

Generates a MAME-compatible software list XML (`coco_flop.xml`) from CoCo disk
game images downloaded from the [Color Computer Archive](https://colorcomputerarchive.com).

Inspects each disk image using **decb** (ToolShed) to determine the correct BASIC
load command — `RUN`, `LOADM`, etc. — rather than blindly assuming one type.

---

## Requirements

- **Python 3.8+** (pyenv on Linux/Windows both work)
- **decb** from [ToolShed](https://sourceforge.net/projects/toolshed/) in your PATH
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
| *(no options)* | Download from Archive, process, write `hash/coco_flop.xml` |
| `--no-download` | Skip downloading; process existing `archive/` folder |
| `--deploy` | Copy output XML to MAME hash directory after generating |
| `--verbose` | Show per-disk detail during processing |
| `--output FILE` | Override output path (default: `hash/coco_flop.xml`) |

### Typical first run

```bash
python generate_coco_hash.py
```

Downloads all game disk images from the Archive's `Disks/Games/` section,
extracts them into `archive/`, inspects each one, and writes `hash/coco_flop.xml`.

### Subsequent runs (already have the files)

```bash
python generate_coco_hash.py --no-download
```

### Generate and deploy directly to MAME

```bash
python generate_coco_hash.py --deploy
```

Copies the output to:
- **Linux:** `~/.mame/hash/coco_flop.xml`
- **Windows:** `%USERPROFILE%\mame\hash\coco_flop.xml`

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
- `~/.mame/hash` → `<project>/hash/` — so MAME finds `coco_flop.xml`
- `~/.mame/software` → `<project>/software/` — so MAME finds the zipped DSK media

### Step 2 — Edit mame.ini

Two settings in `mame.ini` need updating (`~/.mame/mame.ini` on Linux,
`%USERPROFILE%\mame\mame.ini` on Windows).

> **Important:** Use **absolute paths** — MAME does not expand `$HOME`, `~`,
> or `%USERPROFILE%` in mame.ini settings.

**`hashpath`** — MAME uses the first `coco_flop.xml` it finds left to right.
Your user hash directory must come before the MAME install's `hash` directory:

Linux:
```
hashpath    /home/<user>/.mame/hash;hash;/opt/mame/hash
```

Windows:
```
hashpath    C:\Users\<user>\mame\hash;hash
```

**`swpath`** — This is what MAME uses to find software list zip files
(`rompath` is for ROMs, not software lists). Add your user software directory
as an absolute path first:

Linux:
```
swpath    /home/<user>/.mame/software;software;/media/share1/software
```

Windows:
```
swpath    C:\Users\<user>\mame\software;software
```

### Step 3 — rompath

Leave `rompath` for ROM sets only — remove any software directories from it:

```
rompath    roms;chds;/media/share1/roms
```

### Using the software list in MAME

Once set up, the list appears in the MAME file browser:

**TAB → File Manager → FloppyDisk1 → software list →
Tandy Radio Shack Color Computer Disk Images**

Or launch directly from the command line:
```
mame coco3 -flop1 coco_flop:gamename
```

---

## How it works

1. **Download** — scrapes the Archive directory listing and downloads ZIP files
   to `downloads/`. Previously downloaded files are skipped.

2. **Extract** — unzips each archive into `archive/`, preserving the per-game
   folder structure. DSK filenames are lowercased.

3. **Inspect** — runs `decb dir` on each DSK file to get the disk's file listing.
   Each file has a name, extension (`BAS` / `BIN` / data), and type code.

4. **Load command detection** — determines the correct BASIC command to launch
   the program (see below).

5. **Hash** — computes SHA1 and CRC32 for each DSK file.

6. **XML** — generates a MAME software list XML entry for each disk, including
   description, publisher, platform compatibility, hashes, and load command.

7. **Package** — zips each DSK into `software/coco_flop/<name>.zip` for MAME's
   rompath. Zip names match the XML software names exactly.

---

## Load command detection

The correct command depends on the file type on the disk:

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

The summary output reports confidence for each entry:

| Level | Meaning |
|---|---|
| `Sure` | Single file, known entry point, or disk-name match |
| `Guess` | One BAS loader + one or more BIN data files |
| `Ambiguous` | Multiple candidates; first used — review recommended |
| `None` | No executable files (picture/data disks) |
| `Error` | `decb` failed — likely OS-9, copy-protected, or corrupt |

Ambiguous entries are listed at the end of the run with the candidate files shown.

---

## Folder naming conventions

The Color Computer Archive names each game folder as:

```
Game Title (Publisher)
Game Title (Publisher) (Coco 3)
```

The script parses this to populate:
- **description** — game title (without publisher)
- **publisher** — text in the last set of parentheses
- **compatibility** — `COCO3` if `(Coco 3)` is present; otherwise `COCO,COCO3`

---

## Excluded content

The following folder patterns are skipped automatically:

`translations`, `protected`, `os-9`, `os9`, `disto`, `sdc`, `burke`, `bible`,
`cocovga`, `french`, `portuguese`, `dragon32`

---

## Project layout

```
generate_coco_hash.py   Main script
create-mame-links.sh    One-time symlink setup (Linux)
create-mame-links.ps1   One-time junction setup (Windows)
downloads/              Downloaded ZIP files (created on first run)
archive/                Extracted DSK images, one subfolder per game
hash/                   Generated output (coco_flop.xml)
software/coco_flop/     Zipped DSKs for MAME swpath
```

---

## Future

- **Cart support** — `coco_cart.xml` from `Carts/` section of the Archive
  (simpler: no `decb` needed, no load command)

---

Special thanks to **Guillaume Major** for hosting the Color Computer Archive.
