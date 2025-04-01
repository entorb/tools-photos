"""Downloads files from my cameras SD card."""

import datetime as dt
import sys
from pathlib import Path
from shutil import copyfile
from zoneinfo import ZoneInfo

TZ_DE = ZoneInfo("Europe/Berlin")
PREFIX = "TME_"

PATH_LAST_FILE = Path(__file__).parent / "photo_dl_from_sd_lastfile.txt"
DIR_IN = Path("/Volumes/TM-NIKON/DCIM/")
DIR_OUT = Path("/Users/torben/Pictures/Digikam/00_fotos_von_kam_holen/")

if not DIR_IN.exists():
    print(f"Source dir {DIR_IN} not found, exiting...")
    sys.exit()
DIR_OUT.mkdir(parents=True, exist_ok=True)

last_file = PATH_LAST_FILE.read_text().strip()

# read list of all files on SD card
all_files = sorted(DIR_IN.glob(f"*/{PREFIX}*"))

# check if last_file is in all_files
last_file_in_all_files = False
pos_last_file_in_all_files = 0
for i, p in enumerate(all_files):
    if p.name == last_file:
        last_file_in_all_files = True
        pos_last_file_in_all_files = i + 1
        break

# skip already transferred files
if last_file_in_all_files:
    all_files = all_files[pos_last_file_in_all_files:]


# copy new files
for p in all_files:
    print(p.name)
    file_ts = p.stat().st_mtime  # read modification timestamp
    file_dt = dt.datetime.fromtimestamp(file_ts, tz=TZ_DE)
    str_date = file_dt.strftime("%y%m%d_%H%M%S")
    outdir_ym = outfile = (
        DIR_OUT / file_dt.strftime("%y%m")  # sub dir YYMM
    )
    outdir_ym.mkdir(exist_ok=True)
    outfile = (
        outdir_ym / f"{str_date}_{p.stem.replace(PREFIX, 'Nikon_')}{p.suffix.lower()}"
    )
    # DCIM/115D7000/TME_5932.JPG
    # ->
    # NewFromCam/2408/240812_215120_Nikon_5932.jpg

    # print(outfile)
    # if 1 == 2:
    copyfile(p, outfile)

print(f"Last file: {p.name}")

PATH_LAST_FILE.write_text(p.name)
