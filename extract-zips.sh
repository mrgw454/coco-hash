#!/bin/bash

# purge and create archive folder
if [ -d archive ]; then
	rm -rf archive
fi

mkdir archive

# extract all files prior to processing
cd archive
find ../colorcomputerarchive.com -name "*.zip" | while read filename; do unzip -o "$filename"; done;

# rename all files to lowercase
# requires Debian package "rename" to be installed
echo
echo Renaming all files to lowercase.  This may take some time...
echo
find . -type f -iname "*.dsk" -execdir rename 's/(.*)/\L$1/' {} \;
echo

# remove all zip files
find ../colorcomputerarchive.com -type f -name '*.zip' -delete

# remove colorcomputerarchive.com folder
rm -rf ../colorcomputerarchive.com

echo
echo Done!
echo

