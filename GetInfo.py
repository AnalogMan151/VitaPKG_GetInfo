#!/usr/bin/env python3
# Author: AnalogMan
# Thanks to: mmozeiko & pkg2zip
# Ver 1.3
# Modified Date: 2018-03-19
# Purpose: Obtains Title ID, Title, Region, Minimum Firmware, Content ID, and Size from PKG header.
# Usage: GetInfo.py http://...

import sys
import urllib.request
from math import log

total_size = 0
pkg_type = ""

def pretty_size(n, pow=0, b=1024, u='B', pre=['']+[p+'i'for p in'KMGTPEZY']):
    pow, n = min(int(log(max(n*b**pow, 1), b)), len(pre)-1), n*b**pow
    return "%%.%if %%s%%s" % abs(pow % (-pow-1)) % (n/b**float(pow), pre[pow], u)

def get16le(data, i):
    return (int.from_bytes(data[i:i+2], byteorder='little'))

def get32le(data, i):
    return (int.from_bytes(data[i:i+4], byteorder='little'))

def get32be(data, i):
    return (int.from_bytes(data[i:i+4], byteorder='big'))

def get64be(data, i):
    return (int.from_bytes(data[i:i+8], byteorder='big'))

def GetRegion(id):
    if id == "U":
        return "USA"
    elif id == "E":
        return "EUR"
    elif id == "J":
        return "JPN"
    elif id == "K":
        return "KOR"
    elif id == "H":
        return "HKG"
    elif id == "I":
        return "INT"
    else:
        return "???"

def GetSFO(header):
    global total_size
    global pkg_type
    meta_offset = get32be(header, 8)
    meta_count = get32be(header, 12)
    content_type = 0
    sfo_offset = 0
    sfo_size = 0
    items_offset = 0
    items_size = 0
    total_size = get64be(header, 24)

    for i in range(meta_count):
        ctype = get32be(header, meta_offset)
        size = get32be(header, meta_offset + 4)

        if ctype == 2:
            content_type = get32be(header, meta_offset + 8)

        if ctype == 14:
            sfo_offset = get32be(header, meta_offset + 8)
            sfo_size = get32be(header, meta_offset + 12)
        
        meta_offset += 2 * 4 + size
    
    if content_type == 0x15:
        pkg_type = "VITA APP"
    elif content_type == 0x16:
        pkg_type = "VITA DLC"
    elif content_type == 0x1F:
        pkg_type = "VITA THEME"
    else:
        print("\nERROR: PKG type not supported.\n".format(content_type))
        sys.exit(1)
    
    return header[sfo_offset:sfo_offset + sfo_size]

def ParseSFO(sfo):
    if get32le(sfo, 0) != 0x46535000:
        return False

    keys = get32le(sfo, 8)
    values = get32le(sfo, 12)
    count = get32le(sfo, 16)

    title = "Undefined"
    contentid = "Undefined"
    min_ver = 0.0
    titleid = "Undefined"
    catagory = 0

    for i in range(count):
        index_key = keys + get16le(sfo, i * 16 + 20)
        index_value = values + get16le(sfo, i * 16 + 20 + 12)
        key = bytearray()
        for char in sfo[index_key:]:
            if char == 0:
                break
            key.append(char)
        value = bytearray()
        for char in sfo[index_value:]:
            if char == 0:
                break
            value.append(char)
        if key.decode("utf-8") == "TITLE":
            title = value.decode("utf-8")
        elif key.decode("utf-8") == "CONTENT_ID":
            contentid = value.decode("utf-8")
            titleid = value.decode("utf-8")[7:16]
        elif key.decode("utf-8") == "PSP2_DISP_VER":
            min_ver = float(value.decode("utf-8"))
        elif key.decode("utf-8") == "CATEGORY":
            category = value

    return titleid, title, min_ver, contentid, category

def main(argv):
    try:
        url = sys.argv[1]
    except:
        print("Usage: {} {}".format(sys.argv[0], 'http://...'))
        sys.exit(2)

    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-10000"})
        with urllib.request.urlopen(req) as f:
            header = f.read()
    except urllib.error.HTTPError:
        print("Could not open URL")
        sys.exit(2)
    
    titleid, title, min_ver, contentid, category = ParseSFO(GetSFO(header))
    region = GetRegion(contentid[0])

    global pkg_type
    if category.decode("utf-8") == "gp" and pkg_type == "VITA APP":
        pkg_type = "VITA UPDATE"

    print("\n")
    print("{:13} {}".format("Type:", pkg_type))
    print("{:13} {}".format("Title ID:", titleid))
    print("{:13} {}".format("Title:", title))
    print("{:13} {}".format("Region:", region))
    print("{:13} {}".format("Min FW:", min_ver))
    print("{:13} {}".format("Content ID:", contentid))
    print("{:13} {}".format("Size:", total_size))
    print("{:13} {}".format("Pretty Size:", pretty_size(total_size)))
    print("\n")

if __name__ == "__main__":
   main(sys.argv[0:1])
