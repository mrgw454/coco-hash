#!/bin/bash

# create archive folder if it does not exist
if [ ! -d archive ]; then
	mkdir archive
fi

# unzip all files prior to processing
cd archive

#find . -name "*.zip" | while read filename; do unzip -o -d "`dirname "$filename"`" "$filename"; done;
find ../colorcomputerarchive.com -name "*.zip" | while read filename; do unzip -o "$filename"; done;

# remove all zip files (uncomment next line remove all zip files)
#find ../colorcomputerarchive.com -type f -name '*.zip' -delete

echo
echo Done!
echo

