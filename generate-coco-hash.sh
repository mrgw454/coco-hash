#!/bin/bash

# get script directory
scriptpath=$(dirname -- "$( readlink -f -- "$0"; )";)

# check to see if archive folder has any disk files to process
if [ -d archive ]
then
	if [ "$(ls -A archive)" ]; then
		echo "archive folder has files to process.  Proceeding..."
		echo

		# clean-up previous folders and files
		if [ -f coco-hash.csv ]; then
			rm coco-hash.csv
		fi

		if [ -d hash ]; then
			rm -rf hash
		fi

		mkdir hash

		if [ -d software ]; then
			rm -rf software
		fi

		mkdir -p software/coco_flop


		# find all DSK images, generate crc32 & sha1 hashs, grab file name (with path) and file size.  Write it out to a temp file (coco-hash.csv) for later processing

		counter=0

		shopt -s nocaseglob
		shopt -s globstar

		for i in archive/**/*.DSK; do # Whitespace-safe and recursive
			counter=$((counter+1))

			echo "$counter $i"

			# extract parent folder name from full path
			filepath=$i
			parentname="$(basename "$(dirname "$filepath")")"
			echo "$filepath"
			echo "$parentname"
			echo
			echo

			# check for copy protected images, etc., and exclude them
			if [[ $parentname != *"Translations"* ]] && [[ $parentname != *"protected"* ]] && [[ $parentfilename != *"OS-9"* ]] && [[ $parentfilename != *"Disto"* ]] && [[ $parentfilename != *"SDC"* ]] && [[ $parentfilename != *"OS9"* ]] && [[ $parentfilename != *"Burke"* ]] && [[ $parentfilename != *"Bible"* ]] && [[ $parentfilename != *"CoCoVGA"* ]] && [[ $parentfilename != *"French"* ]] && [[ $parentfilename != *"Portuguese"* ]] && [[ $parentfilename != *"Dragon32"* ]] ; then

				rhash -r -i -C -H -p '%h,%c,"%p","%f","%s"\r\n' "$i" >> coco-hash.csv
				cp "$i" software/coco_flop


			fi

		done

		shopt -u nocaseglob

		# process coco-hash/csv file and generate coco_flop.xml file for MAME
		./coco-hash coco-hash.csv

		# zip all DSK images, remove DSK image and keep ZIP file
		cd software/coco_flop
		for file in *; do zip "${file%.*}.zip" "$file"; rm "$file"; done

		echo
		echo Done!
		echo

	else
		echo "archive folder is empty. Aborting."
		echo
	fi

else
        echo "archive folder not found.  Aborting."
        echo
fi
