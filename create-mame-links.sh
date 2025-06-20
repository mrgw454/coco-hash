#!/bin/bash

# get script directory
scriptpath=$(dirname -- "$( readlink -f -- "$0"; )";)

# create new links to hash and software folders in standard MAME location

# for hash folder
if [ -L $HOME/.mame/hash ]; then
	echo previous hash symbolic folder exists.  Removing.
	echo
	rm $HOME/.mame/hash
fi

if [ -d $scriptpath/hash ]; then
	echo creating new symbolic link for hash
	ln -s $scriptpath/hash $HOME/.mame/hash
	ls -l $HOME/.mame/hash
	echo
else
	echo $scriptpath/hash does NOT exist.  Aborting.
	echo
	exit 1
fi

echo
echo

# for software folder
if [ -L $HOME/.mame/software ]; then
	echo previous software symbolic folder exists.  Removing.
	echo
	rm $HOME/.mame/software
fi

if [ -d $scriptpath/software ]; then
        echo creating new symbolic link for software
        ln -s $scriptpath/software $HOME/.mame/software
	ls -l $HOME/.mame/software
	echo
else
        echo $scriptpath/software does NOT exist.  Aborting.
        echo
        exit 1
fi


echo
echo Done!
echo
