#!/bin/bash

if [ -d colorcomputerarchive.com ]; then
	echo previous colorcomputerarchive.com folder exists.  Deleting.
	echo
	rm -rf colorcomputerarchive.com
fi

# if no search parms, use generic URL's to grab software
if [ -z "$1" ]; then

	# use wget to download Color Computer disk images from Color Computer Archive (https://colorcomputerarchive.com/repo/Disks/)
	#wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/
	#wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Applications/
	wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Demos/
	#wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*"  -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Utilities/
	#wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Games/
	#wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/repo/Disks/Public%20Domain/

else

	echo
	echo Searching for $1 on colorcomputerarchive.com...
	echo
	wget -np --no-cookies -r -p -e robots=off -v --mirror --convert-links -U mozilla --level=1 --reject "*French*, *DrivePak*, *Portuguese*, *translation*, *OS-9*" -A.zip -A.pdf -A.rom -A.txt -A.jpg -A.gif -A.png -A.dsk -A.os9 -A.wav -A.c10 -A.bas https://colorcomputerarchive.com/search?q=$1
fi

echo
cd colorcomputerarchive.com/repo
recursively-delete-empty-folders.sh

cd ../..

echo
echo Done!
echo
