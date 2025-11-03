# macOS Packaging Files

This directory contains the files needed for creating a macOS .dmg package.

## Files needed:

1. **background.png** - Background image for the DMG window (600x400 pixels recommended)
2. **Cruise.icns** - macOS application icon in .icns format

## Instructions:

### Creating background.png
- Create an image roughly 600x400 pixels
- Design it to guide users (app logo with arrow pointing to Applications folder)
- Save as background.png

### Creating Cruise.icns
Start with a high-quality square PNG (1024x1024 pixels recommended):

**Easy Method:** Use an online "PNG to ICNS converter"

**Professional Method (on Mac):**
```bash
mkdir Cruise.iconset
sips -z 1024 1024 logo.png --out Cruise.iconset/icon_512x512@2x.png
sips -z 512 512   logo.png --out Cruise.iconset/icon_512x512.png
sips -z 512 512   logo.png --out Cruise.iconset/icon_256x256@2x.png
sips -z 256 256   logo.png --out Cruise.iconset/icon_256x256.png
sips -z 256 256   logo.png --out Cruise.iconset/icon_128x128@2x.png
sips -z 128 128   logo.png --out Cruise.iconset/icon_128x128.png
iconutil -c icns Cruise.iconset
rm -r Cruise.iconset
```

Replace the placeholder files with your actual assets before building.