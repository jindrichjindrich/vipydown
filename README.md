# Vipydown - **Vi**deo **Py**thon **Down**loader

Vipydown is the all in one Python 3 script which runs a web
interface (both, server and client side) to [youtube_dl](https://pypi.org/project/youtube_dl/)
command line script used to download [Youtube](https://youtube.com) video files for local use.
It is intended for use (and tested) in Windows 10.

## Installation

Right now, the vipydown.py script can be used only as a standalone [Python](https://python.org) file
which you download and place to any empty folder of your choice. Also, the Python
(version 3.6 or above) must be installed on your computer and must be available
from command line (i.e., folder where the python.exe is located must be in the
PATH environmental variable).

  1. Download the [vipydown.py](https://raw.githubusercontent.com/jindrichjindrich/vipydown/master/vipydown.py)
  2. Move it to an empty folder of your choice to which you have a write access,
     e.g., C:\Users\USER\vipydown, where USER is the active Windows user account name
  3. Run the vipydown.py, either from cmd: "python vipydown.py" or by clicking
     the file with a mouse.
  4. The vipydown.py will create vipydown.lnk file in its folder and copy it
     to the Desktop folder, usually C:\Users\USER\Desktop, and to the startup
     folder, usually C:\Users\USER\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
     The vipydown.lnk file is then used to start the vipydown server and client.

To prevent starting vipydown upon computer startup, delete the vipydown.lnk file
from the startup folder.

## Usage

1. Start the vipydown server and web client by clicking the vipydown link on the Desktop
2. Wait few seconds for the server to update the youtube_dl module/script
3. Your default web browser will be pointed to the vipydown web page, where
   you can copy/paste address(es) of the video(s) you want to download. Also,
   list of already downloaded vides will be shown (obtained by inspecting log
   files located in log/ subfolder of your vipydown folder)
4. Click the Download button. The download will start and the downloaded files
   will be placed to default Download folder (usually C:\Users\USER\Downloads),
   eventually to its subfolder specified in the web interface.

