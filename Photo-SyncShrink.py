"""
'synchronizes' source and target photo directories while resizing file in target dir to 1920px

location online: https://github.com/entorb/Tools-Photos
location local:  f:\FotoalbumSSD\Skripte
"""

# config is in PhotoSyncShrink.ini

# DONE
# 1. delete from dirTarget
# 1.1 dirs that are not in dirSource
# 1.2 files that are not in dirSource
# 1.3 applying blacklist of not wanted files / dirs
# 2. copy from dirTarget
# 2.1 copy all
# 2.2 copy using backlist
# 2.3 shrinking pictures

# TODO
# target: remove blacklisted files

# Bugs


# setup
import time
import subprocess
import os
import shutil
from configparser import ConfigParser
# from PIL import Image  # pip3 install Pillow
# import piexif  # pip3 install piexif
# PROBLEM:
# PIL Image.save() drops the IPTC data like tags, keywords, copywrite, ...
# so using ImageMagick instead
# install: download from https://imagemagick.org/
# V1: use commandline imagemagick's magick tool
# maybe later: V2: use python module https://docs.wand-py.org install see https://docs.wand-py.org/en/0.6.5/guide/install.html#install-imagemagick-on-windows


o = {}  # options / settions / configuration parsed from .ini file
l_blacklist = []
l_ext_img_files = []
l_ext_video_files = []
l_ext_other_files = []
l_magick_param = []
l_subprocesses = []  # list of subprocesses

# TODO
# shutil.rmtree("e:/tmp/target-PY/")
# os.makedirs("e:/tmp/target-PY/", exist_ok=True)  # = mkdir -p
# if os.path.isfile("e:/tmp/target-PY/Dir1/180000 Rennen/180127_121042_tm.JPEG"):
#     os.remove("e:/tmp/target-PY/Dir1/180000 Rennen/180127_121042_tm.JPEG")

### Helper Functions ###


def read_config():
    config = ConfigParser(interpolation=None)
    # interpolation=None -> treats % in values as char % instead of interpreting it
    config.read('Photo-SyncShrink.ini', encoding='utf-8')

    o['dirSource'] = config.get('general', 'dirSource').replace('\\', '/')
    o['dirTarget'] = config.get('general', 'dirTarget').replace('\\', '/')
    assert os.path.isdir(
        o['dirSource']), f"source dir not found: {o['dirSource']}"
    assert os.path.isdir(
        o['dirTarget']), f"target dir not found: {o['dirTarget']}"

    global l_blacklist
    l_blacklist = sorted(config.get('general', 'blacklist').split())
    global l_ext_img_files
    l_ext_img_files = sorted([e.lower()
                              for e in config.get('general', 'ext_img_files').split()])
    global l_ext_video_files
    l_ext_video_files = sorted([e.lower()
                                for e in config.get('general', 'ext_video_files').split()])

    global l_ext_other_files
    l_ext_other_files = sorted([e.lower()
                                for e in config.get('general', 'ext_other_files').split()])

    o['img_max_size'] = config.getint('general', 'img_max_size')
    o['jpeg_quality'] = config.getint('general', 'jpeg_quality')
    if o['jpeg_quality'] == 0:
        o['jpeg_quality'] = 'keep'

    o['jpeg_remove_exif'] = config.getboolean('general', 'jpeg_remove_exif')

    o['copy_video_files'] = config.getboolean(
        'general', 'copy_video_files')
    o['copy_other_files'] = config.getboolean(
        'general', 'copy_other_files')
    o['copy_all_files'] = config.getboolean(
        'general', 'copy_all_files')

    o['max_processes'] = config.getint('general', 'max_processes')

    print("settings")
    for key, value in o.items():
        print(f"  {key} = {value}")
    print("blacklist")
    for value in l_blacklist:
        print(f"  {value}")
    print("")


def is_in_blacklist(path: str):
    ret = False
    for item in l_blacklist:
        if item in path:
            ret = True
            break
    return ret


def set_magick_param():
    """ sets common parameters for image magick convert command"""
    l_magick_param.append('-auto-orient')
    if o['jpeg_remove_exif'] == True:
        l_magick_param.append('-strip')
    l_magick_param.extend(
        ('-size', f"{o['img_max_size']}x{o['img_max_size']}"))
    l_magick_param.extend(
        ('-resize', f"{o['img_max_size']}x{o['img_max_size']}>"))
    # "1920x1920>" -> keep aspect ratio and resize only if larger


def process_enqueue(new_process_parameters):
    global l_subprocesses
    # wait for free slot
    while len(l_subprocesses) >= o['max_processes']:
        process_remove_finished_from_queue()
        time.sleep(0.1)  # sleep 0.1s
    process = subprocess.Popen(new_process_parameters,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    l_subprocesses.append(process)


def process_remove_finished_from_queue():
    global l_subprocesses
    i = 0
    while i <= len(l_subprocesses) - 1:
        process = l_subprocesses[i]
        if process.poll != None:  # has already finished
            process_print_output(process)
            l_subprocesses.pop(i)
        else:  # still running
            i += 1


def process_wait_for_all_finished():
    global l_subprocesses
    for process in l_subprocesses:
        process_print_output(process)
    l_subprocesses = []  # empty list of done subprocesses


def process_print_output(process):
    """waits for process to finish and prints process output"""
    stdout, stderr = process.communicate()
    if stdout != '':
        print(f'Out: {stdout}')
    if stderr != '':
        print(f'ERROR: {stderr}')


### Main Functions ###


def clean_up_target():
    print("=== delete from dirTarget ===")
    for (dirpath, dirnames, filenames) in os.walk(o['dirTarget']):
        dirpath = dirpath.replace('\\', '/')
        for childitem in dirnames:
            targetPath = os.path.join(dirpath, childitem).replace('\\', '/')
            # replace from the left only
            sourcePath = o['dirSource'] + targetPath[len(o['dirTarget']):]
            # sourcePath = targetPath.replace(o['dirTarget'], o['dirSource'])
            # print(f"{targetPath} <-- {sourcePath}")
            if not (os.path.isdir(sourcePath)):
                print(f"deleting {targetPath}")
                shutil.rmtree(targetPath)
            if is_in_blacklist(targetPath):
                print(f"deleting {targetPath}")
                shutil.rmtree(targetPath)
        for childitem in filenames:
            targetPath = os.path.join(dirpath, childitem).replace('\\', '/')
            # replace from the left only
            sourcePath = o['dirSource'] + targetPath[len(o['dirTarget']):]
            # sourcePath = targetPath.replace(o['dirTarget'], o['dirSource'])
            # print(f"{targetPath} <-- {sourcePath}")
            if not (os.path.isfile(sourcePath)):
                print(f"deleting {targetPath}")
                os.remove(targetPath)
            if is_in_blacklist(targetPath):
                print(f"deleting {targetPath}")
                os.remove(targetPath)


def sync_source_to_target():
    print("=== sync source to target ===")
    for (dirpath, dirnames, filenames) in os.walk(o['dirSource']):
        # create sub dirs
        for childitem in dirnames:
            sourcePath = os.path.join(dirpath, childitem).replace('\\', '/')
            if not is_in_blacklist(sourcePath):
                targetPath = o['dirTarget'] + sourcePath[len(o['dirSource']):]
                os.makedirs(targetPath, exist_ok=True)  # = mkdir -p
        # transfer files
        for childitem in filenames:
            sourcePath = os.path.join(dirpath, childitem).replace('\\', '/')

            if is_in_blacklist(sourcePath):
                continue  # skip this file

            targetPath = o['dirTarget'] + sourcePath[len(o['dirSource']):]
            if os.path.isfile(targetPath):
                continue  # do nothing if file already exists

            fileext = os.path.splitext(
                childitem)[1][1:].lower()  # without leading '.'

            if fileext in l_ext_img_files:
                if fileext in ('jpg', 'jpeg'):  # resize j  eg images
                    print(f"resizing {sourcePath[len(o['dirSource'])+1:]}")
                    resize_image_ImageMagick(sourcePath)
                else:
                    print(f"cp {sourcePath[len(o['dirSource'])+1:]}")
                    shutil.copyfile(sourcePath, targetPath)
            elif o['copy_video_files'] and fileext in l_ext_video_files:  # copy video files
                print(f"cp {sourcePath[len(o['dirSource'])+1:]}")
                shutil.copyfile(sourcePath, targetPath)
            elif o['copy_other_files'] and fileext in l_ext_other_files:  # copy other files
                print(f"cp {sourcePath[len(o['dirSource'])+1:]}")
                shutil.copyfile(sourcePath, targetPath)
            elif (o['copy_all_files']):  # copy all files
                print(f"cp {sourcePath[len(o['dirSource'])+1:]}")
                shutil.copyfile(sourcePath, targetPath)


# def resize_image_PIL(fileIn: str):
#     fileOut = o['dirTarget'] + fileIn[len(o['dirSource']):]
#     # PROBLEM:
#     # PIL Image.save() drops the IPTC data like tags, keywords, copywrite, ...
#     # so using ImageMagick instead
#     # Read image
#     img = Image.open(fileIn)
#     # load exif data
#     exif_dict = piexif.load(img.info["exif"])
#     exif_bytes = piexif.dump(exif_dict)
#     # Resize keeping aspect ration -> img.thumbnail
#     # drops exif data, exif can be added from source file via exif= in save, see below
#     maxsize = o['img_max_size'], o['img_max_size']
#     img.thumbnail(maxsize, Image.ANTIALIAS)
#     # exif=dict_exif_bytes
#     img.save(fp=fileOut, format="JPEG",
#              quality=o['jpeg_quality'], exif=exif_bytes)

def resize_image_ImageMagick(fileIn: str):
    """resize jpeg images usuing imagemagick command line tool
    command:
    magick convert e:/tmp/source/Dir1/180127_121042_tm.jpg -auto-orient -size 1920x1920 -resize 1920x1920> e:/tmp/target-PY/Dir1/180127_121042_tm.jpg
    """
    fileOut = o['dirTarget'] + fileIn[len(o['dirSource']):]
    param = []
    if os.name == 'nt':
        param.append("magick")  # for windows we need to prepend this
    param.extend(("convert", fileIn))
    param.extend(l_magick_param)
    param.append(fileOut)
    # V1 single thread
    # process = subprocess.run(param, capture_output=True, text=True)
    # print(process.stdout)

    # V2 spawn subprocess
    process_enqueue(param)


if __name__ == "__main__":
    read_config()
    set_magick_param()
    clean_up_target()
    sync_source_to_target()
    process_wait_for_all_finished()
