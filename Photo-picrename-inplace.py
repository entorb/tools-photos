#!/usr/bin/env python3
"""
Renames files and photos based on date.

renames in place, not moved into subfolder

location online: https://github.com/entorb/Tools-Photos
location local:  f:/FotoalbumSSD/Skripte
"""
import glob
import os
import platform
from datetime import datetime

from PIL import Image

# import re
# from PIL import ExifTags


suffix = ""
# suffix = '_BM'

# skip these files
l_ignore = ("000_picrename_here.py", ".vscode")


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


def get_date(path_to_file) -> datetime:
    """
    Return datetime of file creation.

    1. for jpg images try reading from exif tag
    2. for others fetch modification date and creation date and use the older one
    """
    dt = datetime.fromtimestamp(0)  # 1.1.1970
    # for pictures try to read exif data
    fileext = os.path.splitext(path_to_file)[1]
    if fileext.lower() in (".jpg", ".jpeg"):
        image = Image.open(path_to_file)
        exif = image.getexif()
        exif_creation_time = exif.get(36867)
        if exif_creation_time:
            exif_creation_time = exif_creation_time.replace(":", "-", 2)
            dt_exif_creation = datetime.fromisoformat(exif_creation_time)
            dt = dt_exif_creation

    # else use file timestamp instead
    if dt == datetime.fromtimestamp(0):
        # creation time is a bit tricky
        ts_file_created = creation_date(path_to_file)
        dt_file_created = datetime.fromtimestamp(ts_file_created)

        ts_file_modified = os.path.getmtime(path_to_file)
        dt_file_modified = datetime.fromtimestamp(ts_file_modified)

        if (
            dt_file_created <= dt_file_modified
            and dt_file_created > datetime.fromtimestamp(0)
        ):
            dt = dt_file_created
        else:
            dt = dt_file_modified
        # del ts_file_created, ts_file_modified
    return dt


def gen_datestr(dt: datetime) -> str:
    """
    Format datetime to string.
    """
    return dt.strftime("%y%m%d_%H%M%S")


def gen_filename(filepath: str, suffix: str = "") -> tuple:
    """
    Return tuple of new filename , new extension.
    """
    dt = get_date(filepath)
    (filename, fileext) = os.path.splitext(filepath)
    datestr = gen_datestr(dt)
    count_identical_files = 0

    filename_new = f"{datestr}{suffix}"
    fileext_new = fileext.lower()
    if fileext_new == ".jpeg":
        fileext_new = ".jpg"

    # check if outfile already exists, if so append number
    while os.path.isfile(f"{filename_new}{fileext_new}"):
        count_identical_files += 1
        filename_new = f"{datestr}{suffix}_%02d" % count_identical_files

    return filename_new, fileext_new


def rename_file(filepath_old: str, filepath_new: str):
    """
    Perform the file renaming after some security checks.
    """
    # target_dir = os.path.split(filepath_new)[0]
    # assert os.path.isdir(target_dir), f"dir {target_dir} missing"
    assert filepath_old != filepath_new, f"{filepath_old}: newfile = oldfile"
    assert not os.path.isfile(
        filepath_new,
    ), f"{filepath_old}: {filepath_new} already exists"
    os.rename(filepath_old, filepath_new)


def rename_files_matching(search_str: str, suffix: str = ""):
    """
    Use glob in currend dir applying search_str.
    """
    for filepath in sorted(glob.glob(search_str)):
        filename = os.path.splitext(filepath)[0]
        if filename in l_ignore:
            continue
        filename_new, fileext_new = gen_filename(filepath, suffix)
        filepath_new = f"{filename_new}{fileext_new}"

        print(f"{filepath} -> {filepath_new}")
        rename_file(filepath, filepath_new)


rename_files_matching(search_str="*.jpg", suffix=suffix)
rename_files_matching(search_str="*.mp4", suffix=suffix)
