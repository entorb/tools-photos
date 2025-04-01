#!/usr/bin/env python3
"""
Synchronizes source and target photo directories.

resizing file in target dir to 1920px.
location online: https://github.com/entorb/Tools-Photos
location local: f:/FotoalbumSSD/Skripte
"""

# config is in PhotoSyncShrink.ini
# requirements:
# ImageMagick https://imagemagick.org
# DONE
# 1. delete from dirTarget
# 1.1 dirs that are not in dirSource
# 1.2 files that are not in dirSource
# 1.3 applying blacklist of not wanted files / dirs
# 2. copy from dirTarget
# 2.1 copy all
# 2.2 copy using backlist
# 2.3 shrinking pictures
# target: remove blacklisted files / dirs
# target: remove video and other files if not included in selection (.ini file)
# TODO
# blacklist: handle "*"

import multiprocessing  # for multiprocessing.cpu_count()
import os
import shutil
import subprocess
import time
from configparser import ConfigParser
from pathlib import Path

# from PIL import Image # pip3 install Pillow
# import piexif # pip3 install piexif
# PROBLEM:
# PIL Image.save() drops the IPTC data like tags, keywords, copywrite, ...
# so using ImageMagick instead
# install: download from https://imagemagick.org/
# V1: use command-line imagemagick's magick tool
# maybe later: V2: use python module https://docs.wand-py.org install see https://docs.wand-py.org/en/0.6.5/guide/install.html#install-imagemagick-on-windows


# options / settings / configuration parsed from .ini file
o: dict[str, str | bool | int] = {}
l_blacklist: list[str] = []
l_ext_img_files: list[str] = []
l_ext_video_files: list[str] = []
l_ext_other_files: list[str] = []
l_magick_param: list[str] = []
l_subprocesses: list[subprocess.Popen[str]] = []  # list of subprocesses

# TODO:
# shutil.rmtree("e:/tmp/target-PY/")
# os.makedirs("e:/tmp/target-PY/", exist_ok=True) # = mkdir -p
# if os.path.isfile("e:/tmp/target-PY/Dir1/180000 Rennen/180127_121042_tm.JPEG"):
#   os.remove("e:/tmp/target-PY/Dir1/180000 Rennen/180127_121042_tm.JPEG")

# Helper Functions


def read_config() -> None:
    """Read config file."""
    config = ConfigParser(interpolation=None)
    # interpolation=None -> treats % in values as char % instead of interpreting it
    config.read("photo_SyncShrink.ini", encoding="utf-8")

    o["dirSourceBase"] = config.get("general", "dirSourceBase").replace("\\", "/")
    o["dirTargetBase"] = config.get("general", "dirTargetBase").replace("\\", "/")
    assert isinstance(o["dirSourceBase"], str)
    assert isinstance(o["dirTargetBase"], str)

    assert Path(o["dirSourceBase"]).is_dir(), (
        f"source dir not found: {o['dirSourceBase']}"
    )
    assert Path(o["dirTargetBase"]).is_dir(), (
        f"target dir not found: {o['dirTargetBase']}"
    )

    global l_whitelist
    l_whitelist = sorted(config.get("general", "whitelist").lower().split())

    global l_blacklist
    l_blacklist = sorted(config.get("general", "blacklist").lower().split())

    o["copy_video_files"] = config.getboolean(
        "general",
        "copy_video_files",
    )
    o["copy_other_files"] = config.getboolean(
        "general",
        "copy_other_files",
    )
    o["copy_all_files"] = config.getboolean(
        "general",
        "copy_all_files",
    )

    global l_ext_img_files
    l_ext_img_files = sorted(
        [e.lower() for e in config.get("general", "ext_img_files").split()],
    )
    global l_ext_video_files
    l_ext_video_files = sorted(
        [e.lower() for e in config.get("general", "ext_video_files").split()],
    )

    global l_ext_other_files
    l_ext_other_files = sorted(
        [e.lower() for e in config.get("general", "ext_other_files").split()],
    )

    global l_ext_valid
    l_ext_valid = l_ext_img_files
    if o["copy_video_files"]:
        l_ext_valid.extend(l_ext_video_files)
    if o["copy_other_files"]:
        l_ext_valid.extend(l_ext_other_files)

    o["img_max_size"] = config.getint("general", "img_max_size")
    o["jpeg_quality"] = config.getint("general", "jpeg_quality")
    if o["jpeg_quality"] == 0:
        o["jpeg_quality"] = "keep"

    o["jpeg_remove_exif"] = config.getboolean("general", "jpeg_remove_exif")

    o["max_processes"] = multiprocessing.cpu_count()

    print("settings")
    for key, value in o.items():
        print(f" {key} = {value}")
    print("blacklist")
    for value in l_blacklist:
        print(f" {value}")
    print()


def is_in_blacklist(path: str) -> bool:  # noqa: D103
    ret = False
    for item in l_blacklist:
        if item in path.lower():
            ret = True
            break
    return ret


def set_magick_param() -> None:
    """Set common parameters for image magick convert command."""
    l_magick_param.append("-auto-orient")
    if o["jpeg_remove_exif"] is True:
        l_magick_param.append("-strip")
    l_magick_param.extend(
        ("-size", f"{o['img_max_size']}x{o['img_max_size']}"),
    )
    l_magick_param.extend(
        ("-resize", f"{o['img_max_size']}x{o['img_max_size']}>"),
    )
    # "1920x1920>" -> keep aspect ratio and resize only if larger


def process_enqueue(new_process_parameters: list[str]) -> None:
    global l_subprocesses
    # wait for free slot
    while len(l_subprocesses) >= o["max_processes"]:  # type: ignore
        process_remove_finished_from_queue()
        time.sleep(0.1)  # sleep 0.1s
    process = subprocess.Popen(  # noqa: S603
        new_process_parameters,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    l_subprocesses.append(process)


def process_remove_finished_from_queue() -> None:
    global l_subprocesses
    i = 0
    while i <= len(l_subprocesses) - 1:
        process = l_subprocesses[i]
        if process.poll is not None:  # has already finished
            process_print_output(process)
            l_subprocesses.pop(i)
        else:  # still running
            i += 1


def process_wait_for_all_finished() -> None:
    global l_subprocesses
    for process in l_subprocesses:
        process_print_output(process)
    l_subprocesses = []  # empty list of done subprocesses


def process_print_output(process: subprocess.Popen[str]) -> None:
    """Wait for process to finish and prints process output."""
    stdout, stderr = process.communicate()
    if stdout != "":
        print(f"Out: {stdout}")
    if stderr != "":
        print(f"ERROR: {stderr}")


# Main Functions


def clean_up_target_base() -> None:  # noqa: D103
    print("=== delete from dirTargetBase ===")
    # I only delete dirs not in whitelist, ignoring any file in target dir
    for d in os.scandir(o["dirTargetBase"]):
        if d.is_dir() and d.name not in l_whitelist:
            print(f"del {d.name}")
            shutil.rmtree(d.path)


def clean_up_target() -> None:  # noqa: D103
    print("=== delete from dirTarget ===")
    assert isinstance(o["dirSource"], str)
    assert isinstance(o["dirTarget"], str)
    for dirpath, dirnames, filenames in os.walk(o["dirTarget"]):
        dirpath = dirpath.replace("\\", "/")  # noqa: PLW2901

        # 1. check dirs
        for childitem in dirnames:
            target_path = os.path.join(dirpath, childitem).replace("\\", "/")
            target_path_rel = target_path[len(o["dirTarget"]) :]
            # 1.1 delete blacklisted dirs
            if is_in_blacklist(target_path):
                print(f"del {target_path}")
                shutil.rmtree(target_path)
                continue

            # 1.2 delete dirs not in source
            # replace from the left only
            source_path = o["dirSource"] + target_path[len(o["dirTarget"]) :]
            # print(f"{targetPath} <-- {sourcePath}")
            if not (os.path.isdir(source_path)):
                print(f"del {target_path_rel}")
                shutil.rmtree(target_path)
                continue

        # 2. check files
        for childitem in filenames:
            target_path = os.path.join(dirpath, childitem).replace("\\", "/")
            target_path_rel = target_path[len(o["dirTarget"]) :]
            file_ext = os.path.splitext(childitem)[1][1:].lower()  # without leading '.'

            # 2.1 delete blacklisted files
            # 2.2 delete files based on extension
            if is_in_blacklist(target_path) or file_ext not in l_ext_valid:
                print(f"del {target_path_rel}")
                os.remove(target_path)
                continue

            # 2.3 delete files not in source
            # replace from the left only
            source_path = o["dirSource"] + target_path[len(o["dirTarget"]) :]
            # sourcePath = targetPath.replace(o['dirTarget'], o['dirSource'])
            # print(f"{targetPath} <-- {sourcePath}")
            if not (os.path.isfile(source_path)):
                print(f"del {target_path_rel}")
                os.remove(target_path)
                continue


def sync_source_to_target() -> None:
    print("=== sync source to target ===")
    assert isinstance(o["dirSource"], str)
    assert isinstance(o["dirTarget"], str)
    for dirpath, dirnames, filenames in os.walk(o["dirSource"]):
        # create sub dirs
        for childitem in dirnames:
            sourcePath = os.path.join(dirpath, childitem).replace("\\", "/")
            if not is_in_blacklist(sourcePath):
                targetPath = o["dirTarget"] + sourcePath[len(o["dirSource"]) :]
                os.makedirs(targetPath, exist_ok=True)  # = mkdir -p
        # transfer files
        for childitem in filenames:
            sourcePath = os.path.join(dirpath, childitem).replace("\\", "/")

            if is_in_blacklist(sourcePath):
                continue  # skip this file

            targetPath = o["dirTarget"] + sourcePath[len(o["dirSource"]) :]
            # a = o['dirTarget']
            # b = sourcePath
            sourcePathRel = sourcePath[len(o["dirSource"]) :]
            # d = targetPath
            if os.path.isfile(targetPath):
                continue  # do nothing if file already exists

            file_ext = os.path.splitext(childitem)[1][1:].lower()  # without leading '.'

            if file_ext in l_ext_valid:
                if file_ext in ("jpg", "jpeg"):  # resize jpeg images
                    print(f"resizing {sourcePathRel}")
                    resize_image_imagemagick(sourcePath)
                else:  # copy other files
                    print(f"cp {sourcePathRel}")
                    shutil.copyfile(sourcePath, targetPath)


# def resize_image_PIL(fileIn: str):
#   fileOut = o['dirTarget'] + fileIn[len(o['dirSource']):]
#   # PROBLEM:
#   # PIL Image.save() drops the IPTC data like tags, keywords, copywrite, ...
#   # so using ImageMagick instead
#   # Read image
#   img = Image.open(fileIn)
#   # load exif data
#   exif_dict = piexif.load(img.info["exif"])
#   exif_bytes = piexif.dump(exif_dict)
#   # Resize keeping aspect ration -> img.thumbnail
#   # drops exif data, exif can be added from source file via exif= in save, see below
#   maxsize = o['img_max_size'], o['img_max_size']
#   img.thumbnail(maxsize, Image.ANTIALIAS)
#   # exif=dict_exif_bytes
#   img.save(fp=fileOut, format="JPEG",
#       quality=o['jpeg_quality'], exif=exif_bytes)


def resize_image_imagemagick(file_in: str) -> None:
    """
    Resize jpeg images using imagemagick command line tool.

    command:
    magick convert e:/tmp/source/Dir1/180127_121042_tm.jpg -auto-orient -size 1920x1920
    -resize 1920x1920> e:/tmp/target-PY/Dir1/180127_121042_tm.jpg
    """
    assert isinstance(o["dirSource"], str)
    assert isinstance(o["dirTarget"], str)
    file_out = o["dirTarget"] + file_in[len(o["dirSource"]) :]
    param: list[str] = []
    if os.name == "nt":
        param.append("magick")  # for windows we need to prepend this
    param.extend(("convert", file_in))
    param.extend(l_magick_param)
    param.append(file_out)
    # V1 single thread
    # process = subprocess.run(param, capture_output=True, text=True)
    # print(process.stdout)

    # V2 spawn subprocess
    process_enqueue(param)


if __name__ == "__main__":
    read_config()
    set_magick_param()
    clean_up_target_base()
    assert isinstance(o["dirSourceBase"], str)
    assert isinstance(o["dirTargetBase"], str)
    for dir_whitelist in l_whitelist:
        print(f"\n====== {dir_whitelist} ======")
        o["dirSource"] = o["dirSourceBase"] + "\\" + dir_whitelist
        o["dirTarget"] = o["dirTargetBase"] + "\\" + dir_whitelist

        clean_up_target()
        sync_source_to_target()
        process_wait_for_all_finished()
