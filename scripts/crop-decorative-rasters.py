#!/usr/bin/env python3
"""
Re-crop decorative line art from lines_reference.png as sharp transparent images.
Removes SVG outputs — raster crops only (lossless WebP + PNG).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "public" / "assets"
SRC_ASSETS = ROOT / "src" / "assets" / "decorative"
DECO = ASSETS / "decorative"
LINES_SRC = DECO / "lines_reference.png"

# Output dirs (public for URL paths + src for Astro <Image /> imports)
PUBLIC_LINES = DECO / "lines"
SRC_LINES = SRC_ASSETS / "lines"
PUBLIC_DECO = DECO  # bat/corner/frame live beside sources


def make_black_transparent(im: Image.Image, threshold: int = 14) -> Image.Image:
    rgba = im.convert("RGBA")
    arr = np.array(rgba)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    black = (r.astype(np.int16) + g.astype(np.int16) + b.astype(np.int16)) <= threshold * 3
    arr[..., 3] = np.where(black, 0, a)
    return Image.fromarray(arr, "RGBA")


def trim_alpha(im: Image.Image, pad: int = 6) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l, t = max(0, l - pad), max(0, t - pad)
    r, b = min(im.width, r + pad), min(im.height, b + pad)
    return im.crop((l, t, r, b))


def neon_mask(im: Image.Image, luma_min: int = 22) -> np.ndarray:
    rgba = np.array(im.convert("RGBA"))
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    purple = (b.astype(np.int16) >= r.astype(np.int16) - 8) & (b > 35)
    return ((luma >= luma_min) & (a > 15) & purple) | ((luma >= luma_min + 35) & (a > 15))


def save_sharp(im: Image.Image, dest_stem: Path) -> list[str]:
    """Lossless WebP + compressed PNG for max neon-line sharpness."""
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    webp = dest_stem.with_suffix(".webp")
    png = dest_stem.with_suffix(".png")
    im.save(webp, "WEBP", lossless=True, method=6)
    im.save(png, "PNG", optimize=True)
    return [str(webp.relative_to(ROOT)), str(png.relative_to(ROOT))]


def classify_boxes(boxes: list[tuple]) -> list[tuple[str, tuple]]:
    """boxes: (lab, x0, y0, x1, y1, area, w, h)"""
    horizontals, verticals = [], []
    for lab, x0, y0, x1, y1, area, w, h in boxes:
        if area < 1200:
            continue
        ratio = w / max(h, 1)
        item = (lab, x0, y0, x1, y1)
        if ratio >= 2.0:
            horizontals.append((y0, w, item))
        elif ratio <= 0.6:
            verticals.append((x0, h, item))

    horizontals.sort()
    verticals.sort()
    h_names = [
        "divider-ornate",
        "divider-wave",
        "divider-circuit",
        "flourish-sweep",
        "divider-compact",
    ]
    v_names = [
        "accent-vertical-simple",
        "accent-vertical-curve",
        "accent-vertical-stars",
        "accent-vertical-circuit",
    ]
    out: list[tuple[str, tuple]] = []
    for i, (_, _, item) in enumerate(horizontals[:5]):
        out.append((h_names[i] if i < len(h_names) else f"divider-h-{i+1}", item))
    for i, (_, _, item) in enumerate(verticals[:4]):
        out.append((v_names[i] if i < len(v_names) else f"accent-v-{i+1}", item))
    return out


def crop_lines() -> list[str]:
    im = Image.open(LINES_SRC).convert("RGBA")
    mask = neon_mask(im)
    # Light close so thin strokes stay one component without merging distant lines
    mask = ndimage.binary_dilation(mask, iterations=1)
    labels, count = ndimage.label(mask.astype(np.uint8), structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))

    boxes = []
    for lab in range(1, count + 1):
        ys, xs = np.where(labels == lab)
        if len(xs) == 0:
            continue
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        w, h = x1 - x0, y1 - y0
        boxes.append((lab, x0, y0, x1, y1, w * h, w, h))

    classified = classify_boxes(boxes)
    outputs: list[str] = []

    for name, (lab, x0, y0, x1, y1) in classified:
        pad = 10
        x0p, y0p = max(0, x0 - pad), max(0, y0 - pad)
        x1p, y1p = min(im.width, x1 + pad), min(im.height, y1 + pad)

        # Crop full RGBA from source, then punch transparency for non-component pixels
        crop = im.crop((x0p, y0p, x1p, y1p)).convert("RGBA")
        local = labels[y0p:y1p, x0p:x1p] == lab
        # Slight expand so anti-aliased purple edges aren't clipped
        local = ndimage.binary_dilation(local, iterations=2)
        arr = np.array(crop)
        # Keep purple pixels near the component; clear pure black
        keep = local | (neon_mask(crop) & ndimage.binary_dilation(local, iterations=3))
        arr[..., 3] = np.where(keep, arr[..., 3], 0)
        # Force near-black to transparent
        rgb_sum = arr[..., 0].astype(np.int16) + arr[..., 1] + arr[..., 2]
        arr[..., 3] = np.where(rgb_sum <= 42, 0, arr[..., 3])
        out_im = trim_alpha(Image.fromarray(arr, "RGBA"), pad=4)

        for base in (PUBLIC_LINES / name, SRC_LINES / name):
            outputs.extend(save_sharp(out_im, base))
        print(f"  line {name}: {out_im.size[0]}×{out_im.size[1]}")

    # Standalone spark crop from ornate center (small square) — optional helper from divider-ornate
    # Extract a spark by finding small diamond-like component? Skip — spark not needed as separate if unused.
    return outputs


def export_decorative_rasters() -> list[str]:
    """
    Export web-ready transparent rasters.
    Never overwrite masters named *_reference / *_decoration / logo sources.
    Writes bat.webp|png, corner.webp|png, frame.webp|png alongside masters.
    """
    outputs: list[str] = []
    jobs = [
        # Prefer dedicated master names when present
        ("bat.png", "bat"),
        ("corner_decoration.png", "corner"),
        ("frame.png", "frame"),
    ]
    for src_name, stem in jobs:
        src = DECO / src_name
        # If master was already replaced by a previous run, still allow re-export from current file
        if not src.exists() and stem == "corner":
            src = DECO / "corner.png"
        if not src.exists():
            continue
        im = trim_alpha(make_black_transparent(Image.open(src)))
        # Public: webp + png with stem name (safe if src is corner_decoration.png)
        # If src is bat.png/frame.png, writing bat.png would overwrite — write webp only + .transparent.png
        if src.name == f"{stem}.png":
            webp_only = DECO / stem
            im.save(webp_only.with_suffix(".webp"), "WEBP", lossless=True, method=6)
            im.save(DECO / f"{stem}.transparent.png", "PNG", optimize=True)
            outputs.append(str((DECO / f"{stem}.webp").relative_to(ROOT)))
            outputs.append(str((DECO / f"{stem}.transparent.png").relative_to(ROOT)))
        else:
            for base in (DECO / stem,):
                outputs.extend(save_sharp(im, base))
        for base in (SRC_ASSETS / stem,):
            outputs.extend(save_sharp(im, base))
        print(f"  deco {stem}: {im.size[0]}×{im.size[1]}")
    return outputs


def wipe_svgs_and_old() -> None:
    svg_dir = DECO / "svg"
    if svg_dir.exists():
        shutil.rmtree(svg_dir)
        print("removed decorative/svg/")
    old_webp = DECO / "webp"
    if old_webp.exists():
        shutil.rmtree(old_webp)
        print("removed decorative/webp/ (superseded by /lines and root deco images)")
    # Remove stale lines-reference webp if any at root
    for stale in DECO.glob("lines-reference.*"):
        stale.unlink(missing_ok=True)


def write_manifest(outputs: list[str]) -> None:
    lines = sorted({p.name for p in PUBLIC_LINES.glob("*.webp")})
    manifest = {
        "phase": "raster-decorative-only",
        "note": "SVGs removed. Use lossless WebP (preferred) or PNG for sharp neon line art.",
        "astro": {
            "preferred": "Import from src/assets/decorative/ and use Astro <Image />",
            "publicFallback": "Or reference /assets/decorative/... paths in <img>",
        },
        "decorative": {
            "bat": "/assets/decorative/bat.webp",
            "corner": "/assets/decorative/corner.webp",
            "frame": "/assets/decorative/frame.webp",
        },
        "lines": {name.replace(".webp", ""): f"/assets/decorative/lines/{name}" for name in lines},
        "outputs": outputs,
    }
    (ASSETS / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    PUBLIC_LINES.mkdir(parents=True, exist_ok=True)
    SRC_LINES.mkdir(parents=True, exist_ok=True)
    SRC_ASSETS.mkdir(parents=True, exist_ok=True)

    wipe_svgs_and_old()
    print("→ Cropping lines from reference (full-res, lossless)…")
    outputs = crop_lines()
    print("→ Exporting bat / corner / frame…")
    outputs.extend(export_decorative_rasters())
    write_manifest(outputs)
    print(f"Done. {len(outputs)} files written.")


if __name__ == "__main__":
    main()
