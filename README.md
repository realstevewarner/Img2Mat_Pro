## Image 2 Material Pro

Extract materials and color palettes from any image.  Generate production-ready **materials, swatches, labels, Blender Palettes, and Assets** with one click.

<img width="2079" height="1256" alt="Screengrab 2" src="https://github.com/user-attachments/assets/4f6ed37d-36ed-4ef5-b90f-a1097b6f0880" />

## Highlights

- **It just works.**  Load an image.  Click Generate Materials.  Done.
- **Simple UI** with Advanced Options
- **K-Means (RGB, Comfy)** or **Poster Unique** extraction
- **Lock Colors** allow you to ensure the specific color you want gets created as a material.
- **Auto-sized labels** that never exceed swatch width
- **Asset-ready materials** in the click of a button
- **Image Editor sync** will use whatever image is visible in the Image Editor
- **Plain English Color Names** created automatically
- **Blender Palette** creation for your texture painting needs

<img width="2078" height="1164" alt="Screengrab" src="https://github.com/user-attachments/assets/b8a2989b-4cac-4b5d-b033-bebb4a225ef8" />


## How to Use

1. Open **View3D → Sidebar → Img2Mat**.
2. Load an image into an Image Viewer window.  Make sure the **Sync with Image Viewer** checkbox is enabled at the top of the Img2Mat window.
3. Choose how many colors you want to pull by adjusting the **Palette Size** (default 8).
4. If you want to ensure a color gets added as a material, add a **Lock Color** and then sample from the image. Rename the color if you'd like.  You can use the custom name for this color by enabling the **Use Lock Names** checkbox.
5. In **Output**, enable **Generate Swatches**/**Generate Labels**/**Mark as Assets**/**Create Blender Palette** as desired.
6. Click **Generate Materials**.

## Pro Features

This tool is designed to simply work with zero fuss.  However it wouldn't be a Pro tool if it didn't offer options under the hood.  

If you toggle down the Options, you'll find two separate methods for sampling.  

**K-Means** is based on Christian Byrne's ComfyUI img2colors node.  It works 99.99% of the time, however if you find that the colors aren't accurate, you can try the Poster Unique method.

**Color Space** will sample images in sRGB (useful for JPG, PNG, etc.) by default.  If you're using an EXR or HDR file, you can set the Color Space to **Linear to sRGB.**

**Sampling / Comfy K-Means / Lock Snapping** are all settings you can play with if the tool isn't grabbing accurate colors.  To be honest, I don't know what they do and I've never had to adjust them.  But there there if you want to play with them.  

**Naming** allows you to change the way the colloquial color names are applied.  If you find that the color names aren't quite matching what you'd expect, you can try a different method here.

**Subsurface** lets you determine if the colors will impact the resulting material's subsurface scattering.  Leave it at 0 for normal materials.  If you're doing leaves, skin, etc. set it to 0.2.  For wax, set it to 0.5.

**Assets & Palette** let you specify names for the assets and palettes created.
