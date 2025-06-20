#!/bin/bash

if [ ! -f coco-hash.bas ]; then
	echo coco-hash.bas file does NOT exist.  Aborting.
	echo
else
	echo coco-hash.bas file exists.  Compiling.
	echo
	fbc -lang qb coco-hash.bas

	if [ $? -eq 0 ]
	then
        	echo "Compilation was successful."
        	echo
	else
        	echo "Compilation was NOT successful.  Aborting installation." >&2
        	echo
        	exit 1
	fi
fi

echo
echo Done!
echo

