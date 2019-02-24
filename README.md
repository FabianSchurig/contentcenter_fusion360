# Customizable Content Center for Fusion 360

## Description
Choose from different customizable content and insert your selection into your Fusion design. Easily change the parameters to make the inserted file (screw, nut, ...) personal, such it fits your needs. You can also save your presets or upload your own customizable content to share with others. While finished to set up the part as you want it, you can join it to existing JointOrigins or to other inserted files.

Watch a video on how to use it.  
[![How to use it](https://img.youtube.com/vi/OzHQy3awX9Q/0.jpg)](https://www.youtube.com/watch?v=OzHQy3awX9Q)

## Available Content
You can browse throught the available content on my website https://custom.hk-fs.de/insert. I try to add more content over time. If you miss a part please let me know and I will try my best to add it.

## Installation

Use the Autodesk App Store links or try a manual installation. You only get the absolutely newest version with the manual installation. But the Add-In will also update itself to the newest available Version if you update from the Autodesk App Store. If something is not going well try the manual installation.

### Link to Autodesk App Store
[Windows 64 Version](https://apps.autodesk.com/FUSION/en/Detail/Index?id=4836063011761992262&appLang=en&os=Win64&autostart=true)  
[Mac OS Version](https://apps.autodesk.com/FUSION/en/Detail/Index?id=4836063011761992262&os=Mac&appLang=en)  

### Manual Installation

Update procedure moved to my own webserver, newest version can be downloaded from the following links.  
[contentcenter_fusion360.zip](https://custom.hk-fs.de/uploads/contentcenter_fusion360.zip)  
[contentcenter_fusion360.tar.gz](https://custom.hk-fs.de/uploads/contentcenter_fusion360.tar.gz)  

~~Note: You still have to install the missing python packages with pip into ./modules/modules~~

Extract the zip/tar.gz into the Fusion 360 Add-In Folder ~~and open a new terminal there.~~

Please place it in the correct folder depending from your OS:

```
Windows (web install):
Add-In: %appdata%\Autodesk\Autodesk Fusion 360\API\AddIns
 
Mac OS (web install):
Add-In: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns
 
Mac OS (Mac App Store [MAS]):
Add-In: ~/Library/Containers/com.autodesk.mas.fusion360/Data/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns
```

More help on manual installation can be found at [Autodesk here](https://knowledge.autodesk.com/support/fusion-360/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html)

Previous way on installing python packages (only needed if you clone the repository)
```
cd ./contentcenter_fusion360
pip install -r requirements.txt -t ./modules/modules/
In the ./modules/modules/ folder should be some new folders now if it worked.
``` 

## Upcoming and planned Features
- Material Selection
- More advanced thread selection
- More details on different parts (an image of the parameters, link to a shop to buy the screw)
- More parts

### Already Updated
~~- Don't recompute joints after one changed.~~  
~~- reading already imported files~~  
~~- import same content multiple times with different parameters without refreshing (F5)~~  

## Known Issues
~~If you open the Content Center and the existing joint origins are not recognized hit F5 to refresh the site.~~  
There is a big __Refresh!__ button shown if it is not connected.  

~~If the UI freezes try Alt-Tab out and in again and hit the Ok button of the error message.~~  

Material Selection is disabled, because it needs too much time.  

~~Because it recomputes every joint after a change happens to the joint selection, it definately needs too long.~~  
In large assemblies computing joints still needs too long.  

Change between designs in not possible so far. __Hit F5__ on the Panel of the Content Center to start over.  

~~Some preset names are empty because someone added presets with an empty name.~~  
I try to delete empty or faulty presets or content as fast as I can.  




