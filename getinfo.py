#!/usr/bin/env python3
# Author: AnalogMan
# Thanks to: mmozeiko & pkg2zip
# Ver 1.4
# Modified Date: 2018-03-19
# Purpose: Obtains Type, Title ID, Title, Region, Minimum Firmware, App Version, Content ID, and Size from PKG header.
# Usage: 
# from getinfo import ParseSFO
# titleid, region, title, min_ver, contentid, total_size, pretty_size, pkg_type, category = ParseSFO(pkg_url)

import sys
import urllib.request
from math import log

total_size = 0
pkg_type = ''

# Formates the size from bytes to largest unit of data for easy reading
def pretty_size(n, pow=0, b=1024, u='B', pre=['']+[p+'i'for p in'KMGTPEZY']):
    pow, n = min(int(log(max(n*b**pow, 1), b)), len(pre)-1), n*b**pow
    return '%%.%if %%s%%s' % abs(pow % (-pow-1)) % (n/b**float(pow), pre[pow], u)

# Retrieve N bytes of data in little endian from passed data set starting at passed offset
def readLE(data, offset, length):
    return (int.from_bytes(data[offset:offset+length], byteorder='little'))

# Retrieve N bytes of data in big endian from passed data set starting at passed offset
def readBE(data, offset, length):
    return (int.from_bytes(data[offset:offset+length], byteorder='big'))

# Set region based on first character of Content ID
def GetRegion(id):
    if id == 'U':
        return 'USA'
    elif id == 'E':
        return 'EUR'
    elif id == 'J':
        return 'JPN'
    elif id == 'K':
        return 'KOR'
    elif id == 'H':
        return 'HKG'
    elif id == 'I':
        return 'INT'
    else:
        return '???'

def GetHeader(url):
    for _ in range(10):
        try:
            req = urllib.request.Request(url, headers={'Range': 'bytes=0-10000'})
            with urllib.request.urlopen(req) as f:
                header = f.read()
                return header
        except urllib.error.HTTPError:
            # print('Could not open URL')
            return b'\x00\x00\x00\x00'
        except ConnectionResetError:
            continue
    print("Connection tries reached")
    exit(2)

# Extracts param.sfo from passed header data from PKG file
def GetSFO(url):
    global pkg_type, total_size

    header = GetHeader(url)
    if readBE(header, 0, 4) != 0x7F504B47:
        return b'\x00\x00\x00\x00'

    # Read offset where meta data begins
    meta_offset = readBE(header, 8, 4)

    # Read number of meta data elements
    meta_count = readBE(header, 12, 4)

    # Initialize variables
    content_type = 0
    sfo_offset = 0
    sfo_size = 0

    # Read total PKG size from header
    total_size = readBE(header, 24, 8)

    # Loop through meta data elements to obtain content type and SFO offset and size
    for _i in range(meta_count):
        ctype = readBE(header, meta_offset, 4)
        size = readBE(header, meta_offset + 4, 4)

        # Content type element found, read value
        if ctype == 2:
            content_type = readBE(header, meta_offset + 8, 4)

        # SFO offset and size element found, read value
        if ctype == 14:
            sfo_offset = readBE(header, meta_offset + 8, 4)
            sfo_size = readBE(header, meta_offset + 12, 4)

        meta_offset += 2 * 4 + size

    # Classify content type based on value obtained from loop
    if content_type == 0x15:
        pkg_type = 'VITA APP'
    elif content_type == 0x16:
        pkg_type = 'VITA DLC'
    elif content_type == 0x1F:
        pkg_type = 'VITA THEME'
    else:
        # print('\nERROR: PKG type not supported.\n')
        return b'\x00\x00\x00\x00'

    # Return slice containing param.sfo
    return header[sfo_offset:sfo_offset + sfo_size]

# Parses passed param.sfo for data
def ParseSFO(url):
    sfo = GetSFO(url)

    # Check MAGIC '\0PSF' to verify proper SFO file
    if readBE(sfo, 0, 4) != 0x00505346:
        return False

    # Obtain starting offsets for key indexes and value indexes and amount of key:value pairs
    keys = readLE(sfo, 8, 4)
    values = readLE(sfo, 12, 4)
    count = readLE(sfo, 16, 4)

    # Initialize variables
    title = 'Undefined'
    contentid = 'Undefined'
    min_ver = 0.0
    titleid = 'Undefined'
    category = 0

    # Loop through key:value pairs starting with the first
    for i in range(count):
        index_key = keys + readLE(sfo, i * 16 + 20, 2)
        index_value = values + readLE(sfo, i * 16 + 20 + 12, 2)
        key = bytearray()

        # Iterate over byte values until \00 terminator to get key string
        for char in sfo[index_key:]:
            if char == 0:
                break
            key.append(char)
        value = bytearray()

        # iterate over byte values until \00 terminator to get value string
        for char in sfo[index_value:]:
            if char == 0:
                break
            value.append(char)

        # Checks if key is one of the wanted data and assigns value if so
        if key.decode('utf-8') == 'TITLE':
            title = value.decode('utf-8').replace('\n', ' ')
        elif key.decode('utf-8') == 'CONTENT_ID':
            contentid = value.decode('utf-8')
            titleid = value.decode('utf-8')[7:16]
        elif key.decode('utf-8') == 'PSP2_DISP_VER':
            min_ver = float(value.decode('utf-8'))
        elif key.decode('utf-8') == 'CATEGORY':
            category = value.decode('utf-8')
        elif key.decode('utf-8') == 'APP_VER':
            app_ver = float(value.decode('utf-8'))

    # Returns all values obtained from param.sfo
    return titleid, GetRegion(contentid[0:1]), title, min_ver, contentid, total_size, pretty_size(total_size), pkg_type, category
