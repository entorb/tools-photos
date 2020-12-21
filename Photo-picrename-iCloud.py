"""
renames files and photos from iCloud Downloads based on date
run on Windows in directory iCloud Downloads

location online: https://github.com/entorb/Tools-Photos
location local:  f:\FotoalbumSSD\Skripte\
"""


import os
import glob
import platform
import re
from datetime import datetime

from PIL import Image, ExifTags  # pip3 install Pillow

os.chdir("f:\\FotoalbumSSD\\00_iCloud_download")

outfolder = 'renamed'
os.makedirs(f"{outfolder}/HEIC", exist_ok=True)  # = mkdir -p
os.makedirs(f"{outfolder}/png", exist_ok=True)  # = mkdir -p
os.makedirs(f"{outfolder}/vids", exist_ok=True)  # = mkdir -p
os.makedirs(f"{outfolder}/Telegram", exist_ok=True)  # = mkdir -p
os.makedirs(f"{outfolder}/WhatsApp", exist_ok=True)  # = mkdir -p

# skip these files
l_ignore = """
000_rename.py
.vscode
""".split()


def creation_date(path_to_file):
    """
    from https://stackoverflow.com/posts/39501288/1709587
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
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
    returns datetime of file creation
    1. for jpg images try reading from exif tag
    2. for others fetch modification date and creation date and use the older one
    """
    dt = datetime.fromtimestamp(0)  # 1.1.1970
    # for pictures try to read exif data
    fileext = os.path.splitext(path_to_file)[1]
    if (fileext.lower() in ('.jpg', '.jpeg')):
        image = Image.open(path_to_file)
        exif = image.getexif()
        exif_creation_time = exif.get(36867)
        if (exif_creation_time):
            exif_creation_time = exif_creation_time.replace(':', '-', 2)
            dt_exif_creation = datetime.fromisoformat(exif_creation_time)
            dt = dt_exif_creation

    # else use file timestamp instead
    if dt == datetime.fromtimestamp(0):
        # creation time is a bit tricky
        ts_file_created = creation_date(path_to_file)
        dt_file_created = datetime.fromtimestamp(ts_file_created)

        ts_file_modified = os.path.getmtime(path_to_file)
        dt_file_modified = datetime.fromtimestamp(ts_file_modified)

        if dt_file_created <= dt_file_modified and dt_file_created > datetime.fromtimestamp(0):
            dt = dt_file_created
        else:
            dt = dt_file_modified
        # del ts_file_created, ts_file_modified
    return dt


def gen_datestr(dt: datetime) -> str:
    """
    format datetime to string
    """
    return dt.strftime("%y%m%d_%H%M%S")


def gen_filename(filepath: str, suffix: str = '', outsubfolder: str = '') -> tuple:
    """
    returns tuple of new filename , new extension
    """
    dt = get_date(filepath)
    (filename, fileext) = os.path.splitext(filepath)
    datestr = gen_datestr(dt)
    count_identical_files = 0

    filename_new = f"{datestr}{suffix}"
    fileext_new = fileext.lower()
    if fileext_new == '.jpeg':
        fileext_new = '.jpg'

    # check if outfile already exists, if so append number
    while os.path.isfile(f"{outfolder}/{outsubfolder}/{filename_new}{fileext_new}"):
        count_identical_files += 1
        filename_new = f"{datestr}{suffix}_%02d" % count_identical_files

    return filename_new, fileext_new


def rename_file(filepath_old: str, filepath_new: str):
    """
    Perform the file renaming after some security checks
    """
    target_dir = os.path.split(filepath_new)[0]
    assert os.path.isdir(target_dir), f"dir {target_dir} missing"
    assert filepath_old != filepath_new, f"{filepath_old}: newfile = oldfile"
    assert not os.path.isfile(
        filepath_new), f"{filepath_old}: {filepath_new} already exists"
    os.rename(filepath_old, filepath_new)


def fix_edited_name_for_jpg():
    """
    for some strange reason I have
    IMG_1400 (Edited).HEIC
    IMG_1400(Edited).jpg -> space to add 
    """
    for filepath in sorted(glob.glob("*(Edited).*")):
        filepath_new = re.sub(re.compile(
            '(\d)(\(Edited\))'), r'\1 \2', filepath)
        if filepath != filepath_new:
            rename_file(filepath, filepath_new)


def rename_iPhone_photos():
    """
    rename IMG_*.jpg and same named.HEIC and _HEVC.MOV (dynamic Photos)
    """
    for filepath in sorted(glob.glob("IMG_*.jpg")):
        filename = os.path.splitext(filepath)[0]
        filename_new, fileext_new = gen_filename(filepath)
        filepath_new = f"{outfolder}/{filename_new}{fileext_new}"

        print(f"{filepath} -> {filepath_new}")
        rename_file(filepath, filepath_new)

        # for iPhone .jpg we usually also find a .HEIC and if enabled also a _HEVC.MOV
        for ext2 in (".HEIC", "_HEVC.MOV"):
            o = filename + ext2
            if os.path.isfile(o):
                n = f"{outfolder}/HEIC/{filename_new}{ext2.lower()}"

                print(f"{o} -> {n}")
                rename_file(o, n)


def rename_files_matching(search_str: str, suffix='', outsubfolder: str = ''):
    """
    use glob in currend dir applying search_str
    """
    for filepath in sorted(glob.glob(search_str)):
        filename = os.path.splitext(filepath)[0]
        filename_new, fileext_new = gen_filename(
            filepath, suffix, outsubfolder)
        filepath_new = f"{outfolder}/{outsubfolder}/{filename_new}{fileext_new}"

        print(f"{filepath} -> {filepath_new}")
        rename_file(filepath, filepath_new)


def rename_Whatsapp_files():
    """
    rename all files of filename matching
    exact 36 chars 
    of 0-9,a-f,A-F
    """
    myPatternWA = '^[0-9a-fA-F\-]+$'
    myRegExpWA = re.compile(myPatternWA)

    for f in os.scandir('./'):
        if not f.is_file or f.name in l_ignore:
            continue
        filepath = f.name  # name: without leading ./, path: with
        filename = os.path.splitext(f.name)[0]
        if len(filename) != 36:
            continue

        match = myRegExpWA.search(filename)
        if match:
            filename_new, fileext_new = gen_filename(
                filepath=filepath, suffix='_WA', outsubfolder='WhatsApp')
            filepath_new = f"{outfolder}/WhatsApp/{filename_new}{fileext_new}"
            print(f"{filepath} -> {filepath_new}")
            rename_file(filepath, filepath_new)
        else:
            # print("not matched")
            pass


fix_edited_name_for_jpg()

rename_iPhone_photos()

# rename_iPhone_png
rename_files_matching(search_str="IMG_*.PNG",
                      suffix="", outsubfolder="png")

# rename_iPhone_vids()
rename_files_matching(search_str="IMG_*.MOV",
                      suffix="", outsubfolder="vids")
rename_files_matching(search_str="IMG_*.MP4",
                      suffix="", outsubfolder="vids")

# rename_telegram_photos()
rename_files_matching(search_str="camphoto_*.jpg",
                      suffix="_TG", outsubfolder="Telegram")
rename_files_matching(search_str="telegram-*.jpg",
                      suffix="_TG", outsubfolder="Telegram")

rename_Whatsapp_files()
