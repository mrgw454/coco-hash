# coco-hash
Automated process for creating Color Computer Disk software hash files (XML) for MAME


1. Start by running the following command to download Color Computer disk images (in ZIP format) from the Color Computer Archive: 
  
  **./get-disk-images.sh**
  
  It's currently set to only download files from the 'Demos' folder, but you can edit the script to change the path that wget uses.


2. Once the wget download command is complete, run this command:

  **./extract-zips.sh**
  
  This will extract all the zip files in the ./colorcomputerarchive.com folder into the ./archive folder.


3. Finally, run this script to process the files you've downloaded and create the necessary MAME hash file (and software repo) for the Color Computer disk images:

  **./coco-hash.sh**
  
  
If using the CoCo-Pi distribution, you can allow MAME to see the CoCo disk based software by selecting the "Update MAME software HASH file for CoCo"
by going to the Utilities Menu, then Administration Menu.

When in MAME (CoCo drivers only), you can bring up the UI (normally the TAB key), select "File Manager", "FloppyDisk1 (or 2)", "software list", "Tandy Radio Shack Color Computer Disk Images."



Special thank you to **Guillaume Major** (owner of the Color Computer Archive) for hosting all the disk files and for assisting with this project.
