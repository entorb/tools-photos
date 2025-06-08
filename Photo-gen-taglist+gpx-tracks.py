"""
Jpeg -> GPX Traglist and + IPTC Taglist files

location online: https://github.com/entorb/tools/tree/master/Photo-Tools
location local:  f:\FotoalbumSSD\Skripte

Features
walks through a directory and its sub dirs
reads tags of all jpeg files
generates a 000000_gps.gpx track of all photos containing coordinates
generates a 000000_tags.txt list of all tags/keywords assigned to photos
generates a global DB of all tags
"""

# Bugs
#
#
# TODO:
# tags: per start_dir create a list
#
# IDEA:
# in the gps file create a new segment per day
# sum up the tags into the parent directory
#

import os
import re

import datetime
import platform
import pytz

from iptcinfo3 import IPTCInfo  # this works in pyhton 3!
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Settings
l_dirs = r"""
f:\FotoalbumSSD\Jahre\2020
f:\FotoalbumSSD\Jahre\2019
""".split()

file_tag_db = "f:/FotoalbumSSD/Jahre/000000_tags_db.txt"
l_dirs_to_skip = """
  .dtrash
""".split()

l_tags_to_skip = """
  Wer
"""

#
# Helper functions EXIF and Tags
#


def get_exif(filename: str) -> dict:
    """
    extracts exif data as dict from jpeg file
    """
    # from https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    image = Image.open(filename)
    image.verify()
    image.close()
    return image.getexif()


def get_labeled_exif(exif: dict) -> dict:
    """
    converts the exif key IDs into strings and returns that readable dict
    """
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val
    return labeled


# iptc_keys = ['object name', 'edit status', 'editorial update', 'urgency', 'subject reference', 'category', 'supplemental category', 'fixture identifier', 'keywords', 'content location code', 'content location name', 'release date', 'release time', 'expiration date', 'expiration time', 'special instructions', 'action advised', 'reference service', 'reference date', 'reference number', 'date created', 'time created', 'digital creation date', 'digital creation time', 'originating program', 'program version', 'object cycle', 'by-line', 'by-line title',
#              'city', 'sub-location', 'province/state', 'country/primary location code', 'country/primary location name', 'original transmission reference', 'headline', 'credit', 'source', 'copyright notice', 'contact', 'caption/abstract', 'local caption', 'writer/editor', 'image type', 'image orientation', 'language identifier', 'custom1', 'custom2', 'custom3', 'custom4', 'custom5', 'custom6', 'custom7', 'custom8', 'custom9', 'custom10', 'custom11', 'custom12', 'custom13', 'custom14', 'custom15', 'custom16', 'custom17', 'custom18', 'custom19', 'custom20']


def extractIptcKeywordTags(thisFile: str) -> list:
    """
    extracts IPTC keywords (=tags) from jpeg file
    """
    assert os.path.isfile(thisFile)
    iptc = IPTCInfo(thisFile)

    # for key in iptc_keys:
    #     if iptc[key]:
    #         print(f"{key}:")
    #         print(iptc[key])

    iptc_keywords = []
    if len(iptc['keywords']) > 0:  # or supplementalCategories or contacts
        for key in sorted(iptc['keywords']):
            # try:
            s = key.decode('utf-8')  # decode binary strings
            # s = key.decode('ascii')  # decode binary strings
            iptc_keywords.append(s)
            # except UnicodeDecodeError:
            #     continue
    return iptc_keywords


#
# Helper Functions Geo Location
#


def get_geotagging(exif: dict) -> dict:
    """returns the GPS related fields from the exif date dict"""
    # from https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    if not exif:
        raise ValueError("No EXIF metadata found")
    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")
            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]
    return geotagging


def get_decimal_from_dms(dms: tuple, ref: str) -> float:
    """
    converts exif internal DMS storage of GPS coordinates into a float
    """
    # from https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    # this was broken with new package version
    # degrees = dms[0][0] / dms[0][1]
    # minutes = dms[1][0] / dms[1][1] / 60.0
    # seconds = dms[2][0] / dms[2][1] / 3600.0
    degrees = float(dms[0])
    minutes = float(dms[1]) / 60.0
    seconds = float(dms[2]) / 3600.0
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return round(degrees + minutes + seconds, 5)


def get_coordinates(geotags) -> tuple:
    """converts exif internal storage of GPS coordinates into a (lat,lon)"""
    lat = get_decimal_from_dms(
        geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
    lon = get_decimal_from_dms(
        geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
    alt = 0
    # this was broken with new package version
    # if 'GPSAltitude' in geotags and geotags['GPSAltitude'][1] > 0:
    # alt = geotags['GPSAltitude'][0] / geotags['GPSAltitude'][1]
    if 'GPSAltitude' in geotags and geotags['GPSAltitude'] > 0:
        alt = int(round(float(geotags['GPSAltitude']), 0))
    return (lat, lon, alt)


#
# Helper Function Date and Time
#

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


def get_pic_datetime_as_str(path_to_file: str, exif_labeled: dict) -> str:
    picDate = ""
    if 'DateTime' in exif_labeled:
        s = exif_labeled['DateTime']
        picDate = dateStrLocalToUtc(s)
    elif 'DateTimeDigitized' in exif_labeled:
        s = exif_labeled['DateTimeDigitized']
        picDate = dateStrLocalToUtc(s)
    elif 'DateTimeOriginal' in exif_labeled:
        s = exif_labeled['DateTimeOriginal']
        picDate = dateStrLocalToUtc(s)
    else:
        # print("No date in exif found, using file creation or modification date instead, whatever is older")
        ts_file_created = creation_date(fileIn)
        # dt_file_created = datetime.datetime.fromtimestamp(ts_file_created)
        ts_file_modified = os.path.getmtime(fileIn)
        # dt_file_modified = datetime.datetime.fromtimestamp(ts_file_modified)
        if ts_file_created <= ts_file_modified and ts_file_created > 0:
            ts = ts_file_created
        else:
            ts = ts_file_modified
        picDate = datetime.datetime.utcfromtimestamp(
            ts).replace(microsecond=0).isoformat() + 'Z'
    return picDate


def dateStrLocalToUtc(datestr: str) -> str:
    """
    e.g. '2019:01:03 09:17:15' -> '2019-01-03T08:17:15+00:00'
    The format is "YYYY:MM:DD HH:MM:SS" with time shown in 24-hour format, and the date and time separated by one blank character (hex 20).
    https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif/datetimeoriginal.html
    """
    assert len(datestr) >= 19
    localTimeZone = pytz.timezone("Europe/Berlin")
    dateNaive = ""
    if datestr[4] == ':':
        fmt = '%Y:%m:%d %H:%M:%S'
    elif datestr[4] == '-':
        fmt = '%Y-%m-%d %H:%M:%S'
    dateNaive = datetime.datetime.strptime(datestr, fmt)

    # try:
    #     dateNaive = datetime.datetime.strptime(datestr, fmt)
    #     break
    # except ValueError:
    #     pass
    if dateNaive == "":
        raise ValueError('no valid date format found')
    # dateNaive = datetime.datetime.strptime(datestr, '%Y:%m:%d %H:%M:%S')
    local_dt = localTimeZone.localize(dateNaive, is_dst=None)
    datestr_utc = local_dt.astimezone(pytz.utc).isoformat()
    return datestr_utc


if __name__ == "__main__":
    d_tag_db = {}
    for start_dir in l_dirs:
        fileOut_startDir_tags = start_dir + '/' + '000000_tags.txt'
        fh_startDir_tags = open(fileOut_startDir_tags, mode='w',
                                encoding='utf-8', newline='\n')

        # walk into path and fetch all files matching extension jpe?g
        for (dirpath, dirnames, filenames) in os.walk(start_dir, topdown=True):
            dirpath = dirpath.replace('\\', '/')
            dirpath_rel = dirpath[len(start_dir)+1:]
            if dirpath_rel == "":
                dirpath_rel = dirpath

            # filter dirs to ignore
            dirnames[:] = [d for d in dirnames if d not in l_dirs_to_skip]

            # filter files to only jpegs
            filenames = [f for f in filenames if re.search(
                r'\.jpe?g$', f, re.IGNORECASE)]

            print('===')
            print('===' + dirpath_rel)
            print('===')
            # tags are counted in a dict
            # gps coordinates are collected in a list
            # for later writing both to files
            contTagsInThisDir = {}
            contGpxInThisDir = []

            for fileJpeg in filenames:
                print('==>', fileJpeg)
                fileIn = dirpath + '/' + fileJpeg

                # 1.1 IPTC tags
                tags = extractIptcKeywordTags(fileIn)
                for tag in tags:
                    if tag in l_tags_to_skip:
                        continue
                    if tag not in contTagsInThisDir:
                        contTagsInThisDir[tag] = 1
                    else:
                        contTagsInThisDir[tag] += 1

                # 1.2 EXIF for date and geo coordinates
                exif = get_exif(fileIn)
                exif_labeled = {}
                try:
                    exif_labeled = get_labeled_exif(exif)
                except:
                    pass  # except all

                # 1.2.1 date
                picDate = get_pic_datetime_as_str(
                    path_to_file=fileIn, exif_labeled=exif_labeled)

                # 1.2.1 Geo location
                picLatLonAlt = ()
                if exif:
                    try:
                        geotags = get_geotagging(exif)
                        picLatLonAlt = get_coordinates(geotags)
                    except ValueError:
                        pass
                    except KeyError:
                        pass

                if len(picLatLonAlt) == 3:
                    # print(picDate, picLatLonAlt[0], picLatLonAlt[1], picLatLonAlt[2])
                    s = f'<trkpt lat="{picLatLonAlt[0]}" lon="{picLatLonAlt[1]}"><time>{picDate}</time><name>{fileJpeg}</name>'
                    if picLatLonAlt[2] != 0:
                        s += f'<ele>{picLatLonAlt[2]}</ele>'
                    s += '</trkpt>'
                    contGpxInThisDir.append(s)
                # file loop
            # dir loop

            # 2.1 write list of tags in file per subdirectory
            if len(contTagsInThisDir) > 1:
                fileOut2 = dirpath + '/' + '000000_tags.txt'
                fh2 = open(fileOut2, mode='w', encoding='utf-8', newline='\n')
                for k in sorted(contTagsInThisDir.keys()):
                    fh2.write("" + k + "\t" + str(contTagsInThisDir[k])+"\n")
                fh2.close()

                fh_startDir_tags.write(
                    dirpath_rel+"\t"+", ".join(sorted(contTagsInThisDir.keys())) + "\n")

                for tag in sorted(contTagsInThisDir.keys()):
                    if tag not in d_tag_db:
                        d_tag_db[tag] = []
                    d_tag_db[tag].append(dirpath)

            # 2.2 write gpx track in file per subdirectory
            if len(contGpxInThisDir) > 1:
                fileOut1 = dirpath + '/' + '000000_gps.gpx'
                fh1 = open(fileOut1, mode='w', encoding='utf-8', newline='\n')
                date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
                gpxHead = f'<?xml version="1.0" encoding="UTF-8" ?>\n<gpx version="1.1" creator="Torben Menke, https://entorb.net" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.topografix.com/GPX/1/1" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">\n<metadata><time>{date}</time></metadata>\n<trk><trkseg>'
                fh1.write(gpxHead + "\n")
                fh1.write("\n".join(contGpxInThisDir))
                fh1.write("\n</trkseg></trk></gpx>\n")
                fh1.close()

        fh_startDir_tags.close()

        # write tag DB
        fh = open(file_tag_db, mode='w', encoding='utf-8', newline='\n')
        for tag in sorted(d_tag_db.keys()):
            l = d_tag_db[tag]
            fh.write(tag+"\n")
            fh.write("\n".join(sorted(l)))
            fh.write("\n\n")
        fh.close()
