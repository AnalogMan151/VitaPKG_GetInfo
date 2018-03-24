#!/usr/bin/env python3
# Author: AnalogMan
# Thanks to: mmozeiko & pkg2zip
# Ver 1.4
# Modified Date: 2018-03-19
# Purpose: Obtains Type, Title ID, Title, Region, Minimum Firmware, App Version, Content ID, and Size from PKG header.
# Usage: GetInfo.py http://...

import sys
import urllib.request
from math import log

total_size = 0
pkg_type = ""

# Formates the size from bytes to largest unit of data for easy reading
def pretty_size(n, pow=0, b=1024, u='B', pre=['']+[p+'i'for p in'KMGTPEZY']):
    pow, n = min(int(log(max(n*b**pow, 1), b)), len(pre)-1), n*b**pow
    return "%%.%if %%s%%s" % abs(pow % (-pow-1)) % (n/b**float(pow), pre[pow], u)

# Retrieve 2 bytes of data in little endian from passed data set starting at passed offset
def get16le(data, offset):
    return (int.from_bytes(data[offset:offset+2], byteorder='little'))

# Retrieve 4 bytes of data in little endian from passed data set starting at passed offset
def get32le(data, offset):
    return (int.from_bytes(data[offset:offset+4], byteorder='little'))

# Retrieve 4 bytes of data in big endian from passed data set starting at passed offset
def get32be(data, offset):
    return (int.from_bytes(data[offset:offset+4], byteorder='big'))

# Retrieve 8 bytes of data in big endian from passed data set starting at passed offset
def get64be(data, offset):
    return (int.from_bytes(data[offset:offset+8], byteorder='big'))

# Set region based on first character of Content ID
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

# Extracts param.sfo from passed header data from PKG file
def GetSFO(header):
    global total_size
    global pkg_type
    
    # Read offset where meta data begins
    meta_offset = get32be(header, 8)
    
    # Read number of meta data elements
    meta_count = get32be(header, 12)
    
    # Initialize variables
    content_type = 0
    sfo_offset = 0
    sfo_size = 0
    
    # Read total PKG size from header
    total_size = get64be(header, 24)

    # Loop through meta data elements to obtain content type and SFO offset and size
    for _i in range(meta_count):
        ctype = get32be(header, meta_offset)
        size = get32be(header, meta_offset + 4)

        # Content type element found, read value
        if ctype == 2:
            content_type = get32be(header, meta_offset + 8)

        # SFO offset and size element found, read value
        if ctype == 14:
            sfo_offset = get32be(header, meta_offset + 8)
            sfo_size = get32be(header, meta_offset + 12)
        
        meta_offset += 2 * 4 + size

    # Classify content type based on value obtained from loop
    if content_type == 0x15:
        pkg_type = "VITA APP"
    elif content_type == 0x16:
        pkg_type = "VITA DLC"
    elif content_type == 0x1F:
        pkg_type = "VITA THEME"
    else:
        print("\nERROR: PKG type not supported.\n")
        sys.exit(1)
    
    # Return slice contianing param.sfo
    return header[sfo_offset:sfo_offset + sfo_size]

# Parses passed param.sfo for data
def ParseSFO(sfo):
    
    # Check MAGIC 'SFO\0' to verify proper SFO file
    if get32le(sfo, 0) != 0x46535000:
        return False

    # Obtain starting offsets for key indexes and value indexes and amount of key:value pairs
    keys = get32le(sfo, 8)
    values = get32le(sfo, 12)
    count = get32le(sfo, 16)

    # Initialize variables
    title = "Undefined"
    contentid = "Undefined"
    min_ver = 0.0
    titleid = "Undefined"
    category = 0
    app_ver = 0.0

    # Loop through key:value pairs starting with the first
    for i in range(count):
        index_key = keys + get16le(sfo, i * 16 + 20)
        index_value = values + get16le(sfo, i * 16 + 20 + 12)
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
        if key.decode("utf-8") == "TITLE":
            title = value.decode("utf-8").replace("\n", " ")
        elif key.decode("utf-8") == "CONTENT_ID":
            contentid = value.decode("utf-8")
            titleid = value.decode("utf-8")[7:16]
        elif key.decode("utf-8") == "PSP2_DISP_VER":
            min_ver = float(value.decode("utf-8"))
        elif key.decode("utf-8") == "CATEGORY":
            category = value
        elif key.decode("utf-8") == "APP_VER":
            app_ver = float(value.decode("utf-8"))

    # Returns all values obtained from param.sfo
    return titleid, title, min_ver, contentid, category, app_ver

def main(argv):
    try:
        url = sys.argv[1]
    except:
        print("Usage: {} {}".format(sys.argv[0], 'http://...'))
        sys.exit(2)

    # Download the first 10,000 bytes of the PKG file to obtain header and param.sfo
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-10000"})
        with urllib.request.urlopen(req) as f:
            header = f.read()
    except urllib.error.HTTPError:
        print("Could not open URL")
        sys.exit(2)
  
    # Assign variables by extracting param.sfo from header and then passing to ParseSFO
    titleid, title, min_ver, contentid, category, app_ver = ParseSFO(GetSFO(header))
    region = GetRegion(contentid[0])

    global pkg_type
    
    # Vita Updates are a sub-class of Vita Apps, check category to determine
    if category.decode("utf-8") == "gp" and pkg_type == "VITA APP":
        pkg_type = "VITA UPDATE"

    print("\n")
    print("{:13} {}".format("Type:", pkg_type))
    print("{:13} {}".format("Title ID:", titleid))
    print("{:13} {}".format("Title:", title))
    print("{:13} {}".format("Region:", region))
    print("{:13} {}".format("Min FW:", min_ver))
    print("{:13} {}".format("App Ver:", app_ver))
    print("{:13} {}".format("Content ID:", contentid))
    print("{:13} {}".format("Size:", total_size))
    print("{:13} {}".format("Pretty Size:", pretty_size(total_size)))
    print("\n")

if __name__ == "__main__":
   main(sys.argv[0:1])
