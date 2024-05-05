#!/usr/bin/env python3
"""
Rename files and photos from iCloud based on date.

V1: run on Windows in directory iCloud Downloads
V2: download photos from icloud.com in heaps of one month each
do decided: use originals in HEIC format or download "compatible" ones in jpeg
but reduced size?

location online: https://github.com/entorb/Tools-Photos
"""
# TODO:
# ruff: noqa

# extract date and time from movies via pip install exifread
import datetime as dt
import glob
import os
import platform
import re

import exifread  # pip3 install exifread

# from PIL import Image, ExifTags  # pip3 install Pillow

basedir = "f:\\FotoalbumSSD\\00_fotos_von_icloud_holen\\downloaded"
outdir = "renamed"

# skip these files
l_ignore = [
    "000_rename.py",
    ".vscode",
]


def fix_edited_name_for_jpg():
    """
    Remove (Edited).

    for some strange reason I have
    IMG_1400 (Edited).HEIC
    IMG_1400(Edited).jpg -> space to add
    """
    for filepath in sorted(glob.glob("*(Edited).*")):
        filepath_new = re.sub(re.compile(r"(\d)(\(Edited\))"), r"\1 \2", filepath)
        if filepath != filepath_new:
            rename_file_after_checks(filepath, filepath_new)


def creation_date(path_to_file):
    """
    Get creation date.

    from https://stackoverflow.com/posts/39501288/1709587
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == "Windows":
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def get_date(path_to_file) -> dt.datetime:
    """
    Get Date.

    returns datetime of file creation
    1. for jpg images try reading from exif tag
    2. for heic images try reading from exif tag
    (NO: 3. for others fetch modification date and creation date and use the older one)
    """
    d = dt.datetime.fromtimestamp(0)  # 1.1.1970
    # for pictures try to read exif data
    file_ext = os.path.splitext(path_to_file)[1]
    # if file_ext.lower() in (".jpg", ".jpeg"):
    # image = Image.open(path_to_file)
    # exif = image.getexif()
    # exif_creation_time = exif.get(36867)
    # if exif_creation_time:
    #     exif_creation_time = exif_creation_time.replace(":", "-", 2)
    #     dt_exif_creation = dt.datetime.fromisoformat(exif_creation_time)
    #     d = dt_exif_creation

    if file_ext.lower() in (
        ".jpg",
        ".jpeg",
        ".heic",
    ):
        with open(path_to_file, "rb") as fh:
            tags = exifread.process_file(fh)
        # for key, value in tags.items():
        #     print(f"{key}\t{value}")
        if "EXIF DateTimeOriginal" in tags and str(tags["EXIF DateTimeOriginal"]) != 0:
            exif_creation_time = str(tags["EXIF DateTimeOriginal"])
            exif_creation_time = exif_creation_time.replace(":", "-", 2)
            dt_exif_creation = dt.datetime.fromisoformat(exif_creation_time)
            d = dt_exif_creation

    # not, this is just the date of the download
    # else use file timestamp instead
    if d == dt.datetime.fromtimestamp(0):
        # creation time is a bit tricky
        ts_file_created = creation_date(path_to_file)
        dt_file_created = dt.datetime.fromtimestamp(ts_file_created)

        ts_file_modified = os.path.getmtime(path_to_file)
        dt_file_modified = dt.datetime.fromtimestamp(ts_file_modified)

        if (
            dt_file_created <= dt_file_modified
            and dt_file_created > dt.datetime.fromtimestamp(0)
        ):
            dt2 = dt_file_created
        else:
            dt2 = dt_file_modified
        if dt2 < dt.datetime.today() - dt.timedelta(days=7):
            d = dt2
        # del ts_file_created, ts_file_modified
    return d


def gen_datestr(d: dt.datetime) -> str:
    """
    Format datetime to string.
    """
    s = d.strftime("%y%m%d_%H%M%S")
    if d == dt.datetime.fromtimestamp(0):
        s = "000000"
    return s


def gen_filename(
    filepath: str,
    suffix: str = "",
    out_sub_dir: str = "",
    remove: str = "",
) -> tuple:
    """
    Generate filename.

    suffix: at string starting with "_" to insert in filename after date
    remove: a string to remove from filename
    returns tuple of new filepath, new filename, new extension
    if output file already exists, append sequence
    """
    (filename, file_ext) = os.path.splitext(filepath)
    d = get_date(filepath)
    datestr = gen_datestr(d)
    count_identical_files = 0

    filename_modified = filename.replace("IMG_", "img_")
    if remove != "":
        filename_modified = filename_modified.replace(remove, "")
    filename_new = f"{datestr}{suffix}_{filename_modified}"

    file_ext_new = file_ext.lower()
    if file_ext_new == ".jpeg":
        file_ext_new = ".jpg"

    filepath_new = f"{outdir}/{out_sub_dir}/{filename_new}{file_ext_new}"

    # check if outfile already exists, if so append number
    while os.path.isfile(f"{filepath_new}"):
        count_identical_files += 1
        filename_new = (
            f"{datestr}{suffix}_{filename_modified}_%02d" % count_identical_files
        )
        filepath_new = f"{outdir}/{out_sub_dir}/{filename_new}{file_ext_new}"

    return filepath_new, filename_new, file_ext_new


def rename_file_after_checks(filepath_old: str, filepath_new: str):
    """
    Perform the file renaming after some security checks.
    """
    target_dir = os.path.split(filepath_new)[0]
    assert os.path.isdir(target_dir), f"dir {target_dir} missing"
    assert filepath_old != filepath_new, f"{filepath_old}: newfile = oldfile"
    assert not os.path.isfile(
        filepath_new,
    ), f"{filepath_old}: {filepath_new} already exists"
    os.rename(filepath_old, filepath_new)


def rename_iPhone_photos():
    """
    Rename IMG_*.JPEG and same named.HEIC and _HEVC.MOV (dynamic Photos).
    """
    list_of_files = []
    list_of_files.extend(glob.glob("IMG_*.JPG"))
    list_of_files.extend(glob.glob("IMG_*.JPEG"))
    for filepath in sorted(list_of_files):
        filename = os.path.splitext(filepath)[0]
        filepath_new, filename_new, file_ext_new = gen_filename(filepath)

        print(f"{filepath} -> {filepath_new}")
        rename_file_after_checks(filepath, filepath_new)

        # for iPhone .jpg we usually also find a .HEIC and if enabled also a _HEVC.MOV
        for ext2 in (".HEIC", "_HEVC.MOV"):
            o = filename + ext2
            if os.path.isfile(o):
                n = f"{outdir}/HEIC/{filename_new}{ext2.lower()}"

                print(f"{o} -> {n}")
                rename_file_after_checks(o, n)

    list_of_files = glob.glob("IMG_*.HEIC")
    for filepath in sorted(list_of_files):
        filepath_new, filename_new, file_ext_new = gen_filename(filepath)

        print(f"{filepath} -> {filepath_new}")
        rename_file_after_checks(filepath, filepath_new)


def rename_files_matching(
    search_str: str,
    suffix="",
    out_sub_dir: str = "",
    remove: str = "",
):
    """
    Use glob in current dir applying search_str.
    """
    for filepath in sorted(glob.glob(search_str)):
        if not os.path.isdir(f"{outdir}/{out_sub_dir}"):
            os.mkdir(f"{outdir}/{out_sub_dir}")

        # filename = os.path.splitext(filepath)[0]
        filepath_new, filename_new, file_ext_new = gen_filename(
            filepath=filepath,
            suffix=suffix,
            out_sub_dir=out_sub_dir,
            remove=remove,
        )

        print(f"{filepath} -> {filepath_new}")
        rename_file_after_checks(filepath, filepath_new)


def rename_Whatsapp_files():
    """
    Rename all files of filename matching.

    - exact 36 chars
    - of 0-9,a-f,A-F
    """
    myPatternWA = r"^[0-9a-fA-F\-]+$"
    myRegExpWA = re.compile(myPatternWA)
    out_sub_dir = "WhatsApp"

    for f in os.scandir("./"):
        if not f.is_file or f.name in l_ignore:
            continue
        filepath = f.name  # name: without leading ./, path: with
        filename = os.path.splitext(f.name)[0]
        if len(filename) != 36:
            continue

        match = myRegExpWA.search(filename)
        if match:
            if not os.path.isdir(f"{outdir}/{out_sub_dir}"):
                os.mkdir(f"{outdir}/{out_sub_dir}")
            filepath_new, filename_new, file_ext_new = gen_filename(
                filepath=filepath,
                suffix="_WA",
                out_sub_dir=out_sub_dir,
            )
            print(f"{filepath} -> {filepath_new}")
            rename_file_after_checks(filepath, filepath_new)
        else:
            # print("not matched")
            pass


def doit(sub_dir):
    # print(f"{basedir}/{sub_dir}")
    os.chdir(f"{basedir}/{sub_dir}")
    os.makedirs(outdir, exist_ok=True)  # = mkdir -p
    for d in ("E", "H", "B", "Unfug", "Sport", "Leute", "Torben"):
        os.makedirs(f"{outdir}/{d}", exist_ok=True)  # = mkdir -p

    # jpeg -> jpg
    for filepath in sorted(glob.glob("*.JPEG")):
        filepath_new = filepath.replace(".JPEG", ".jpg")
        # filepath_new = re.sub(".jpe?g$", ".jpg", filepath, re.IGNORECASE)
        if filepath_new != filepath and not os.path.isfile(filepath_new):
            os.rename(filepath, filepath_new)

    fix_edited_name_for_jpg()

    rename_iPhone_photos()

    # rename_iPhone_png
    rename_files_matching(search_str="*.PNG", suffix="", out_sub_dir="png")
    rename_files_matching(search_str="*.png", suffix="", out_sub_dir="png")

    # rename_iPhone_vids()
    rename_files_matching(search_str="IMG_*.MOV", suffix="", out_sub_dir="vids")
    rename_files_matching(search_str="IMG_*.MP4", suffix="", out_sub_dir="vids")

    # rename_telegram_photos()
    rename_files_matching(
        search_str="camphoto_*.jpg",
        suffix="_TG",
        out_sub_dir="Telegram",
        remove="camphoto_",
    )
    rename_files_matching(
        search_str="telegram-*.jpg",
        suffix="_TG",
        out_sub_dir="Telegram",
        remove="telegram-",
    )

    # rename_threema_photos()
    rename_files_matching(
        search_str="threema-*.jpg",
        suffix="_TM",
        out_sub_dir="Threema",
        remove="threema-",
    )
    rename_files_matching(
        search_str="threema-*.jpeg",
        suffix="_TM",
        out_sub_dir="Threema",
        remove="threema-",
    )

    rename_Whatsapp_files()


os.chdir(f"{basedir}")
dirs = []
for d in os.scandir("./"):
    if d.is_dir():
        dirs.append(d.name)

for d in dirs:
    doit(sub_dir=d)
