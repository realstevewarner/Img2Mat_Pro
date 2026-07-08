bl_info = {
    "name": "Image to Material (Locks + Assets + Smart Names + Palettes + Pantone)",
    "author": "Steve Warner + Codex",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Img2Mat",
    "description": (
        "Comfy-style RGB K-Means + Top-N, uniform grid sampling, lock colors with exact snapping, "
        "Asset materials, Image-Editor sync, Blender Palette creation, ACB library conversion, and Pantone matching."
    ),
    "category": "Material",
}

import bpy
import colorsys
import random
import os
import json
import math
import struct
import hashlib
import traceback
from typing import List, Tuple, Dict, Optional

from bpy.props import (
    PointerProperty, FloatProperty, BoolProperty, IntProperty, EnumProperty,
    FloatVectorProperty, StringProperty, CollectionProperty
)
from bpy.types import Panel, Operator, PropertyGroup, UIList, AddonPreferences


# =============================================================================
# sRGB <-> Linear
# =============================================================================

def _srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def tuple_srgb_to_linear(rgb):
    r, g, b = rgb
    return (_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b))


def tuple_linear_to_srgb(rgb):
    r, g, b = rgb
    return (_linear_to_srgb(r), _linear_to_srgb(g), _linear_to_srgb(b))


# =============================================================================
# CSS names + helpers
# =============================================================================

CSS_UNION_HEX_TO_NAMES: Dict[str, str] = {
    "#000000": "black", "#000080": "navy", "#00008b": "darkblue", "#0000cd": "mediumblue", "#0000ff": "blue",
    "#006400": "darkgreen", "#008000": "green", "#008080": "teal", "#008b8b": "darkcyan", "#00bfff": "deepskyblue",
    "#00ced1": "darkturquoise", "#00fa9a": "mediumspringgreen", "#00ff00": "lime", "#00ffff": "aqua",
    "#191970": "midnightblue", "#1e90ff": "dodgerblue", "#20b2aa": "lightseagreen", "#228b22": "forestgreen",
    "#2e8b57": "seagreen", "#2f4f4f": "darkslategray", "#32cd32": "limegreen", "#3cb371": "mediumseagreen",
    "#40e0d0": "turquoise", "#4169e1": "royalblue", "#4682b4": "steelblue", "#483d8b": "darkslateblue",
    "#4b0082": "indigo", "#556b2f": "darkolivegreen", "#5f9ea0": "cadetblue", "#6495ed": "cornflowerblue",
    "#66cdaa": "mediumaquamarine", "#6a5acd": "slateblue", "#6b8e23": "olivedrab", "#708090": "slategray",
    "#778899": "lightslategray", "#7b68ee": "mediumslateblue", "#7cfc00": "lawngreen", "#7fff00": "chartreuse",
    "#7fffd4": "aquamarine", "#800000": "maroon", "#800080": "purple", "#808000": "olive", "#808080": "gray",
    "#87ceeb": "skyblue", "#87cefa": "lightskyblue", "#8a2be2": "blueviolet", "#8b0000": "darkred",
    "#8b4513": "saddlebrown", "#8fbc8f": "darkseagreen", "#90ee90": "lightgreen", "#9370db": "mediumpurple",
    "#98fb98": "palegreen", "#9acd32": "yellowgreen", "#a0522d": "sienna", "#a52a2a": "brown", "#a9a9a9": "darkgray",
    "#add8e6": "lightblue", "#adff2f": "greenyellow", "#b0c4de": "lightsteelblue", "#b0e0e6": "powderblue",
    "#b22222": "firebrick", "#bc8f8f": "rosybrown", "#c0c0c0": "silver", "#c71585": "mediumvioletred",
    "#cd5c5c": "indianred", "#cd853f": "peru", "#d2691e": "chocolate", "#d2b48c": "tan", "#d3d3d3": "lightgrey",
    "#d8bfd8": "thistle", "#daa520": "goldenrod", "#db7093": "palevioletred", "#dc143c": "crimson",
    "#deb887": "burlywood", "#e0ffff": "lightcyan", "#e6e6fa": "lavender", "#e9967a": "darksalmon",
    "#ee82ee": "violet", "#eee8aa": "palegoldenrod", "#f08080": "lightcoral", "#f0e68c": "khaki",
    "#f0f8ff": "aliceblue", "#f0fff0": "honeydew", "#f0ffff": "azure", "#f4a460": "sandybrown", "#f5deb3": "wheat",
    "#f5f5dc": "beige", "#f5f5f5": "whitesmoke", "#f5fffa": "mintcream", "#f8f8ff": "ghostwhite", "#fa8072": "salmon",
    "#faebd7": "antiquewhite", "#faf0e6": "linen", "#fafad2": "lightgoldenrodyellow", "#fbceb1": "apricot",
    "#fdf5e6": "oldlace", "#ff0000": "red", "#ff00ff": "fuchsia", "#ff1493": "deeppink", "#ff4500": "orangered",
    "#ff6347": "tomato", "#ff69b4": "hotpink", "#ff7f50": "coral", "#ff8c00": "darkorange", "#ffa07a": "lightsalmon",
    "#ffa500": "orange", "#ffb6c1": "lightpink", "#ffc0cb": "pink", "#ffd700": "gold", "#ffdab9": "peachpuff",
    "#ffdead": "navajowhite", "#ffe4b5": "moccasin", "#ffe4c4": "bisque", "#ffe4e1": "mistyrose", "#ffebcd": "blanchedalmond",
    "#ffefd5": "papayawhip", "#fff0f5": "lavenderblush", "#fff5ee": "seashell", "#fff8dc": "cornsilk",
    "#fffacd": "lemonchiffon", "#fffaf0": "floralwhite", "#ffff00": "yellow", "#ffffe0": "lightyellow", "#ffffff": "white"
}


def nearest_css_name_distance(r8, g8, b8):
    best_name, best_d, best_hex = "color", 1e9, None
    for hex_str, name in CSS_UNION_HEX_TO_NAMES.items():
        rr, gg, bb = int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16)
        d = abs(r8 - rr) + abs(g8 - gg) + abs(b8 - bb)
        if d < best_d:
            best_d, best_name, best_hex = d, name, hex_str
    return best_name.title(), best_d, best_hex


def hue_family_from_h(hdeg):
    h = hdeg % 360.0
    if h < 12 or h >= 348:
        return "Red"
    if h < 36:
        return "Orange"
    if h < 60:
        return "Yellow"
    if h < 96:
        return "Yellow-Green"
    if h < 156:
        return "Green"
    if h < 192:
        return "Cyan"
    if h < 264:
        return "Blue"
    if h < 312:
        return "Magenta"
    return "Red-Magenta"


def tone_prefix(s, v):
    if v < 0.22:
        return "Black"
    if v > 0.92 and s < 0.18:
        return "White"
    if s < 0.12:
        return "Gray"
    if v < 0.40:
        return "Dark"
    if v > 0.80 and s < 0.70:
        return "Light"
    if s < 0.40:
        return "Muted"
    return ""


def descriptive_name_from_rgb(rgb):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    fam = hue_family_from_h(h * 360.0)
    t = tone_prefix(s, v)
    return f"{t + ' ' if t else ''}{fam}"


def css_hue_guard_name_from_rgb(rgb):
    r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
    css_name, dist, _ = nearest_css_name_distance(r8, g8, b8)
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    fam = hue_family_from_h(h * 360.0)

    if v < 0.22 or (v > 0.92 and s < 0.18) or s < 0.12:
        return css_name.title()

    fam_map = {
        "Red": ["red", "crimson", "maroon", "firebrick", "tomato", "coral", "orangered"],
        "Orange": ["orange", "sandybrown", "chocolate", "peru", "sienna", "peach", "apricot", "goldenrod"],
        "Yellow": ["yellow", "khaki", "gold", "lemon", "ivory"],
        "Green": ["green", "olive", "chartreuse", "lime", "teal", "seagreen", "turquoise"],
        "Cyan": ["cyan", "aqua", "turquoise"],
        "Blue": ["blue", "navy", "royal", "sky", "indigo", "slate"],
        "Magenta": ["magenta", "fuchsia", "pink", "violet", "plum", "orchid"],
        "Red-Magenta": ["magenta", "red", "crimson", "fuchsia", "pink", "violet", "plum", "orchid"],
        "Yellow-Green": ["yellow", "green", "olive", "chartreuse", "lime"],
    }
    lower = css_name.lower()
    mismatch = not any(tok in lower for tok in fam_map.get(fam, []))
    if dist > 90 or mismatch:
        return descriptive_name_from_rgb(rgb)
    return css_name.title()


def rgb_to_hex(rgb):
    r, g, b = [max(0, min(255, round(v * 255))) for v in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


# =============================================================================
# ACB / library conversion helpers
# NOTE:
# - This is isolated from the existing image-to-material extraction pipeline.
# - Lab conversion below is only used for converting imported ACB library colors.
# =============================================================================

IMG2MAT_ACB_MODEL_MAP = {
    0: "RGB",
    2: "CMYK",
    7: "Lab",
}

IMG2MAT_LIBRARY_MANIFEST_NAME = "library_manifest.json"


def img2mat_sanitize_filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in name).strip()
    return safe.replace(" ", "_") or "library"


def img2mat_expand_special_tokens(text: str) -> str:
    if not text:
        return ""
    return text.replace("^R", "\u00AE").replace("^C", "\u00A9")

def img2mat_parse_localized_field(text: str) -> str:
    """
    Adobe ACB strings often look like:
    $$$/colorbook/PANTONE/title=tmp15F1.tmp.acb
    $$$/colorbook/PANTONE/prefix=PANTONE
    $$$/colorbook/PANTONE/postfix=
    "$$$/colorbook/PANTONE/description=Copyright^C X-Rite, 2013"

    We keep the original raw field elsewhere, but parse the value after '=' for UI/library use.
    """
    if text is None:
        return ""
    s = text.strip().strip('"')
    if "=" in s:
        s = s.split("=", 1)[1]
    return img2mat_expand_special_tokens(s).strip()


def img2mat_acb_display_title(filepath: str, parsed_title: str) -> str:
    stem = os.path.splitext(os.path.basename(filepath))[0]
    title = (parsed_title or "").strip()
    lower = title.lower()
    if not title or (lower.startswith("tmp") and lower.endswith(".acb")):
        return stem
    return title


def img2mat_join_color_name(prefix: str, name: str, suffix: str) -> str:
    parts = []
    if prefix and prefix.strip():
        parts.append(prefix.strip())
    if name and name.strip():
        parts.append(name.strip())
    if suffix and suffix.strip():
        parts.append(suffix.strip())
    return " ".join(parts).strip()


def img2mat_read_u32_string(data: bytes, offset: int) -> Tuple[str, int]:
    if offset + 4 > len(data):
        raise ValueError("Unexpected end of file while reading UTF-16BE string length.")
    length = struct.unpack_from(">I", data, offset)[0]
    offset += 4
    byte_count = length * 2
    if offset + byte_count > len(data):
        raise ValueError("Unexpected end of file while reading UTF-16BE string payload.")
    raw = data[offset:offset + byte_count]
    offset += byte_count
    return raw.decode("utf-16-be", errors="replace"), offset


def img2mat_lab_to_srgb(lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    CIELAB (D50-ish ACB payload usage in Adobe color books) -> XYZ -> sRGB.
    This is used only for creating preview RGB values for imported library entries.
    It does not touch the existing image extraction path.
    """
    L, a, b = lab

    fy = (L + 16.0) / 116.0
    fx = fy + (a / 500.0)
    fz = fy - (b / 200.0)

    def f_inv(t):
        t3 = t * t * t
        if t3 > 0.008856:
            return t3
        return (t - 16.0 / 116.0) / 7.787

    xr = f_inv(fx)
    yr = f_inv(fy)
    zr = f_inv(fz)

    # Reference white
    X = xr * 0.95047
    Y = yr * 1.00000
    Z = zr * 1.08883

    # XYZ -> linear RGB
    r_lin = X * 3.2406 + Y * -1.5372 + Z * -0.4986
    g_lin = X * -0.9689 + Y * 1.8758 + Z * 0.0415
    b_lin = X * 0.0557 + Y * -0.2040 + Z * 1.0570

    def linear_to_srgb_clamped(c):
        c = max(0.0, min(1.0, c))
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    return (
        max(0.0, min(1.0, linear_to_srgb_clamped(r_lin))),
        max(0.0, min(1.0, linear_to_srgb_clamped(g_lin))),
        max(0.0, min(1.0, linear_to_srgb_clamped(b_lin))),
    )


def img2mat_cmyk_bytes_to_srgb(bytes4: List[int]) -> Tuple[float, float, float]:
    """
    Adobe ACB CMYK bytes are stored as inverse quantized percentages.
    This is only for library conversion previews.
    """
    if len(bytes4) < 4:
        return (0.0, 0.0, 0.0)

    c = (255 - bytes4[0]) / 255.0
    m = (255 - bytes4[1]) / 255.0
    y = (255 - bytes4[2]) / 255.0
    k = (255 - bytes4[3]) / 255.0

    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))


def img2mat_components_to_preview_srgb(model_id: int, components: List[int]) -> Tuple[float, float, float]:
    if model_id == 0:  # RGB
        if len(components) < 3:
            return (0.0, 0.0, 0.0)
        return (
            max(0.0, min(1.0, components[0] / 255.0)),
            max(0.0, min(1.0, components[1] / 255.0)),
            max(0.0, min(1.0, components[2] / 255.0)),
        )

    if model_id == 2:  # CMYK
        return img2mat_cmyk_bytes_to_srgb(components[:4])

    if model_id == 7:  # Lab
        if len(components) < 3:
            return (0.0, 0.0, 0.0)
        L = components[0] * 100.0 / 255.0
        a = components[1] - 128.0
        b = components[2] - 128.0
        return img2mat_lab_to_srgb((L, a, b))

    return (0.0, 0.0, 0.0)


def img2mat_components_to_payload(model_id: int, components: List[int]) -> Dict[str, object]:
    if model_id == 0:
        return {
            "rgb_8bit": components[:3],
        }

    if model_id == 2:
        c = round((255 - components[0]) / 2.55, 1) if len(components) > 0 else 0.0
        m = round((255 - components[1]) / 2.55, 1) if len(components) > 1 else 0.0
        y = round((255 - components[2]) / 2.55, 1) if len(components) > 2 else 0.0
        k = round((255 - components[3]) / 2.55, 1) if len(components) > 3 else 0.0
        return {
            "cmyk_percent": [c, m, y, k],
        }

    if model_id == 7:
        L = round(components[0] * 100.0 / 255.0, 3) if len(components) > 0 else 0.0
        a = int(components[1] - 128) if len(components) > 1 else 0
        b = int(components[2] - 128) if len(components) > 2 else 0
        return {
            "lab": [L, a, b],
        }

    return {
        "raw_components": components[:]
    }


def img2mat_parse_acb_file(filepath: str) -> Dict[str, object]:
    with open(filepath, "rb") as f:
        data = f.read()

    if len(data) < 16:
        raise ValueError("ACB file is too small to be valid.")

    if data[:4] != b"8BCB":
        raise ValueError("Not a valid ACB file. Missing '8BCB' signature.")

    offset = 4
    version, book_id = struct.unpack_from(">HH", data, offset)
    offset += 4

    raw_title, offset = img2mat_read_u32_string(data, offset)
    raw_prefix, offset = img2mat_read_u32_string(data, offset)
    raw_suffix, offset = img2mat_read_u32_string(data, offset)
    raw_description, offset = img2mat_read_u32_string(data, offset)

    if offset + 8 > len(data):
        raise ValueError("ACB file ended before header color metadata.")

    color_count, page_size, page_selector_offset, model_id = struct.unpack_from(">HHHH", data, offset)
    offset += 8

    model_name = IMG2MAT_ACB_MODEL_MAP.get(model_id, f"Unknown({model_id})")
    component_count = 4 if model_id == 2 else 3

    colors = []
    for idx in range(color_count):
        name, offset = img2mat_read_u32_string(data, offset)

        if offset + 6 > len(data):
            raise ValueError(f"ACB file ended while reading short code for color {idx}.")

        short_code = data[offset:offset + 6].decode("ascii", errors="replace")
        offset += 6

        if offset + component_count > len(data):
            raise ValueError(f"ACB file ended while reading components for color {idx}.")

        components = list(data[offset:offset + component_count])
        offset += component_count

        preview_rgb = img2mat_components_to_preview_srgb(model_id, components)
        payload = img2mat_components_to_payload(model_id, components)

        full_name = img2mat_join_color_name(
            img2mat_parse_localized_field(raw_prefix),
            name,
            img2mat_parse_localized_field(raw_suffix)
        )

        color_record = {
            "index": idx,
            "name": name,
            "full_name": full_name if full_name else name,
            "short_code": short_code,
            "model_id": model_id,
            "model_name": model_name,
            "components_raw": components,
            "preview_rgb": [round(preview_rgb[0], 6), round(preview_rgb[1], 6), round(preview_rgb[2], 6)],
            "preview_hex": rgb_to_hex(preview_rgb),
        }
        color_record.update(payload)
        colors.append(color_record)

    trailer = ""
    if offset < len(data):
        try:
            trailer = data[offset:].decode("ascii", errors="replace")
        except Exception:
            trailer = ""

    parsed_title = img2mat_parse_localized_field(raw_title)

    return {
        "source_filename": os.path.basename(filepath),
        "source_filepath": filepath,
        "signature": "8BCB",
        "version": version,
        "book_id": book_id,
        "title_raw": raw_title,
        "prefix_raw": raw_prefix,
        "suffix_raw": raw_suffix,
        "description_raw": raw_description,
        "title": img2mat_acb_display_title(filepath, parsed_title),
        "prefix": img2mat_parse_localized_field(raw_prefix),
        "suffix": img2mat_parse_localized_field(raw_suffix),
        "description": img2mat_parse_localized_field(raw_description),
        "color_count": color_count,
        "page_size": page_size,
        "page_selector_offset": page_selector_offset,
        "model_id": model_id,
        "model_name": model_name,
        "trailer": trailer,
        "colors": colors,
    }


def img2mat_get_addon_prefs(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__name__)
    if not addon:
        return None
    return addon.preferences


def img2mat_addon_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def img2mat_default_acb_source_dir() -> str:
    candidate = os.path.join(img2mat_addon_dir(), "Pantone-color-libraries-master")
    return candidate if os.path.isdir(candidate) else ""


def img2mat_default_library_dir() -> str:
    base = bpy.utils.user_resource('CONFIG')
    if not base:
        base = os.path.expanduser("~")
    return os.path.join(base, "img2mat_libraries")


def img2mat_resolve_library_root(context=None) -> str:
    prefs = img2mat_get_addon_prefs(context)
    raw = prefs.library_root_dir.strip() if prefs else ""
    root = bpy.path.abspath(raw) if raw else img2mat_default_library_dir()
    os.makedirs(root, exist_ok=True)
    return root


def img2mat_manifest_path(context=None) -> str:
    return os.path.join(img2mat_resolve_library_root(context), IMG2MAT_LIBRARY_MANIFEST_NAME)


def img2mat_load_manifest(context=None) -> Dict[str, object]:
    path = img2mat_manifest_path(context)
    if not os.path.exists(path):
        return {"libraries": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"libraries": []}
        if "libraries" not in data or not isinstance(data["libraries"], list):
            data["libraries"] = []
        return data
    except Exception:
        return {"libraries": []}


def img2mat_save_manifest(manifest: Dict[str, object], context=None):
    path = img2mat_manifest_path(context)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def img2mat_list_json_library_files(context=None) -> List[str]:
    root = img2mat_resolve_library_root(context)
    out = []
    if not os.path.isdir(root):
        return out
    for fn in os.listdir(root):
        if fn.lower().endswith(".json") and fn != IMG2MAT_LIBRARY_MANIFEST_NAME:
            out.append(os.path.join(root, fn))
    return sorted(out)


def img2mat_write_library_json(library_data: Dict[str, object], context=None) -> str:
    root = img2mat_resolve_library_root(context)

    title = library_data.get("title") or library_data.get("source_filename") or "library"
    model = library_data.get("model_name") or "Unknown"
    base_name = img2mat_sanitize_filename(f"{title}_{model}")
    output_path = os.path.join(root, f"{base_name}.json")

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            same_library = (
                existing.get("source_filename", "") == library_data.get("source_filename", "") or
                (
                    existing.get("book_id", None) == library_data.get("book_id", None) and
                    existing.get("title", "") == library_data.get("title", "") and
                    existing.get("model_name", "") == library_data.get("model_name", "")
                )
            )
        except Exception:
            same_library = True

        if not same_library:
            suffix = 1
            while os.path.exists(output_path):
                suffix += 1
                output_path = os.path.join(root, f"{base_name}_{suffix}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(library_data, f, indent=2, ensure_ascii=False)

    return output_path


def img2mat_upsert_manifest_entry(library_data: Dict[str, object], json_path: str, context=None):
    manifest = img2mat_load_manifest(context)
    libs = manifest.get("libraries", [])

    entry = {
        "title": library_data.get("title", ""),
        "model_name": library_data.get("model_name", ""),
        "book_id": library_data.get("book_id", -1),
        "color_count": library_data.get("color_count", 0),
        "source_filename": library_data.get("source_filename", ""),
        "json_filename": os.path.basename(json_path),
        "json_path": json_path,
        "enabled": True,
    }

    replaced = False
    for i, lib in enumerate(libs):
        same_path = os.path.normpath(lib.get("json_path", "")) == os.path.normpath(json_path)
        same_book = (
            lib.get("book_id", None) == entry["book_id"] and
            lib.get("title", "") == entry["title"] and
            lib.get("model_name", "") == entry["model_name"]
        )
        if same_path or same_book:
            libs[i] = {**lib, **entry}
            replaced = True
            break

    if not replaced:
        libs.append(entry)

    manifest["libraries"] = libs
    img2mat_save_manifest(manifest, context)


def img2mat_rebuild_manifest_from_disk(context=None) -> Dict[str, object]:
    libs = []
    for json_path in img2mat_list_json_library_files(context):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            libs.append({
                "title": data.get("title", os.path.splitext(os.path.basename(json_path))[0]),
                "model_name": data.get("model_name", "Unknown"),
                "book_id": data.get("book_id", -1),
                "color_count": data.get("color_count", 0),
                "source_filename": data.get("source_filename", ""),
                "json_filename": os.path.basename(json_path),
                "json_path": json_path,
                "enabled": True,
            })
        except Exception:
            continue

    manifest = {"libraries": libs}
    img2mat_save_manifest(manifest, context)
    return manifest


def img2mat_get_manifest_library_count(context=None) -> int:
    manifest = img2mat_load_manifest(context)
    return len(manifest.get("libraries", []))


def img2mat_get_enabled_library_count(context=None) -> int:
    manifest = img2mat_load_manifest(context)
    return sum(1 for x in manifest.get("libraries", []) if x.get("enabled", True))


IMG2MAT_LIBRARY_ENUM_CACHE = []


def img2mat_library_selector_id(lib_meta: Dict[str, object]) -> str:
    key = "|".join([
        str(lib_meta.get("json_filename", "")),
        str(lib_meta.get("title", "")),
        str(lib_meta.get("book_id", "")),
    ])
    return "LIB_" + hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()


def img2mat_pantone_library_items(self, context):
    global IMG2MAT_LIBRARY_ENUM_CACHE

    items = [
        (
            "SOLID_COATED",
            "Solid Coated",
            "Use the installed PANTONE+ Solid Coated library, preferring the V3 book when present",
            0,
        ),
        (
            "ALL_ENABLED",
            "All Enabled Libraries",
            "Search every enabled imported color library",
            1,
        ),
    ]

    try:
        manifest = img2mat_load_manifest(context)
        for idx, lib in enumerate(manifest.get("libraries", []), start=2):
            if not lib.get("enabled", True):
                continue
            title = lib.get("title", "Untitled")
            model = lib.get("model_name", "Unknown")
            count = lib.get("color_count", 0)
            source = lib.get("source_filename", lib.get("json_filename", ""))
            items.append((
                img2mat_library_selector_id(lib),
                title,
                f"{model} | {count} colors | {source}",
                idx,
            ))
    except Exception:
        pass

    IMG2MAT_LIBRARY_ENUM_CACHE = items
    return IMG2MAT_LIBRARY_ENUM_CACHE


def img2mat_load_library_from_manifest_entry(lib: Dict[str, object], context=None) -> Optional[Dict[str, object]]:
    root = img2mat_resolve_library_root(context)
    json_path = lib.get("json_path") or os.path.join(root, lib.get("json_filename", ""))
    if not json_path or not os.path.isfile(json_path):
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    data["_manifest_title"] = lib.get("title", data.get("title", ""))
    data["_json_path"] = json_path
    data["_selector_id"] = img2mat_library_selector_id(lib)
    return data


def img2mat_library_matches_filter(lib_meta: Dict[str, object], library_data: Dict[str, object], name_filter: str) -> bool:
    terms = [part.strip().lower() for part in (name_filter or "").split(",") if part.strip()]
    if not terms:
        return True

    haystack = " ".join([
        str(lib_meta.get("title", "")),
        str(lib_meta.get("source_filename", "")),
        str(lib_meta.get("json_filename", "")),
        str(library_data.get("title", "")),
        str(library_data.get("source_filename", "")),
    ]).lower()
    return any(term in haystack for term in terms)


def img2mat_load_enabled_libraries(context=None, name_filter: str = "") -> List[Dict[str, object]]:
    manifest = img2mat_load_manifest(context)
    loaded = []

    for lib in manifest.get("libraries", []):
        if not lib.get("enabled", True):
            continue

        data = img2mat_load_library_from_manifest_entry(lib, context)
        if data is None:
            continue

        if not img2mat_library_matches_filter(lib, data, name_filter):
            continue

        loaded.append(data)

    return loaded


def img2mat_library_is_preferred_solid_coated(library_data: Dict[str, object]) -> bool:
    text = " ".join([
        str(library_data.get("title", "")),
        str(library_data.get("source_filename", "")),
        str(library_data.get("_manifest_title", "")),
    ]).lower()
    if "solid coated" not in text:
        return False
    excluded = ("metallic", "pastel", "neon", "bridge", "cmyk", "extended", "goe")
    return not any(token in text for token in excluded)


def img2mat_load_libraries_for_selector(context=None, selector: str = "SOLID_COATED") -> List[Dict[str, object]]:
    selector = selector or "SOLID_COATED"

    if selector == "ALL_ENABLED":
        return img2mat_load_enabled_libraries(context, "")

    enabled = img2mat_load_enabled_libraries(context, "")

    if selector == "SOLID_COATED":
        solid = [lib for lib in enabled if img2mat_library_is_preferred_solid_coated(lib)]
        if not solid:
            return img2mat_load_enabled_libraries(context, "Solid Coated")

        def rank(library_data):
            text = " ".join([
                str(library_data.get("title", "")),
                str(library_data.get("source_filename", "")),
            ]).lower()
            if "v3" in text:
                return 0
            if "336" in text:
                return 1
            return 2

        solid.sort(key=rank)
        return [solid[0]]

    for lib in enabled:
        if lib.get("_selector_id") == selector:
            return [lib]

    return img2mat_load_enabled_libraries(context, "Solid Coated")


def img2mat_srgb_to_lab(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    r, g, b = [max(0.0, min(1.0, v)) for v in rgb]
    r_lin, g_lin, b_lin = (_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b))

    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    xr = x / 0.95047
    yr = y / 1.00000
    zr = z / 1.08883

    def f(t):
        if t > 0.008856:
            return t ** (1.0 / 3.0)
        return 7.787 * t + 16.0 / 116.0

    fx, fy, fz = f(xr), f(yr), f(zr)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def img2mat_color_distance(rgb_a: Tuple[float, float, float], rgb_b: Tuple[float, float, float], metric: str = "LAB") -> float:
    if metric == "RGB":
        return math.sqrt(
            (rgb_a[0] - rgb_b[0]) ** 2 +
            (rgb_a[1] - rgb_b[1]) ** 2 +
            (rgb_a[2] - rgb_b[2]) ** 2
        ) * 255.0

    lab_a = img2mat_srgb_to_lab(rgb_a)
    lab_b = img2mat_srgb_to_lab(rgb_b)
    return math.sqrt(
        (lab_a[0] - lab_b[0]) ** 2 +
        (lab_a[1] - lab_b[1]) ** 2 +
        (lab_a[2] - lab_b[2]) ** 2
    )


def img2mat_iter_library_colors(libraries: List[Dict[str, object]]):
    for library in libraries:
        library_title = library.get("title") or library.get("_manifest_title") or library.get("source_filename") or "Pantone Library"
        for color in library.get("colors", []):
            preview_rgb = color.get("preview_rgb")
            if not preview_rgb or len(preview_rgb) < 3:
                continue
            yield library, library_title, color, (
                max(0.0, min(1.0, float(preview_rgb[0]))),
                max(0.0, min(1.0, float(preview_rgb[1]))),
                max(0.0, min(1.0, float(preview_rgb[2]))),
            )


def img2mat_find_nearest_library_color(
        rgb: Tuple[float, float, float],
        libraries: List[Dict[str, object]],
        metric: str = "LAB"
) -> Optional[Dict[str, object]]:
    best = None
    best_distance = float("inf")

    for library, library_title, color, preview_rgb in img2mat_iter_library_colors(libraries):
        distance = img2mat_color_distance(rgb, preview_rgb, metric=metric)
        if distance < best_distance:
            best_distance = distance
            best = {
                "source_rgb": rgb,
                "match_rgb": preview_rgb,
                "source_hex": rgb_to_hex(rgb),
                "match_hex": color.get("preview_hex") or rgb_to_hex(preview_rgb),
                "pantone_name": color.get("full_name") or color.get("name") or "Pantone Color",
                "short_code": color.get("short_code", ""),
                "library_title": library_title,
                "library_source": library.get("source_filename", ""),
                "model_name": library.get("model_name", ""),
                "distance": best_distance,
                "metric": metric,
            }

    return best


def img2mat_format_pantone_match(match: Dict[str, object]) -> str:
    source_label = str(match.get("source_label", "")).strip()
    source_hex = match.get("source_hex", "")
    source_name = f"{source_label} {source_hex}".strip() if source_label else source_hex
    return (
        f"{source_name} -> {match.get('pantone_name', '')} "
        f"({match.get('match_hex', '')}) | {match.get('library_title', '')} | "
        f"{match.get('metric', 'LAB')} {float(match.get('distance', 0.0)):.2f}"
    )


def img2mat_format_pantone_results(results) -> str:
    return "\n".join(
        img2mat_format_pantone_match({
            "source_hex": item.source_hex,
            "source_label": item.source_label,
            "pantone_name": item.pantone_name,
            "match_hex": item.match_hex,
            "library_title": item.library_title,
            "metric": item.metric,
            "distance": item.distance,
        })
        for item in results
    )


def img2mat_format_combined_pantone_results(p) -> str:
    chunks = []
    palette_text = img2mat_format_pantone_results(p.pantone_results)
    sample_text = img2mat_format_pantone_results(p.pantone_sample_results)
    if palette_text:
        chunks.append(palette_text)
    if sample_text:
        chunks.append(sample_text)
    return "\n".join(chunks)


def img2mat_write_text_block(name: str, body: str):
    text = bpy.data.texts.get(name)
    if text is None:
        text = bpy.data.texts.new(name)
    text.clear()
    text.write(body)
    return text


# =============================================================================
# Image reading
# =============================================================================

def _get_pixels_linear(image: bpy.types.Image):
    if not image.has_data:
        image.pixels[:]
    px = list(image.pixels)
    w, h = image.size
    return w, h, [tuple(px[i:i + 4]) for i in range(0, len(px), 4)]


def read_pixels_as_is(image: bpy.types.Image, stride=1, alpha_min=0.05):
    w, h, data = _get_pixels_linear(image)
    out = []
    idx = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = data[idx]
            idx += 1
            if ((x + y * w) % max(1, stride)) != 0:
                continue
            if a < alpha_min:
                continue
            out.append((max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b))))
    return out


def read_pixels_linear_to_srgb(image: bpy.types.Image, stride=1, alpha_min=0.05):
    w, h, data = _get_pixels_linear(image)
    out = []
    idx = 0
    for y in range(h):
        for x in range(w):
            r_lin, g_lin, b_lin, a = data[idx]
            idx += 1
            if ((x + y * w) % max(1, stride)) != 0:
                continue
            if a < alpha_min:
                continue
            out.append(tuple_linear_to_srgb((r_lin, g_lin, b_lin)))
    return out


def read_pixels_uniform_grid(image: bpy.types.Image, cells=64, alpha_min=0.05, as_is=True):
    w, h, data = _get_pixels_linear(image)
    out = []
    cell_w = max(1, w // cells)
    cell_h = max(1, h // cells)
    for gy in range(cells):
        for gx in range(cells):
            cx = min(w - 1, gx * cell_w + cell_w // 2)
            cy = min(h - 1, gy * cell_h + cell_h // 2)
            idx = cy * w + cx
            r, g, b, a = data[idx]
            if a < alpha_min:
                continue
            if as_is:
                out.append((max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b))))
            else:
                out.append(tuple_linear_to_srgb((r, g, b)))
    return out


def img2mat_read_samples_with_coords(image: bpy.types.Image, p):
    w, h, data = _get_pixels_linear(image)
    out = []
    as_is = (p.pixel_colorspace == 'AS_IS')

    def convert_rgb(r, g, b):
        if as_is:
            return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))
        return tuple_linear_to_srgb((r, g, b))

    if p.sampling == 'GRID':
        cells = max(1, int(p.grid_cells))
        cell_w = max(1, w // cells)
        cell_h = max(1, h // cells)
        for gy in range(cells):
            for gx in range(cells):
                cx = min(w - 1, gx * cell_w + cell_w // 2)
                cy = min(h - 1, gy * cell_h + cell_h // 2)
                r, g, b, a = data[cy * w + cx]
                if a < p.alpha_min:
                    continue
                out.append((convert_rgb(r, g, b), cx, cy, w, h))
    else:
        stride = max(1, int(p.sample_stride))
        idx = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = data[idx]
                idx += 1
                if ((x + y * w) % stride) != 0:
                    continue
                if a < p.alpha_min:
                    continue
                out.append((convert_rgb(r, g, b), x, y, w, h))

    return out


def img2mat_find_sample_uv_for_srgb(samples, target_rgb):
    if not samples:
        return 0.5, 0.5

    best = None
    best_d = float("inf")
    tr, tg, tb = target_rgb
    for rgb, x, y, w, h in samples:
        d = (rgb[0] - tr) ** 2 + (rgb[1] - tg) ** 2 + (rgb[2] - tb) ** 2
        if d < best_d:
            best_d = d
            best = (x, y, w, h)

    x, y, w, h = best
    u = x / max(1, w - 1)
    v = y / max(1, h - 1)
    return max(0.0, min(1.0, u)), max(0.0, min(1.0, v))


# =============================================================================
# K-Means & Top-N
# =============================================================================

def kmeans_rgb_with_locks(points, k=9, iters=300, seed=0, locked=None):
    if not points:
        return []
    if locked is None:
        locked = []
    rnd = random.Random(seed)
    pts = points

    centroids = list(locked[:k])
    anchored = set(range(len(centroids)))

    need = max(0, k - len(centroids))
    if need > 0:
        if not centroids:
            centroids.append(pts[rnd.randrange(len(pts))])
        for _ in range(need):
            d2 = []
            for p in pts:
                mind = min((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2 for c in centroids)
                d2.append(mind)
            total = sum(d2) or 1.0
            r = rnd.random() * total
            upto = 0.0
            for p, w in zip(pts, d2):
                upto += w
                if upto >= r:
                    centroids.append(p)
                    break

    for _ in range(iters):
        buckets = [[] for _ in range(k)]
        for p in pts:
            idx = min(
                range(k),
                key=lambda i: (p[0] - centroids[i][0]) ** 2 + (p[1] - centroids[i][1]) ** 2 + (p[2] - centroids[i][2]) ** 2
            )
            buckets[idx].append(p)

        newc = []
        for i, b in enumerate(buckets):
            if i in anchored:
                newc.append(centroids[i])
            else:
                if b:
                    r = sum(p[0] for p in b) / len(b)
                    g = sum(p[1] for p in b) / len(b)
                    bb = sum(p[2] for p in b) / len(b)
                    newc.append((r, g, bb))
                else:
                    newc.append(pts[rnd.randrange(len(pts))])

        if all(
            abs(nc[0] - c[0]) < 1e-7 and abs(nc[1] - c[1]) < 1e-7 and abs(nc[2] - c[2]) < 1e-7
            for nc, c in zip(newc, centroids)
        ):
            centroids = newc
            break
        centroids = newc

    centroids.sort(key=lambda rgb: (colorsys.rgb_to_hsv(*rgb)[2], colorsys.rgb_to_hsv(*rgb)[0]), reverse=True)
    return centroids


def unique_top_n_with_locks(points, n=9, min_pct=0.002, locked=None):
    if locked is None:
        locked = []

    counts: Dict[Tuple[int, int, int], int] = {}
    for r, g, b in points:
        rr = max(0, min(255, round(r * 255)))
        gg = max(0, min(255, round(g * 255)))
        bb = max(0, min(255, round(b * 255)))
        counts[(rr, gg, bb)] = counts.get((rr, gg, bb), 0) + 1

    total = max(1, sum(counts.values()))
    items = [(rgb, c) for rgb, c in counts.items() if (c / total) >= min_pct]
    if not items:
        items = list(counts.items())
    items.sort(key=lambda x: x[1], reverse=True)

    out, seen = [], set()

    for r, g, b in locked:
        rr = max(0, min(255, round(r * 255)))
        gg = max(0, min(255, round(g * 255)))
        bb = max(0, min(255, round(b * 255)))
        key = (rr, gg, bb)
        if key not in seen:
            out.append((rr / 255.0, gg / 255.0, bb / 255.0))
            seen.add(key)
        if len(out) >= n:
            break

    for (rr, gg, bb), _ in items:
        if len(out) >= n:
            break
        if (rr, gg, bb) in seen:
            continue
        out.append((rr / 255.0, gg / 255.0, bb / 255.0))
        seen.add((rr, gg, bb))

    out.sort(key=lambda rgb: (colorsys.rgb_to_hsv(*rgb)[2], colorsys.rgb_to_hsv(*rgb)[0]), reverse=True)
    return out


def notable_colors_with_locks(points, n=9, locked=None, quant_bits=5, seed=0):
    if locked is None:
        locked = []
    if not points:
        return []

    quant_bits = max(3, min(6, int(quant_bits)))
    shift = 8 - quant_bits

    bins = {}
    accent_groups = {}
    for r, g, b in points:
        r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in (r, g, b)]
        key = (r8 >> shift, g8 >> shift, b8 >> shift)
        count, sr, sg, sb = bins.get(key, (0, 0.0, 0.0, 0.0))
        bins[key] = (count + 1, sr + r, sg + g, sb + b)

        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s >= 0.35 and v >= 0.16:
            hdeg = h * 360.0
            family = hue_family_from_h(hdeg)
            if hdeg < 42.0 or hdeg >= 342.0:
                family = "Warm Accent"
            weight = (s ** 2.0) * ((0.25 + v) ** 1.25)
            vividness = s * math.sqrt(max(0.0, v))
            accent_groups.setdefault(family, []).append((r, g, b, weight, vividness))

    total = max(1, len(points))
    candidates = []
    for count, sr, sg, sb in bins.values():
        rgb = (sr / count, sg / count, sb / count)
        h, s, v = colorsys.rgb_to_hsv(*rgb)
        presence = count / total

        frequency_score = presence ** 0.38
        chroma_score = 0.65 + 0.85 * s
        tone_score = 0.75 + 0.25 * (1.0 - abs(v - 0.55) / 0.55)
        if v < 0.18 or (v > 0.90 and s < 0.18):
            tone_score += 0.12

        importance = frequency_score * chroma_score * max(0.45, tone_score)
        candidates.append({
            "rgb": rgb,
            "count": count,
            "importance": importance,
            "kind": "area",
        })

    min_accent_count = max(4, int(total * 0.004))
    for family, items in accent_groups.items():
        if len(items) < min_accent_count:
            continue

        items.sort(key=lambda item: item[4], reverse=True)
        focused = items[:max(6, int(len(items) * 0.35))]
        total_weight = sum(item[3] for item in focused) or 1.0
        rgb = (
            sum(item[0] * item[3] for item in focused) / total_weight,
            sum(item[1] * item[3] for item in focused) / total_weight,
            sum(item[2] * item[3] for item in focused) / total_weight,
        )

        avg_s = sum(colorsys.rgb_to_hsv(item[0], item[1], item[2])[1] for item in focused) / len(focused)
        avg_v = sum(colorsys.rgb_to_hsv(item[0], item[1], item[2])[2] for item in focused) / len(focused)
        presence = len(items) / total
        importance = 0.20 + (presence ** 0.28) * 0.35 + avg_s * 0.24 + avg_v * 0.18
        if family == "Warm Accent":
            importance += 0.18

        candidates.append({
            "rgb": rgb,
            "count": len(items),
            "importance": importance,
            "kind": "accent",
            "family": family,
        })

    if seed:
        rnd = random.Random(seed)
        for item in candidates:
            item["seed_factor"] = 0.55 + rnd.random() * 0.90
            item["importance"] *= item["seed_factor"]
    else:
        for item in candidates:
            item["seed_factor"] = 1.0

    candidates.sort(key=lambda item: item["importance"], reverse=True)
    candidates = candidates[:max(n * 48, 256)]

    selected = []
    seen = set()

    for rgb in locked[:n]:
        r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
        key = (r8, g8, b8)
        if key not in seen:
            selected.append((r8 / 255.0, g8 / 255.0, b8 / 255.0))
            seen.add(key)

    while len(selected) < n and candidates:
        best_idx = None
        best_score = -1.0

        for idx, item in enumerate(candidates):
            rgb = item["rgb"]
            r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
            if (r8, g8, b8) in seen:
                continue

            if selected:
                min_distance = min(img2mat_color_distance(rgb, chosen, metric="LAB") for chosen in selected)
                if min_distance <= 8.0:
                    distinctness = 0.0
                else:
                    distinctness = min(1.0, ((min_distance - 8.0) / 36.0) ** 1.35)
                separation_score = 0.05 + 0.95 * distinctness
            else:
                separation_score = 1.0

            score = item["importance"] * separation_score
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is None:
            break

        item = candidates.pop(best_idx)
        rgb = item["rgb"]
        r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
        selected.append((r8 / 255.0, g8 / 255.0, b8 / 255.0))
        seen.add((r8, g8, b8))

    selected.sort(key=lambda rgb: (colorsys.rgb_to_hsv(*rgb)[2], colorsys.rgb_to_hsv(*rgb)[0]), reverse=True)
    return selected


# =============================================================================
# Materials / swatches / labels / palette
# =============================================================================

def ensure_collection(name: str):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_collection_objects(coll: bpy.types.Collection):
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def set_if_socket_exists(node, socket_name, value):
    inp = node.inputs.get(socket_name)
    if inp is not None:
        inp.default_value = value
        return True
    return False


def create_material_from_srgb(name: str, rgb_srgb, subsurf=0.0, mark_asset=False, asset_tag=""):
    r_s, g_s, b_s = [max(0.0, min(1.0, v)) for v in rgb_srgb]
    r_lin, g_lin, b_lin = tuple_srgb_to_linear((r_s, g_s, b_s))
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (r_lin, g_lin, b_lin, 1.0)
        if not set_if_socket_exists(bsdf, "Subsurface", subsurf):
            set_if_socket_exists(bsdf, "Subsurface Weight", subsurf)
    if mark_asset and hasattr(mat, "asset_mark"):
        mat.asset_mark()
        if asset_tag:
            try:
                mat.asset_data.tags.new(asset_tag)
            except Exception:
                pass
    return mat


def create_swatch_plane(x, y, size=1.6):
    mesh = bpy.data.meshes.new("Img2Mat_Swatch")
    obj = bpy.data.objects.new("Img2Mat_Swatch", mesh)
    verts = [(x, y, 0), (x + size, y, 0), (x + size, y + size, 0), (x, y + size, 0)]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return obj


def create_label(text, x, y):
    txt = bpy.data.curves.new(type="FONT", name="Img2Mat_Label")
    obj = bpy.data.objects.new("Img2Mat_Label", txt)
    txt.body = text
    txt.align_x = 'CENTER'
    txt.size = 1.0
    obj.location = (x + 0.8, y - 0.15, 0)
    obj.scale = (0.2, 0.2, 0.2)
    return obj


def fit_label_to_width(obj, max_width: float):
    try:
        bpy.context.view_layer.update()
        width = obj.dimensions.x
        if width <= 0.0:
            return
        current_scale = obj.scale.x
        effective_width = width * current_scale
        if effective_width > max_width:
            factor = max_width / effective_width
            obj.scale = (current_scale * factor, current_scale * factor, current_scale * factor)
            bpy.context.view_layer.update()
    except Exception:
        pass


def ensure_palette(name: str):
    pal = bpy.data.palettes.get(name)
    if pal is None:
        pal = bpy.data.palettes.new(name)
    while pal.colors:
        pal.colors.remove(pal.colors[-1])
    return pal


def img2mat_parent_keep_world(child, parent):
    world_matrix = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world_matrix


def img2mat_create_centered_swatch_plane(name, center_x, center_y, size=0.72):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    h = size / 2.0
    verts = [(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = (center_x, center_y, 0.0)
    return obj


def img2mat_create_callout_anchor(name, location, coll, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.08
    obj.location = location
    obj.hide_select = True
    coll.objects.link(obj)
    if parent is not None:
        img2mat_parent_keep_world(obj, parent)
    return obj


def img2mat_callout_line_material():
    mat = bpy.data.materials.get("Img2Mat_Callout_Line")
    if mat is None:
        mat = bpy.data.materials.new("Img2Mat_Callout_Line")
    mat.diffuse_color = (0.24, 0.58, 0.88, 1.0)
    return mat


def img2mat_driver_point_to_object_location(point, target_obj, base_point):
    for idx, axis in enumerate(('x', 'y', 'z')):
        fcurve = point.driver_add('co', idx)
        driver = fcurve.driver
        driver.type = 'SCRIPTED'
        var = driver.variables.new()
        var.name = 'loc'
        var.targets[0].id = target_obj
        var.targets[0].data_path = f"location.{axis}"
        offset = base_point[idx] - target_obj.location[idx]
        driver.expression = f"loc + ({offset:.10f})"


def img2mat_create_callout_line(name, start, end, coll, swatch_obj=None, bevel_depth=0.018):
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new('POLY')
    spline.points.add(1)
    spline.points[0].co = (start[0], start[1], start[2], 1.0)
    spline.points[1].co = (end[0], end[1], end[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    curve.materials.append(img2mat_callout_line_material())
    coll.objects.link(obj)

    if swatch_obj is not None:
        img2mat_driver_point_to_object_location(spline.points[0], swatch_obj, start)

    return obj


def img2mat_create_callout_label(text, center_x, y, coll, max_width=1.8):
    txt = bpy.data.curves.new(type="FONT", name="Img2Mat_Callout_Label")
    obj = bpy.data.objects.new("Img2Mat_Callout_Label", txt)
    txt.body = text
    txt.align_x = 'CENTER'
    txt.align_y = 'CENTER'
    txt.size = 1.0
    obj.location = (center_x, y, 0.24)
    obj.scale = (0.16, 0.16, 0.16)
    coll.objects.link(obj)
    fit_label_to_width(obj, max_width=max_width)
    return obj


def img2mat_link_object_to_collection_only(obj, coll):
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    for user_coll in list(obj.users_collection):
        if user_coll != coll:
            user_coll.objects.unlink(obj)


def img2mat_create_callout_image_object(image, coll, width):
    obj = bpy.data.objects.new(f"Img2Mat_Callout_Image_{image.name}", None)
    obj.empty_display_type = 'IMAGE'
    obj.data = image
    obj.empty_display_size = width
    obj.empty_image_offset = (-0.5, -0.5)
    coll.objects.link(obj)
    return obj


def img2mat_callout_item_text(item):
    source_text = f"{item.source_label} {item.source_hex}".strip() if item.source_label else item.source_hex
    return f"{source_text} -> {item.pantone_name} {item.match_hex}".strip()


def img2mat_callout_side_for_uv(u, v):
    dx = u - 0.5
    dy = v - 0.5
    if abs(dx) > abs(dy):
        return 'RIGHT' if dx >= 0 else 'LEFT'
    return 'TOP' if dy >= 0 else 'BOTTOM'


# =============================================================================
# Lock Colors data & UI
# =============================================================================

class IMG2MAT_ColorItem(PropertyGroup):
    name: StringProperty(name="Name", default="")
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.0, 0.0)
    )


class IMG2MAT_PantoneMatchItem(PropertyGroup):
    source_hex: StringProperty(name="Source", default="")
    source_label: StringProperty(name="Source Label", default="")
    pantone_name: StringProperty(name="Pantone", default="")
    library_title: StringProperty(name="Library", default="")
    match_hex: StringProperty(name="Match", default="")
    metric: StringProperty(name="Metric", default="LAB")
    distance: FloatProperty(name="Distance", default=0.0, precision=3)
    sample_u: FloatProperty(name="Sample U", default=-1.0)
    sample_v: FloatProperty(name="Sample V", default=-1.0)
    source_color: FloatVectorProperty(
        name="Source Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )
    match_color: FloatVectorProperty(
        name="Pantone Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )


class IMG2MAT_UL_LockColors(UIList):
    bl_idname = "IMG2MAT_UL_LockColors"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "color", text="")
        row.prop(item, "name", text="", emboss=False)


class IMG2MAT_UL_PantoneMatches(UIList):
    bl_idname = "IMG2MAT_UL_PantoneMatches"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "source_color", text="")
        source_text = f"{item.source_label} {item.source_hex}".strip() if item.source_label else item.source_hex
        row.label(text=source_text)
        row.prop(item, "match_color", text="")
        row.label(text=item.pantone_name)
        row.label(text=f"{item.distance:.2f}")


class IMG2MAT_OT_LockAdd(Operator):
    bl_idname = "img2mat.lock_add"
    bl_label = "Add Lock Color"

    def execute(self, context):
        p = context.scene.img2mat_props
        item = p.lock_colors.add()
        item.name = f"Lock {len(p.lock_colors)}"
        p.lock_index = len(p.lock_colors) - 1
        return {'FINISHED'}


class IMG2MAT_OT_LockRemove(Operator):
    bl_idname = "img2mat.lock_remove"
    bl_label = "Remove Lock Color"

    def execute(self, context):
        p = context.scene.img2mat_props
        if p.lock_colors and 0 <= p.lock_index < len(p.lock_colors):
            p.lock_colors.remove(p.lock_index)
            p.lock_index = min(p.lock_index, len(p.lock_colors) - 1)
        return {'FINISHED'}


# =============================================================================
# Active Image helpers
# =============================================================================

def find_active_image_from_editors() -> Optional[bpy.types.Image]:
    for area in bpy.context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            for space in area.spaces:
                if space.type == 'IMAGE_EDITOR':
                    img = getattr(space, "image", None)
                    if img is not None:
                        return img
    return None


class IMG2MAT_OT_UseActiveImage(Operator):
    bl_idname = "img2mat.use_active_image"
    bl_label = "Use Active Image (Image Editor)"

    def execute(self, context):
        p = context.scene.img2mat_props
        img = find_active_image_from_editors()
        if img is None:
            self.report({'WARNING'}, "No Image Editor image found.")
            return {'CANCELLED'}
        p.image = img
        self.report({'INFO'}, f"Using active image: {img.name}")
        return {'FINISHED'}


# =============================================================================
# Addon Preferences
# =============================================================================

class IMG2MAT_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    library_root_dir: StringProperty(
        name="Library Folder",
        description="Folder where converted ACB JSON libraries will be stored. If blank, Blender's user config img2mat_libraries folder is used.",
        subtype='DIR_PATH',
        default=""
    )

    acb_source_dir: StringProperty(
        name="ACB Source Folder",
        description="Folder containing Adobe Color Book (.acb) files to import",
        subtype='DIR_PATH',
        default=""
    )

    show_library_help: BoolProperty(
        name="Show Help",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.label(text="Img2Mat Library Management")
        col.prop(self, "library_root_dir")
        col.prop(self, "acb_source_dir")

        row = col.row(align=True)
        row.operator("img2mat.import_acb_library", icon="IMPORT")
        row.operator("img2mat.import_acb_folder", icon="FILE_FOLDER")
        row.operator("img2mat.rebuild_library_manifest", icon="FILE_REFRESH")

        root = img2mat_resolve_library_root(context)
        manifest = img2mat_load_manifest(context)
        lib_count = len(manifest.get("libraries", []))
        enabled_count = sum(1 for x in manifest.get("libraries", []) if x.get("enabled", True))

        box = col.box()
        box.label(text=f"Library Folder: {root}")
        box.label(text=f"Installed Libraries: {lib_count}")
        box.label(text=f"Enabled Libraries: {enabled_count}")

        col.prop(self, "show_library_help", emboss=False, icon="INFO")
        if self.show_library_help:
            help_box = col.box()
            help_box.label(text="This addon does not ship with proprietary color libraries.")
            help_box.label(text="Use Import ACB to convert your own licensed Adobe Color Book files.")
            help_box.label(text="Converted libraries are stored as JSON and can be reused across projects.")
            help_box.label(text="If Library Folder is blank, Blender's user config img2mat_libraries folder is used.")

        if lib_count > 0:
            list_box = col.box()
            list_box.label(text="Installed Libraries")
            for lib in manifest.get("libraries", []):
                row = list_box.row(align=True)
                state = "ON" if lib.get("enabled", True) else "OFF"
                row.label(text=f"{lib.get('title', 'Untitled')} [{lib.get('model_name', 'Unknown')}]")
                row.label(text=f"{lib.get('color_count', 0)} colors")
                row.label(text=state)


# =============================================================================
# UI Props
# =============================================================================

class IMG2MAT_Props(PropertyGroup):
    options_expanded: BoolProperty(
        name="Options",
        description="Show advanced options for color extraction, naming, and output",
        default=False
    )

    library_expanded: BoolProperty(
        name="Library",
        description="Show imported ACB library controls",
        default=False
    )

    output_expanded: BoolProperty(
        name="Output",
        description="Show material, swatch, palette, and Pantone output options",
        default=False
    )

    pantone_expanded: BoolProperty(
        name="Pantone",
        description="Show Pantone matching controls and results",
        default=True
    )

    pantone_library_filter: EnumProperty(
        name="Match Library",
        description="Pantone/color library to search when matching colors",
        items=img2mat_pantone_library_items,
        default=0
    )

    pantone_match_metric: EnumProperty(
        name="Match Method",
        description="Distance method used when finding the nearest Pantone color",
        items=[
            ('LAB', "Perceptual Lab", "Use perceptual Lab distance for nearest visible match"),
            ('RGB', "RGB", "Use raw sRGB distance"),
        ],
        default='LAB'
    )

    pantone_sample_color: FloatVectorProperty(
        name="Sample Color",
        description="Color to match to the nearest Pantone. Use Blender's color picker eyedropper to sample from the image.",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )

    pantone_results: CollectionProperty(type=IMG2MAT_PantoneMatchItem)
    pantone_result_index: IntProperty(name="Active Pantone Match", default=0)
    pantone_sample_results: CollectionProperty(type=IMG2MAT_PantoneMatchItem)
    pantone_sample_result_index: IntProperty(name="Active Single Color Match", default=0)

    pantone_create_swatches: BoolProperty(
        name="Create Pantone Swatches",
        default=True,
        description="Create a matched Pantone swatch collection in the scene"
    )

    pantone_create_text_block: BoolProperty(
        name="Create Text List",
        default=True,
        description="Create a Blender text block with the current Pantone list"
    )

    pantone_text_name: StringProperty(
        name="Text Block",
        default="Img2Mat Pantone Matches",
        description="Name of the Blender text block used for Pantone results"
    )

    pantone_last_summary: StringProperty(
        name="Pantone Summary",
        default=""
    )

    pantone_sample_last_summary: StringProperty(
        name="Single Color Summary",
        default=""
    )

    method: EnumProperty(
        name="Color Sampling Method",
        description="How colors are extracted from the image",
        items=[
            ('NOTABLE', "Notable Colors", "Balance broad image colors with visually distinct accent colors"),
            ('KMEANS_RGB', "K-Means (RGB, Comfy)", "Cluster RGB pixels (Comfy-like)"),
            ('POSTER', "Poster Unique (Top-N)", "Choose most frequent exact sRGB colors"),
        ],
        default='NOTABLE'
    )

    palette_size: IntProperty(
        name="Palette Size",
        min=2,
        max=64,
        default=8,
        description="Number of colors to extract for the palette"
    )

    image: PointerProperty(type=bpy.types.Image, name="Image", description="Source image")

    sync_active_image: BoolProperty(
        name="Sync with Image Viewer",
        description="When enabled, Generate Materials will always use the image shown in any open Image Editor",
        default=True
    )

    pixel_colorspace: EnumProperty(
        name="Color Space",
        description="Interpretation of the image pixel values when sampling",
        items=[
            ('AS_IS', "As-Is (sRGB)", "Treat image.pixels as sRGB (best for PNG/JPEG)"),
            ('LIN_TO_SRGB', "Linear to sRGB", "Convert from linear to sRGB"),
        ],
        default='AS_IS'
    )

    sampling: EnumProperty(
        name="Sampling",
        description="Strategy for picking which pixels to analyze",
        items=[
            ('STRIDE', "All Pixels (stride)", "Use every Nth pixel across the whole image"),
            ('GRID', "Uniform Grid", "Sample one pixel per cell to de-bias large regions"),
        ],
        default='GRID'
    )

    sample_stride: IntProperty(
        name="Pixel Stride",
        min=1,
        max=64,
        default=1,
        description="Use every Nth pixel when 'All Pixels (stride)' is selected"
    )

    grid_cells: IntProperty(
        name="Grid Size",
        min=8,
        max=256,
        default=64,
        description="Number of cells per dimension when using Uniform Grid sampling"
    )

    alpha_min: FloatProperty(
        name="Min Alpha",
        min=0.0,
        max=1.0,
        default=0.05,
        description="Ignore pixels with alpha below this value"
    )

    poster_min_percent: FloatProperty(
        name="Min % (Poster)",
        min=0.0,
        max=0.05,
        default=0.002,
        description="Minimum frequency threshold for Poster Unique method"
    )

    accuracy: IntProperty(
        name="Accuracy",
        min=1,
        max=100,
        default=80,
        description="Higher = more K-Means iterations (more accurate but slower)"
    )

    seed: IntProperty(
        name="Seed",
        min=0,
        max=2**31 - 1,
        default=0,
        description="Random seed for K-Means initialization and Notable Colors variation"
    )

    lock_colors: CollectionProperty(type=IMG2MAT_ColorItem)
    lock_index: IntProperty(name="Active Lock", default=0)

    use_lock_names: BoolProperty(
        name="Use Lock Names",
        default=True,
        description="If a palette color exactly matches a lock color, use the lock's name"
    )

    lock_snap_tol: IntProperty(
        name="Lock Snap Tolerance (8-bit L1)",
        min=0,
        max=30,
        default=6,
        description="Snap extracted colors to nearby lock colors within this 8-bit L1 distance"
    )

    naming_mode: EnumProperty(
        name="Naming",
        description="How to name generated materials",
        items=[
            ('CSS', "CSS", "Nearest CSS/HTML color"),
            ('CSS_GUARD', "CSS + Hue Guard", "Use CSS unless it clashes with hue/tone or is far"),
            ('HUE', "Hue Descriptive", "Descriptive names from hue + tone"),
        ],
        default='CSS_GUARD'
    )

    subsurface: FloatProperty(
        name="Subsurface",
        min=0.0,
        max=1.0,
        default=0.0,
        description="Set Subsurface/SSS on generated Principled BSDF materials"
    )

    generate_swatches: BoolProperty(
        name="Generate Swatches",
        default=True,
        description="Create a grid of colored planes for quick viewing"
    )

    generate_labels: BoolProperty(
        name="Generate Labels",
        default=True,
        description="Add text labels beneath swatches (auto-sized to fit)"
    )

    mark_as_assets: BoolProperty(
        name="Mark Materials as Assets",
        default=True,
        description="Mark materials as Assets and tag them"
    )

    asset_tag: StringProperty(
        name="Asset Tag",
        default="palette",
        description="Tag name to add to generated Assets"
    )

    create_palette: BoolProperty(
        name="Create Blender Palette",
        default=True,
        description="Create a Blender Palette resource with these colors"
    )

    palette_name: StringProperty(
        name="Palette Name",
        default="Img2Mat Palette",
        description="Name of the Blender Palette asset to create"
    )


# =============================================================================
# helpers for locks/snapping
# =============================================================================

def get_locked_colors_srgb(p):
    locks_srgb = []
    for item in p.lock_colors:
        col_lin = tuple(item.color)
        col_srgb = tuple_linear_to_srgb(col_lin)
        locks_srgb.append(tuple(max(0.0, min(1.0, v)) for v in col_srgb))
    return locks_srgb


def snap_to_locked_colors(colors, locks, tol_l1_8bit):
    if not locks or tol_l1_8bit <= 0:
        return colors

    locks8 = [tuple(max(0, min(255, round(c * 255))) for c in lock) for lock in locks]
    snapped = []

    for rgb in colors:
        r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
        replaced = False
        for lr, lg, lb in locks8:
            d = abs(r8 - lr) + abs(g8 - lg) + abs(b8 - lb)
            if d <= tol_l1_8bit:
                snapped.append((lr / 255.0, lg / 255.0, lb / 255.0))
                replaced = True
                break
        if not replaced:
            snapped.append(rgb)

    return snapped


def img2mat_get_lock_name_map(p) -> Dict[Tuple[int, int, int], str]:
    lock_name_map = {}
    for item in getattr(p, "lock_colors", []):
        nm = item.name.strip()
        if not nm:
            continue
        srgb = tuple_linear_to_srgb(tuple(item.color))
        r8 = max(0, min(255, round(srgb[0] * 255)))
        g8 = max(0, min(255, round(srgb[1] * 255)))
        b8 = max(0, min(255, round(srgb[2] * 255)))
        lock_name_map[(r8, g8, b8)] = nm
    return lock_name_map


def img2mat_find_lock_name_for_srgb(p, rgb, tol_l1_8bit=0) -> str:
    lock_name_map = img2mat_get_lock_name_map(p)
    if not lock_name_map:
        return ""

    r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
    if (r8, g8, b8) in lock_name_map:
        return lock_name_map[(r8, g8, b8)]

    best_name = ""
    best_d = None
    tol = max(0, int(tol_l1_8bit))
    for (lr, lg, lb), name in lock_name_map.items():
        d = abs(r8 - lr) + abs(g8 - lg) + abs(b8 - lb)
        if d <= tol and (best_d is None or d < best_d):
            best_d = d
            best_name = name
    return best_name


def img2mat_get_image_for_props(p):
    image = p.image
    if p.sync_active_image or image is None:
        image = find_active_image_from_editors() or image
    if image is not None:
        p.image = image
    return image


def img2mat_extract_palette_from_image(p, image):
    as_is = (p.pixel_colorspace == 'AS_IS')
    if p.sampling == 'GRID':
        samples = read_pixels_uniform_grid(image, cells=p.grid_cells, alpha_min=p.alpha_min, as_is=as_is)
    else:
        samples = (
            read_pixels_as_is(image, stride=p.sample_stride, alpha_min=p.alpha_min)
            if as_is else
            read_pixels_linear_to_srgb(image, stride=p.sample_stride, alpha_min=p.alpha_min)
        )

    if not samples:
        raise ValueError("No samples; check alpha/sampling settings.")

    locks_srgb = get_locked_colors_srgb(p)
    k = p.palette_size
    if locks_srgb and len(locks_srgb) > k:
        locks_srgb = locks_srgb[:k]

    if p.method == 'NOTABLE':
        palette = notable_colors_with_locks(samples, n=k, locked=locks_srgb, seed=p.seed)
    elif p.method == 'KMEANS_RGB':
        iters = int(512 * (p.accuracy / 100))
        palette = kmeans_rgb_with_locks(samples, k=k, iters=iters, seed=p.seed, locked=locks_srgb)
    else:
        palette = unique_top_n_with_locks(samples, n=k, min_pct=p.poster_min_percent, locked=locks_srgb)

    if not palette:
        raise ValueError("Palette extraction produced 0 colors.")

    palette = snap_to_locked_colors(palette, locks_srgb, p.lock_snap_tol)
    return palette, len(locks_srgb)


def img2mat_add_pantone_result_to_collection(collection, match: Dict[str, object]):
    item = collection.add()
    item.source_hex = match.get("source_hex", "")
    item.source_label = match.get("source_label", "")
    item.pantone_name = match.get("pantone_name", "")
    item.library_title = match.get("library_title", "")
    item.match_hex = match.get("match_hex", "")
    item.metric = match.get("metric", "LAB")
    item.distance = float(match.get("distance", 0.0))
    item.sample_u = float(match.get("sample_u", -1.0))
    item.sample_v = float(match.get("sample_v", -1.0))
    item.source_color = tuple_srgb_to_linear(match.get("source_rgb", (1.0, 1.0, 1.0)))
    item.match_color = tuple_srgb_to_linear(match.get("match_rgb", (1.0, 1.0, 1.0)))
    return item


def img2mat_add_pantone_result(p, match: Dict[str, object]):
    return img2mat_add_pantone_result_to_collection(p.pantone_results, match)


def img2mat_add_pantone_sample_result(p, match: Dict[str, object]):
    return img2mat_add_pantone_result_to_collection(p.pantone_sample_results, match)


def img2mat_create_pantone_swatches_from_results(results):
    coll = ensure_collection("PantoneMatches")
    clear_collection_objects(coll)

    grid_x = grid_y = 0
    max_cols = 6

    for item in results:
        match_rgb = tuple_linear_to_srgb(tuple(item.match_color))
        source_text = f"{item.source_label} {item.source_hex}".strip() if item.source_label else item.source_hex
        mat_name = f"{source_text} -> {item.pantone_name} {item.match_hex}".strip()
        mat = create_material_from_srgb(mat_name or "Pantone Match", match_rgb)

        sw = create_swatch_plane(grid_x * 2.2, -grid_y * 2.1, size=1.6)
        sw.data.materials.append(mat)
        coll.objects.link(sw)

        label_text = mat_name
        lbl = create_label(label_text, grid_x * 2.2, -grid_y * 2.1)
        coll.objects.link(lbl)
        fit_label_to_width(lbl, max_width=1.6)

        grid_x += 1
        if grid_x >= max_cols:
            grid_x = 0
            grid_y += 1


def img2mat_finalize_pantone_results(context, p):
    result_text = img2mat_format_combined_pantone_results(p)
    if p.pantone_create_text_block and result_text:
        img2mat_write_text_block(p.pantone_text_name, result_text)
    if p.pantone_create_swatches and p.pantone_results:
        img2mat_create_pantone_swatches_from_results(p.pantone_results)
    context.window_manager.clipboard = result_text
    p.pantone_last_summary = f"{len(p.pantone_results)} Pantone match(es). Copied list to clipboard."


def img2mat_finalize_pantone_sample_result(context, p):
    sample_text = img2mat_format_pantone_results(p.pantone_sample_results)
    result_text = img2mat_format_combined_pantone_results(p)
    if p.pantone_create_text_block and result_text:
        img2mat_write_text_block(p.pantone_text_name, result_text)
    context.window_manager.clipboard = result_text or sample_text
    p.pantone_sample_last_summary = "Single color match copied to clipboard."


# =============================================================================
# Generate Operator
# =============================================================================

class IMG2MAT_OT_Generate(Operator):
    bl_idname = "img2mat.generate_materials"
    bl_label = "Generate Materials"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.img2mat_props

        image = img2mat_get_image_for_props(p)
        if image is None:
            self.report({"ERROR"}, "No image selected (and none visible in Image Editor).")
            return {"CANCELLED"}

        try:
            palette, lock_count = img2mat_extract_palette_from_image(p, image)
        except ValueError as ex:
            self.report({"WARNING"}, str(ex))
            return {"CANCELLED"}

        lock_name_map = img2mat_get_lock_name_map(p) if p.use_lock_names else {}

        sw_coll = ensure_collection("HueSwatches") if p.generate_swatches else None
        if sw_coll:
            clear_collection_objects(sw_coll)

        pal = ensure_palette(p.palette_name) if p.create_palette else None

        grid_x = grid_y = 0
        max_cols = 10

        for rgb in palette:
            r8, g8, b8 = [max(0, min(255, round(v * 255))) for v in rgb]
            hexcode = f"#{r8:02X}{g8:02X}{b8:02X}"

            if (r8, g8, b8) in lock_name_map:
                disp_name = lock_name_map[(r8, g8, b8)]
            else:
                if p.naming_mode == 'CSS':
                    disp_name, _, _ = nearest_css_name_distance(r8, g8, b8)
                elif p.naming_mode == 'HUE':
                    disp_name = descriptive_name_from_rgb(rgb)
                else:
                    disp_name = css_hue_guard_name_from_rgb(rgb)

            mat_name = f"{disp_name} {hexcode}"
            mat = create_material_from_srgb(
                mat_name,
                rgb,
                subsurf=p.subsurface,
                mark_asset=p.mark_as_assets,
                asset_tag=p.asset_tag
            )

            if sw_coll:
                sw = create_swatch_plane(grid_x * 1.8, -grid_y * 1.8, size=1.6)
                if sw.data.materials:
                    sw.data.materials[0] = mat
                else:
                    sw.data.materials.append(mat)
                sw_coll.objects.link(sw)

                if p.generate_labels:
                    lbl = create_label(mat_name, grid_x * 1.8, -grid_y * 1.8)
                    sw_coll.objects.link(lbl)
                    fit_label_to_width(lbl, max_width=1.6)

                grid_x += 1
                if grid_x >= max_cols:
                    grid_x = 0
                    grid_y += 1

            if pal:
                pc = pal.colors.new()
                pc.color = (rgb[0], rgb[1], rgb[2])

        if pal and hasattr(pal, "asset_mark"):
            pal.asset_mark()
            if p.asset_tag:
                try:
                    pal.asset_data.tags.new(p.asset_tag)
                except Exception:
                    pass

        self.report({"INFO"}, f"Generated {len(palette)} materials (locks={lock_count}).")
        return {"FINISHED"}


# =============================================================================
# Library Operators
# =============================================================================

class IMG2MAT_OT_ImportACBLibrary(Operator):
    bl_idname = "img2mat.import_acb_library"
    bl_label = "Import ACB Library"
    bl_description = "Convert a user-supplied Adobe Color Book (.acb) into a JSON library"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.acb", options={'HIDDEN'})

    def execute(self, context):
        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "Please choose a valid .acb file.")
            return {'CANCELLED'}

        try:
            library_data = img2mat_parse_acb_file(self.filepath)
            json_path = img2mat_write_library_json(library_data, context)
            img2mat_upsert_manifest_entry(library_data, json_path, context)

            self.report(
                {'INFO'},
                f"Imported '{library_data.get('title') or os.path.basename(self.filepath)}' "
                f"({library_data.get('color_count', 0)} colors) -> {os.path.basename(json_path)}"
            )
            return {'FINISHED'}

        except Exception as ex:
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to import ACB: {ex}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class IMG2MAT_OT_ImportACBFolder(Operator):
    bl_idname = "img2mat.import_acb_folder"
    bl_label = "Import ACB Folder"
    bl_description = "Convert every Adobe Color Book (.acb) in a folder into reusable JSON libraries"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(subtype='DIR_PATH')
    filter_glob: StringProperty(default="*.acb", options={'HIDDEN'})

    def execute(self, context):
        prefs = img2mat_get_addon_prefs(context)
        folder = self.directory.strip()
        if not folder and prefs and prefs.acb_source_dir.strip():
            folder = prefs.acb_source_dir.strip()
        if not folder:
            folder = img2mat_default_acb_source_dir()

        folder = bpy.path.abspath(folder) if folder else ""
        if not folder or not os.path.isdir(folder):
            self.report({'ERROR'}, "Please choose a folder containing .acb files.")
            return {'CANCELLED'}

        if prefs:
            prefs.acb_source_dir = folder

        acb_files = sorted(
            os.path.join(folder, fn)
            for fn in os.listdir(folder)
            if fn.lower().endswith(".acb")
        )
        if not acb_files:
            self.report({'WARNING'}, "No .acb files found in the selected folder.")
            return {'CANCELLED'}

        imported = 0
        failed = []
        for filepath in acb_files:
            try:
                library_data = img2mat_parse_acb_file(filepath)
                json_path = img2mat_write_library_json(library_data, context)
                img2mat_upsert_manifest_entry(library_data, json_path, context)
                imported += 1
            except Exception as ex:
                failed.append(f"{os.path.basename(filepath)}: {ex}")

        if failed:
            print("Img2Mat ACB folder import failures:")
            for msg in failed:
                print(msg)

        if imported == 0:
            self.report({'ERROR'}, f"Failed to import {len(failed)} ACB file(s). See console.")
            return {'CANCELLED'}

        suffix = f", {len(failed)} failed" if failed else ""
        self.report({'INFO'}, f"Imported {imported} ACB librar{'y' if imported == 1 else 'ies'}{suffix}.")
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = img2mat_get_addon_prefs(context)
        default_dir = ""
        if prefs and prefs.acb_source_dir.strip():
            default_dir = prefs.acb_source_dir.strip()
        if not default_dir:
            default_dir = img2mat_default_acb_source_dir()
        if default_dir:
            self.directory = default_dir
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class IMG2MAT_OT_RebuildLibraryManifest(Operator):
    bl_idname = "img2mat.rebuild_library_manifest"
    bl_label = "Rebuild Library Index"
    bl_description = "Scan the library folder and rebuild the JSON library manifest"

    def execute(self, context):
        manifest = img2mat_rebuild_manifest_from_disk(context)
        self.report({'INFO'}, f"Rebuilt library index: {len(manifest.get('libraries', []))} libraries found.")
        return {'FINISHED'}


class IMG2MAT_OT_ToggleLibraryEnabled(Operator):
    bl_idname = "img2mat.toggle_library_enabled"
    bl_label = "Toggle Library Enabled"

    json_filename: StringProperty()

    def execute(self, context):
        manifest = img2mat_load_manifest(context)
        libs = manifest.get("libraries", [])
        found = False

        for lib in libs:
            if lib.get("json_filename", "") == self.json_filename:
                lib["enabled"] = not lib.get("enabled", True)
                found = True
                break

        if found:
            img2mat_save_manifest(manifest, context)
            self.report({'INFO'}, f"Toggled library '{self.json_filename}'.")
            return {'FINISHED'}

        self.report({'WARNING'}, f"Library '{self.json_filename}' not found in manifest.")
        return {'CANCELLED'}


# =============================================================================
# Pantone Operators
# =============================================================================

class IMG2MAT_OT_MatchPantonePalette(Operator):
    bl_idname = "img2mat.match_pantone_palette"
    bl_label = "Get PMS Colors"
    bl_description = "Extract the image palette and match each color to the nearest enabled Pantone library color"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.img2mat_props

        image = img2mat_get_image_for_props(p)
        if image is None:
            self.report({"ERROR"}, "No image selected (and none visible in Image Editor).")
            return {"CANCELLED"}

        libraries = img2mat_load_libraries_for_selector(context, p.pantone_library_filter)
        if not libraries:
            self.report({"ERROR"}, "No enabled Pantone library is available for the current selection.")
            return {"CANCELLED"}

        try:
            palette, _lock_count = img2mat_extract_palette_from_image(p, image)
        except ValueError as ex:
            self.report({"WARNING"}, str(ex))
            return {"CANCELLED"}

        sample_points = img2mat_read_samples_with_coords(image, p)
        p.pantone_results.clear()
        for rgb in palette:
            match = img2mat_find_nearest_library_color(rgb, libraries, metric=p.pantone_match_metric)
            if match:
                source_label = img2mat_find_lock_name_for_srgb(p, rgb, tol_l1_8bit=0)
                if source_label:
                    match["source_label"] = source_label
                sample_u, sample_v = img2mat_find_sample_uv_for_srgb(sample_points, rgb)
                match["sample_u"] = sample_u
                match["sample_v"] = sample_v
                img2mat_add_pantone_result(p, match)

        if not p.pantone_results:
            self.report({"WARNING"}, "No Pantone matches were produced.")
            return {"CANCELLED"}

        img2mat_finalize_pantone_results(context, p)
        self.report({"INFO"}, p.pantone_last_summary)
        return {"FINISHED"}


class IMG2MAT_OT_MatchPantoneSample(Operator):
    bl_idname = "img2mat.match_pantone_sample"
    bl_label = "Match Sample Color"
    bl_description = "Match the sample color to the nearest enabled Pantone library color"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.img2mat_props
        libraries = img2mat_load_libraries_for_selector(context, p.pantone_library_filter)
        if not libraries:
            self.report({"ERROR"}, "No enabled Pantone library is available for the current selection.")
            return {"CANCELLED"}

        sample_srgb = tuple_linear_to_srgb(tuple(p.pantone_sample_color))
        sample_srgb = tuple(max(0.0, min(1.0, v)) for v in sample_srgb)
        match = img2mat_find_nearest_library_color(sample_srgb, libraries, metric=p.pantone_match_metric)
        if not match:
            self.report({"WARNING"}, "No Pantone match was produced.")
            return {"CANCELLED"}

        image = img2mat_get_image_for_props(p)
        if image is not None:
            sample_points = img2mat_read_samples_with_coords(image, p)
            sample_u, sample_v = img2mat_find_sample_uv_for_srgb(sample_points, sample_srgb)
            match["sample_u"] = sample_u
            match["sample_v"] = sample_v

        source_label = img2mat_find_lock_name_for_srgb(p, sample_srgb, tol_l1_8bit=max(1, p.lock_snap_tol))
        if source_label:
            match["source_label"] = source_label

        p.pantone_sample_results.clear()
        img2mat_add_pantone_sample_result(p, match)
        img2mat_finalize_pantone_sample_result(context, p)
        self.report({"INFO"}, img2mat_format_pantone_match(match))
        return {"FINISHED"}


class IMG2MAT_OT_CopyPantoneResults(Operator):
    bl_idname = "img2mat.copy_pantone_results"
    bl_label = "Copy Pantone List"
    bl_description = "Copy the current Pantone result list to the clipboard"

    def execute(self, context):
        p = context.scene.img2mat_props
        result_text = img2mat_format_combined_pantone_results(p)
        if not result_text:
            self.report({"WARNING"}, "No Pantone results to copy.")
            return {"CANCELLED"}
        context.window_manager.clipboard = result_text
        if p.pantone_create_text_block:
            img2mat_write_text_block(p.pantone_text_name, result_text)
        total = len(p.pantone_results) + len(p.pantone_sample_results)
        p.pantone_last_summary = f"Copied {total} Pantone match(es)."
        self.report({"INFO"}, p.pantone_last_summary)
        return {"FINISHED"}


class IMG2MAT_OT_CreateCallouts(Operator):
    bl_idname = "img2mat.create_callouts"
    bl_label = "Create Callouts"
    bl_description = "Place the active image in the scene and draw swatch callout lines to approximate sampled locations"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.img2mat_props
        image = img2mat_get_image_for_props(p)
        if image is None:
            self.report({"ERROR"}, "No image selected (and none visible in Image Editor).")
            return {"CANCELLED"}

        results = list(p.pantone_results) + list(p.pantone_sample_results)
        if not results:
            self.report({"WARNING"}, "No Pantone results to call out. Run Get PMS Colors first.")
            return {"CANCELLED"}

        sample_points = img2mat_read_samples_with_coords(image, p)
        for item in results:
            if item.sample_u < 0.0 or item.sample_v < 0.0:
                source_rgb = tuple_linear_to_srgb(tuple(item.source_color))
                item.sample_u, item.sample_v = img2mat_find_sample_uv_for_srgb(sample_points, source_rgb)

        coll = bpy.data.collections.get("Img2Mat_Callouts")
        if coll is not None:
            clear_collection_objects(coll)
        else:
            coll = bpy.data.collections.new("Img2Mat_Callouts")
            context.scene.collection.children.link(coll)

        w_px, h_px = image.size
        image_width = 8.0
        image_height = image_width * (h_px / max(1, w_px))
        img2mat_create_callout_image_object(image, coll, image_width)

        left = -image_width / 2.0
        right = image_width / 2.0
        bottom = -image_height / 2.0
        top = image_height / 2.0
        swatch_size = 0.72
        margin = 0.70

        groups = {"LEFT": [], "RIGHT": [], "TOP": [], "BOTTOM": []}
        for item in results:
            u = item.sample_u if 0.0 <= item.sample_u <= 1.0 else 0.5
            v = item.sample_v if 0.0 <= item.sample_v <= 1.0 else 0.5
            groups[img2mat_callout_side_for_uv(u, v)].append(item)

        for side, items in groups.items():
            count = len(items)
            for idx, item in enumerate(items):
                u = item.sample_u if 0.0 <= item.sample_u <= 1.0 else 0.5
                v = item.sample_v if 0.0 <= item.sample_v <= 1.0 else 0.5
                target = ((u - 0.5) * image_width, (v - 0.5) * image_height, 0.08)
                t = (idx + 1) / (count + 1) if count else 0.5

                if side == "LEFT":
                    sx = left - margin - swatch_size
                    sy = top - t * image_height - swatch_size / 2.0
                elif side == "RIGHT":
                    sx = right + margin
                    sy = top - t * image_height - swatch_size / 2.0
                elif side == "TOP":
                    sx = left + t * image_width - swatch_size / 2.0
                    sy = top + margin
                else:
                    sx = left + t * image_width - swatch_size / 2.0
                    sy = bottom - margin - swatch_size

                match_rgb = tuple_linear_to_srgb(tuple(item.match_color))
                mat = create_material_from_srgb(img2mat_callout_item_text(item) or "Img2Mat Callout", match_rgb)
                sw_center_x = sx + swatch_size / 2.0
                sw_center_y = sy + swatch_size / 2.0
                sw = img2mat_create_centered_swatch_plane("Img2Mat_Callout_Swatch", sw_center_x, sw_center_y, size=swatch_size)
                sw.data.materials.append(mat)
                coll.objects.link(sw)

                label_y = sy - 0.18 if side != "BOTTOM" else sy - 0.20
                label = img2mat_create_callout_label(img2mat_callout_item_text(item), sw_center_x, label_y, coll, max_width=2.25)
                img2mat_parent_keep_world(label, sw)
                start = (sw_center_x, sw_center_y, 0.12)
                img2mat_create_callout_line("Img2Mat_Callout_Line", start, target, coll, swatch_obj=sw)

        self.report({"INFO"}, f"Created {len(results)} callout(s).")
        return {"FINISHED"}


class IMG2MAT_OT_ClearSwatches(Operator):
    bl_idname = "img2mat.clear_swatches"
    bl_label = "Clear Swatches"
    bl_description = "Delete generated Hue Swatches and Pantone Matches, and clear Pantone result lists"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.img2mat_props
        cleared_collections = 0
        for coll_name in ("HueSwatches", "PantoneMatches", "Img2Mat_Callouts"):
            coll = bpy.data.collections.get(coll_name)
            if coll is not None:
                clear_collection_objects(coll)
                bpy.data.collections.remove(coll)
                cleared_collections += 1

        p.pantone_results.clear()
        p.pantone_sample_results.clear()
        p.pantone_last_summary = ""
        p.pantone_sample_last_summary = ""
        self.report({"INFO"}, f"Cleared swatches and Pantone lists ({cleared_collections} collection(s)).")
        return {"FINISHED"}


# =============================================================================
# Panel
# =============================================================================

class IMG2MAT_PT_Panel(Panel):
    bl_label = "Image to Material"
    bl_idname = "IMG2MAT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Img2Mat"

    def draw(self, context):
        p = context.scene.img2mat_props
        prefs = img2mat_get_addon_prefs(context)
        col = self.layout.column(align=True)

        # --- Top: Image + Sync
        row = col.row(align=True)
        row.prop(p, "image", text="Image")
        row.operator("img2mat.use_active_image", text="", icon="IMAGE_DATA")
        col.prop(p, "sync_active_image")

        col.separator()

        # --- Palette Size
        col.prop(p, "palette_size")

        col.separator()

        # --- Lock Colors
        col.label(text="Lock Colors")
        row = col.row()
        row.template_list("IMG2MAT_UL_LockColors", "", p, "lock_colors", p, "lock_index", rows=3)
        sub = col.row(align=True)
        sub.operator("img2mat.lock_add", icon="ADD", text="Add Lock Color")
        sub.operator("img2mat.lock_remove", icon="REMOVE", text="Remove Lock Color")
        col.prop(p, "use_lock_names")

        col.separator()

        # --- Pantone single color matching and result review
        box_match = col.box()
        box_match.label(text="Pantone Match")
        row = box_match.row(align=True)
        row.prop(p, "pantone_sample_color", text="")
        row.operator("img2mat.match_pantone_sample", text="Match")

        if p.pantone_sample_results:
            box_match.label(text="Single Color Result")
            box_match.template_list(
                "IMG2MAT_UL_PantoneMatches",
                "single_sample",
                p,
                "pantone_sample_results",
                p,
                "pantone_sample_result_index",
                rows=1
            )
        elif p.pantone_sample_last_summary:
            box_match.label(text=p.pantone_sample_last_summary)

        box_match.separator()
        row = box_match.row(align=True)
        row.label(text="PMS Color Results")
        row.operator("img2mat.copy_pantone_results", text="", icon="COPYDOWN")

        if p.pantone_last_summary:
            box_match.label(text=p.pantone_last_summary)

        if p.pantone_results:
            box_match.template_list(
                "IMG2MAT_UL_PantoneMatches",
                "",
                p,
                "pantone_results",
                p,
                "pantone_result_index",
                rows=6
            )
        else:
            box_match.label(text="No PMS colors yet.")

        col.separator()

        # --- Output
        box_out = col.box()
        header = box_out.row(align=True)
        icon = "TRIA_DOWN" if p.output_expanded else "TRIA_RIGHT"
        header.prop(p, "output_expanded", text="Output", emboss=False, icon=icon)

        if p.output_expanded:
            box_out.prop(p, "generate_swatches", text="Generate Swatches")
            box_out.prop(p, "generate_labels", text="Generate Labels")
            box_out.prop(p, "mark_as_assets", text="Mark Materials as Assets")
            box_out.prop(p, "create_palette", text="Create Blender Palette")

            box_out.separator()
            box_out.label(text="Pantone")
            box_out.prop(p, "pantone_create_swatches")
            box_out.prop(p, "pantone_create_text_block")

        col.separator()

        # --- Library section
        box_lib = col.box()
        header = box_lib.row(align=True)
        icon = "TRIA_DOWN" if p.library_expanded else "TRIA_RIGHT"
        header.prop(p, "library_expanded", text="Library", emboss=False, icon=icon)

        if p.library_expanded:
            root = img2mat_resolve_library_root(context)
            manifest = img2mat_load_manifest(context)
            libs = manifest.get("libraries", [])

            box_lib.label(text=f"Folder: {root}")
            box_lib.label(text=f"Installed: {len(libs)} | Enabled: {sum(1 for x in libs if x.get('enabled', True))}")

            row = box_lib.row(align=True)
            row.operator("img2mat.import_acb_library", icon="IMPORT")
            row.operator("img2mat.import_acb_folder", icon="FILE_FOLDER")
            row.operator("img2mat.rebuild_library_manifest", icon="FILE_REFRESH")

            if prefs and prefs.library_root_dir:
                box_lib.prop(prefs, "library_root_dir", text="Storage")
            if prefs:
                box_lib.prop(prefs, "acb_source_dir", text="ACB Folder")

            if libs:
                list_box = box_lib.box()
                list_box.label(text="Installed Libraries")
                for lib in libs:
                    row = list_box.row(align=True)
                    enabled = lib.get("enabled", True)
                    op = row.operator(
                        "img2mat.toggle_library_enabled",
                        text="",
                        icon='CHECKBOX_HLT' if enabled else 'CHECKBOX_DEHLT',
                        emboss=True
                    )
                    op.json_filename = lib.get("json_filename", "")
                    row.label(text=lib.get("title", "Untitled"))
                    row.label(text=lib.get("model_name", "Unknown"))
                    row.label(text=str(lib.get("color_count", 0)))
            else:
                box_lib.label(text="No imported libraries yet.")
                box_lib.label(text="Use Import ACB to convert your own Adobe Color Book files.")

        col.separator()

        # --- Options
        box = col.box()
        header = box.row(align=True)
        icon = "TRIA_DOWN" if p.options_expanded else "TRIA_RIGHT"
        header.prop(p, "options_expanded", text="Options", emboss=False, icon=icon)

        if p.options_expanded:
            box.separator()
            box.label(text="Color Sampling Method")
            box.prop(p, "method", text="")

            box.separator()
            box.label(text="Pantone")
            box.prop(p, "pantone_library_filter")
            box.prop(p, "pantone_match_metric", text="Match Method")
            row = box.row()
            row.enabled = p.pantone_create_text_block
            row.prop(p, "pantone_text_name")

            box.separator()
            box.label(text="Color Space")
            box.prop(p, "pixel_colorspace", text="")

            box.separator()
            box.label(text="Sampling")
            box.prop(p, "sampling", text="")
            if p.sampling == 'GRID':
                box.prop(p, "grid_cells")
            else:
                box.prop(p, "sample_stride")
            box.prop(p, "alpha_min")

            if p.method == 'NOTABLE':
                box.separator()
                box.label(text="Notable Colors")
                box.prop(p, "seed")
            elif p.method == 'KMEANS_RGB':
                box.separator()
                box.label(text="Comfy K-Means (RGB)")
                box.prop(p, "accuracy")
                box.prop(p, "seed")
            else:
                box.separator()
                box.label(text="Poster Unique")
                box.prop(p, "poster_min_percent")

            box.separator()
            box.label(text="Lock Snapping")
            box.prop(p, "lock_snap_tol")

            box.separator()
            box.label(text="Naming")
            box.prop(p, "naming_mode", text="")

            box.separator()
            box.label(text="Subsurface")
            box.prop(p, "subsurface")

            box.separator()
            box.label(text="Assets & Palette")
            box.prop(p, "asset_tag")
            box.prop(p, "palette_name")

        col.separator()

        # --- Bottom: primary actions
        row = col.row(align=True)
        row.operator(IMG2MAT_OT_Generate.bl_idname, text="Generate Materials", icon="COLOR")
        row.operator("img2mat.match_pantone_palette", text="Get PMS Colors", icon="COLOR")

        col.separator()
        col.operator("img2mat.create_callouts", icon="IMAGE_DATA")

        col.separator()
        col.operator("img2mat.clear_swatches", icon="TRASH")


# =============================================================================
# Registration
# =============================================================================

classes = (
    IMG2MAT_ColorItem,
    IMG2MAT_PantoneMatchItem,
    IMG2MAT_UL_LockColors,
    IMG2MAT_UL_PantoneMatches,
    IMG2MAT_OT_LockAdd,
    IMG2MAT_OT_LockRemove,
    IMG2MAT_OT_UseActiveImage,
    IMG2MAT_AddonPreferences,
    IMG2MAT_Props,
    IMG2MAT_OT_Generate,
    IMG2MAT_OT_ImportACBLibrary,
    IMG2MAT_OT_ImportACBFolder,
    IMG2MAT_OT_RebuildLibraryManifest,
    IMG2MAT_OT_ToggleLibraryEnabled,
    IMG2MAT_OT_MatchPantonePalette,
    IMG2MAT_OT_MatchPantoneSample,
    IMG2MAT_OT_CopyPantoneResults,
    IMG2MAT_OT_CreateCallouts,
    IMG2MAT_OT_ClearSwatches,
    IMG2MAT_PT_Panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.img2mat_props = PointerProperty(type=IMG2MAT_Props)


def unregister():
    if hasattr(bpy.types.Scene, "img2mat_props"):
        del bpy.types.Scene.img2mat_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
