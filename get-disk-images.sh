#!/bin/bash

if [ -d colorcomputerarchive.com ]; then
	echo previous colorcomputerarchive.com folder exists.  Deleting.
	echo
	rm -rf colorcomputerarchive.com
fi

# use wget to download Color Computer disk images from Color Computer Archive (https://colorcomputerarchive.com/repo/Disks/)
wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Demos/

echo
echo Done!
echo
