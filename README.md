# Customizable Content Center for Fusion 360

## Description
Choose from different customizable content and insert your selection into your Fusion design. Easily change the parameters to make the inserted file (screw, nut, ...) personal, such it fits your needs. You can also save your presets or upload your own customizable content to share with others. While finished to set up the part as you want it, you can join it to existing JointOrigins or to other inserted files.

Watch a video on how to use it.  
[![How to use it](https://img.youtube.com/vi/M53IOyPjaKE/0.jpg)](https://www.youtube.com/watch?v=M53IOyPjaKE)

## Link to Autodesk App Store
Coming Soon!

## Installation

How to [install](https://knowledge.autodesk.com/support/fusion-360/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html) Fusion 360 AddIns. 

open terminal

```
cd "%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns"
```
git clone or download zip (and extract it) from repository
```
git clone https://github.com/Bitfroest/contentcenter_fusion360
cd contentcenter_fusion360
```
Install needed packages with pip into the Modules folder
```
pip install --install-option="--prefix=./Modules" -r requirements.txt
```

## Upcoming and planned Features
- Material Selection
- More advanced thread selection
- Don't recompute joints after one changed.
- More details on different parts (an image of the parameters, link to a shop to buy the screw)
- reading already imported files
- import same content multiple times with different parameters without refreshing (F5)

## Known Issues
If you open the Content Center and the existing joint origins are not recognized hit F5 to refresh the site.

If the UI freezes try Alt-Tab out and in again and hit the Ok button of the error message.

Material Selection is disabled, because it needs too much time.

Because it recomputes every joint after a change happens to the joint selection, it definately needs too long.

Change between designs in not possible so far. Hit F5 to start over.

Some preset names are empty because someone added presets with an empty name.




