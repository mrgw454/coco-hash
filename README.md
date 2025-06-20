# coco-hash
Automated process for creating Color Computer Disk software hash files (XML) for MAME

**NOTE for CoCo-Pi users:**

If you update your CoCo-Pi using the "**Update CoCo-Pi from git repo**" feature, it will automatically download/clone this github repo into your /home/pi/source folder.

For those who wish to manually install it, select a top level folder of your choice and use the following command:

**git clone https://github.com/mrgw454/coco-hash.git**


Once downloaded/cloned, change into the 'coco-hash' directory and perform the follwing steps:

1. Start by running the following command to download Color Computer disk images (in ZIP format) from the Color Computer Archive: 
  
  **./get-disk-images-full.sh**
  
  It's currently set to only download files from the 'Demos' folder on the Color Computer Archive, but you can edit the script to change the path that wget uses.  If you pass a search term, it will only download software that it finds a match for.


2. Once the wget download command is complete, run this command:

  **./extract-zips.sh**
  
  This will extract all the zip files in the ./coco-hash/colorcomputerarchive.com folder into the ./coco-hash/archive folder.


3. Finally, run this script to process the files you've downloaded and create the necessary MAME hash file (and software repo) for the Color Computer disk images:

  **./coco-hash.sh**
  
  
If using the CoCo-Pi distribution, you can allow MAME to see the CoCo disk based software by selecting the "Update MAME software HASH file for CoCo"
by going to the Utilities Menu, then Administration Menu.

When in MAME (CoCo drivers only), you can bring up the UI (normally the TAB key), select "File Manager", "FloppyDisk1 (or 2)", "software list", "Tandy Radio Shack Color Computer Disk Images."



Special thank you to **Guillaume Major** (owner of the Color Computer Archive) for hosting all the disk files and for assisting with this project.
