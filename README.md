# Image 2 Material Pro

Turn an image into a production-ready material palette for Blender.

Image 2 Material Pro started as a fast way to extract colors from a reference image and turn them into clean Blender materials. Version 2.0 turns that idea into a full creative round trip: start with a mood image, generate materials, finish your scene, then convert the final render into PMS/Pantone-style color guidance and callouts for fabrication.

## Version 2.0

This is the biggest Image 2 Material Pro update yet. The tool now bridges design, visualization, and production by combining material generation, smarter color extraction, PMS matching, and annotated callouts in one workflow.

Download and install `img2mat_pro-2.0.0.zip`.

## Why It Matters

Creative teams often work from images: mood boards, renders, references, client art, scenic elevations, and finished looks. Image 2 Material Pro helps turn those images into usable Blender materials and vendor-friendly color information without rebuilding palettes by hand.

Use it to:

- Build Blender materials from a reference image in seconds.
- Preserve important accent colors that ordinary palette tools miss.
- Match extracted colors to imported PMS/Pantone libraries.
- Generate readable color lists for vendors, scenic artists, fabricators, and production teams.
- Create callout boards that show where each sampled color came from.

## Headline Features

### Pantone / PMS Matching

Import your own licensed Adobe Color Book (`.acb`) files and match image colors to the nearest library colors. Use a full extracted palette or sample a single color with Blender's color picker. The result is a clear PMS-style list that can travel with your design package.

### Notable Colors Sampling

Large areas can dominate an image, while the colors that matter most are sometimes small accents: a red rocket, a neon sign, a costume detail, or a key scenic element. The Notable Colors method balances overall palette coverage with visually distinct accent colors, helping the generated palette feel much closer to what a designer actually sees.

### Callouts

Turn PMS results into a visual callout board. The add-on places the source image in the viewport, creates color swatches and labels, and draws lines back to the approximate sampled areas. It is ideal for communicating color intent when a vendor needs more than a raw list of hex values.

### Lock Colors

Need a specific color to make the final palette? Add it as a Lock Color and name it. Locked names carry into materials and PMS output, so a color like `Rocket Red` stays identifiable through the whole workflow.

### Streamlined UI

The main actions now live together at the bottom of the panel: Generate Materials, Get PMS Colors, Create Callouts, and Clear Swatches. Advanced controls are tucked into collapsible sections so the everyday workflow stays clean.

### Clear Swatches

Clean up generated swatches, PMS matches, callouts, and result lists with one button. Useful while iterating through different images, seeds, or palette sizes.

## Typical Workflow

1. Load a reference image in Blender's Image Editor.
2. Choose a palette size and add any Lock Colors that must be preserved.
3. Click **Generate Materials** to create Blender materials, swatches, labels, assets, and palettes.
4. When you need production color guidance, click **Get PMS Colors**.
5. Click **Create Callouts** to make an annotated board that shows where the colors came from.
6. Share the PMS list and callout board with your fabrication or scenic team.

## Pantone Library Notice

Image 2 Material Pro does not include or redistribute proprietary Pantone libraries. To use PMS/Pantone matching, import your own licensed `.acb` color books through the add-on preferences. Imported libraries are converted into local JSON files for reuse on your machine.

## Installation

1. Download `img2mat_pro-2.0.0.zip`.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Choose **Install from Disk** and select the zip file.
4. Enable **Image to Material**.
5. Open **View3D > Sidebar > Img2Mat**.

## Included Files

- `img2mat_pro-2.0.0.zip` is the Blender-installable extension package.
- `Image2Mat_Pro.py` is included as the readable source copy for maintainers.

## License

Image 2 Material Pro is released under the GPL-3.0-or-later license.
