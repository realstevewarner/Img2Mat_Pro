## Image 2 Material Pro

Extract materials, color palettes, PMS/Pantone matches, and production callouts from any image. Generate production-ready **materials, swatches, labels, Blender Palettes, Assets, PMS color lists, and annotated callout boards** from a single image-driven workflow.

<img width="2079" height="1256" alt="Screengrab 2" src="https://github.com/user-attachments/assets/4f6ed37d-36ed-4ef5-b90f-a1097b6f0880" />

## Current Version

**1.29.0**

Download and install `img2mat_pro-1.29.0.zip` from this repository.

## Highlights

- **It just works.** Load an image. Click Generate Materials. Done.
- **Notable Colors** extraction balances broad image colors with visually distinct accent colors.
- **PMS/Pantone matching** converts extracted image colors into nearest imported color-library matches.
- **Single Color Sample** lets you match one sampled color without replacing the full PMS results list.
- **Callouts** create a reference image board with color swatches, labels, and lines back to sampled areas.
- **Lock Colors** ensure critical named colors make it into the material and PMS lists.
- **Auto-sized labels** that never exceed swatch width.
- **Asset-ready materials** in the click of a button.
- **Image Editor sync** uses whatever image is visible in the Image Editor.
- **Plain English color names** are created automatically.
- **Blender Palette** creation for texture painting workflows.

<img width="2078" height="1164" alt="Screengrab" src="https://github.com/user-attachments/assets/b8a2989b-4cac-4b5d-b033-bebb4a225ef8" />

## Install

1. Download `img2mat_pro-1.29.0.zip`.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Choose **Install from Disk** and select the zip file.
4. Enable **Image to Material**.
5. Open **View3D > Sidebar > Img2Mat**.

## Basic Workflow

1. Load an image into an Image Editor window.
2. Keep **Sync with Image Viewer** enabled at the top of the Img2Mat panel.
3. Choose the **Palette Size**.
4. Add **Lock Colors** for any named colors that must be included.
5. Use the bottom action buttons:
   - **Generate Materials** creates materials, swatches, labels, assets, and Blender palettes according to Output settings.
   - **Get PMS Colors** extracts the palette and matches it to the selected imported color library.
   - **Create Callouts** creates an annotated image board from the PMS results.
   - **Clear Swatches** clears generated swatches, callouts, and PMS lists.

## Pantone / PMS Libraries

This add-on does **not** ship with proprietary Pantone libraries. Use the add-on preferences to import your own licensed Adobe Color Book (`.acb`) files. Imported libraries are converted to local JSON files for reuse.

Useful controls:

- **Library** shows installed/imported color libraries and lets you import ACB files or rebuild the library index.
- **Options > Pantone** lets you choose the match library, match method, and PMS text block name.
- **Output > Pantone** controls whether PMS swatches and a text list are created.
- **Pantone Match** is for single color sampling and PMS result review.

## Pro Options

The tool is designed to work with very little setup. The collapsible **Options** section exposes deeper controls when needed.

- **Color Sampling Method** chooses Notable Colors, K-Means RGB, or Poster Unique extraction.
- **Seed** allows repeatable or varied palette extraction for Notable Colors and K-Means.
- **Color Space** lets you sample images as sRGB or convert linear values to sRGB.
- **Sampling** controls whether pixels are sampled by stride or uniform grid.
- **Lock Snapping** controls how close extracted colors need to be before snapping to a lock color.
- **Naming** changes the way colloquial color names are generated.
- **Subsurface** applies a default subsurface value to generated materials.
- **Assets & Palette** controls asset tags and Blender Palette naming.

## Notes for Maintainers

`Image2Mat_Pro.py` is included as the readable source copy. The Blender-installable zip contains the same file as `__init__.py` plus `blender_manifest.toml`.
