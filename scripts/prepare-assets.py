#!/usr/bin/env python3
"""
Asset preparation for The Batcave website (data/prep phase only).

- Convert rasters → optimized WebP (+ transparent variants where black bg)
- Vectorize flat neon decorative graphics → SVG (neon purple #7000F8)
- Split lines_reference.png into separate line SVGs via connected components
- Emit a JSON asset manifest
"""

from __future__ import annotations

import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from potrace import Bitmap, BezierSegment, CornerSegment
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "public" / "assets"
SRC_DATA = ROOT / "src" / "data"
WORK = ROOT / ".asset-work"
NEON = "#7000F8"  # sampled from decorative source art (neon violet)


@dataclass
class JobResult:
    kind: str
    src: str
    outputs: list[str]


def ensure_dirs() -> None:
    for p in [
        WORK,
        ASSETS / "brand",
        ASSETS / "environment",
        ASSETS / "textures",
        ASSETS / "decorative" / "svg",
        ASSETS / "decorative" / "svg" / "lines",
        ASSETS / "decorative" / "webp",
        ASSETS / "hero",
        ASSETS / "_source",
        SRC_DATA,
    ]:
        p.mkdir(parents=True, exist_ok=True)


def save_webp(im: Image.Image, dest: Path, quality: int = 82, method: int = 6) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    params = {"quality": quality, "method": method}
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        params["lossless"] = False
    else:
        im = im.convert("RGB")
    im.save(dest, "WEBP", **params)


def make_black_transparent(im: Image.Image, threshold: int = 18) -> Image.Image:
    """Turn near-black pixels transparent (logos / neon-on-black art)."""
    rgba = im.convert("RGBA")
    arr = np.array(rgba)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    black = (r.astype(np.int16) + g.astype(np.int16) + b.astype(np.int16)) <= threshold * 3
    arr[..., 3] = np.where(black, 0, a)
    return Image.fromarray(arr, "RGBA")


def trim_alpha(im: Image.Image, pad: int = 4) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bbox = im.getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def resize_max(im: Image.Image, max_side: int) -> Image.Image:
    w, h = im.size
    m = max(w, h)
    if m <= max_side:
        return im
    scale = max_side / m
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def curves_to_svg_path(path) -> str:
    parts: list[str] = []
    start = path.start_point
    if start is None:
        return ""
    parts.append(f"M {start.x:.2f} {start.y:.2f}")
    for seg in path:
        if isinstance(seg, BezierSegment):
            parts.append(
                f"C {seg.c1.x:.2f} {seg.c1.y:.2f}, {seg.c2.x:.2f} {seg.c2.y:.2f}, {seg.end_point.x:.2f} {seg.end_point.y:.2f}"
            )
        elif isinstance(seg, CornerSegment):
            parts.append(f"L {seg.c.x:.2f} {seg.c.y:.2f} L {seg.end_point.x:.2f} {seg.end_point.y:.2f}")
    parts.append("Z")
    return " ".join(parts)


def bitmap_to_svg(
    mask: np.ndarray,
    out: Path,
    *,
    fill: str = NEON,
    turdsize: int = 4,
    opttolerance: float = 0.2,
) -> tuple[int, int]:
    """mask: True = ink (foreground)."""
    h, w = mask.shape
    # Bitmap expects bright = white; we pass boolean where True becomes white after threshold path
    # Looking at Bitmap.__init__: data > (255 * blacklevel) → True for white areas traced as ink after invert.
    # Safer: pass PIL L image where ink is black (0) and bg is white (255), blacklevel 0.5
    img = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")
    bm = Bitmap(img, blacklevel=0.5)
    paths = bm.trace(turdsize=turdsize, opttolerance=opttolerance, alphamax=1.0)

    d_parts = [curves_to_svg_path(p) for p in paths]
    d_parts = [d for d in d_parts if d]
    path_el = "\n  ".join(f'<path d="{d}" />' for d in d_parts)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" fill="{fill}" role="img" aria-hidden="true">
  {path_el}
</svg>
'''
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return w, h


def neon_mask_from_rgba(im: Image.Image, luma_min: int = 28) -> np.ndarray:
    rgba = np.array(im.convert("RGBA"))
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    luma = (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.float32)
    # Prefer purple-ish luminous pixels over pure white noise
    purple_bias = (b.astype(np.int16) > r.astype(np.int16) - 10) & (b > 40)
    return ((luma >= luma_min) & (a > 20) & purple_bias) | ((luma >= luma_min + 40) & (a > 20))


def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """4-connected component labeling via scipy."""
    labels, count = ndimage.label(mask.astype(np.uint8), structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    return labels.astype(np.int32), int(count)


def component_bboxes(labels: np.ndarray, count: int) -> list[tuple[int, int, int, int, int]]:
    """Return list of (label, x0, y0, x1, y1) with x1/y1 exclusive."""
    out = []
    for lab in range(1, count + 1):
        ys, xs = np.where(labels == lab)
        if len(xs) == 0:
            continue
        out.append((lab, int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return out


def classify_line_boxes(
    boxes: list[tuple[int, int, int, int, int]],
) -> list[tuple[str, tuple[int, int, int, int, int]]]:
    """
    Heuristic naming for lines_reference sheet (2172×724).
    Prefer large area components; classify by aspect ratio + position.
    """
    # Filter tiny noise
    scored = []
    for lab, x0, y0, x1, y1 in boxes:
        w, h = x1 - x0, y1 - y0
        area = w * h
        if area < 800:
            continue
        scored.append((area, lab, x0, y0, x1, y1, w, h))
    scored.sort(reverse=True)

    # Keep top components that look like the sheet elements
    keep = scored[:14]
    named: list[tuple[str, tuple[int, int, int, int, int]]] = []

    horizontals = []
    verticals = []
    others = []
    for area, lab, x0, y0, x1, y1, w, h in keep:
        ratio = w / max(h, 1)
        item = (lab, x0, y0, x1, y1)
        if ratio >= 2.2:
            horizontals.append((y0, w, item))
        elif ratio <= 0.55:
            verticals.append((x0, h, item))
        else:
            others.append((area, item, ratio))

    horizontals.sort()  # top → bottom
    h_names = [
        "divider-ornate",
        "divider-wave",
        "divider-circuit",
        "flourish-sweep",
        "divider-compact",
    ]
    for i, (_, _, item) in enumerate(horizontals):
        name = h_names[i] if i < len(h_names) else f"divider-h-{i + 1}"
        named.append((name, item))

    verticals.sort()  # left → right
    v_names = [
        "accent-vertical-simple",
        "accent-vertical-curve",
        "accent-vertical-stars",
        "accent-vertical-circuit",
    ]
    for i, (_, _, item) in enumerate(verticals):
        name = v_names[i] if i < len(v_names) else f"accent-v-{i + 1}"
        named.append((name, item))

    # Compact / odd leftovers
    for i, (_, item, _) in enumerate(sorted(others, reverse=True)):
        # Avoid duplicates if already covered by bbox overlap with named
        named.append((f"ornament-{i + 1}", item))

    # De-dupe by name keeping first
    seen = set()
    unique = []
    for name, item in named:
        if name in seen:
            continue
        seen.add(name)
        unique.append((name, item))
    return unique


def vectorize_neon_png(src: Path, dest_svg: Path, *, max_side: int = 1600) -> JobResult:
    im = Image.open(src).convert("RGBA")
    im = trim_alpha(make_black_transparent(im))
    im = resize_max(im, max_side)
    mask = neon_mask_from_rgba(im)
    # Dilate slightly for thin strokes continuity
    mask = binary_dilate(mask, iterations=1)
    bitmap_to_svg(mask, dest_svg, turdsize=8, opttolerance=0.25)
    return JobResult("svg", str(src.relative_to(ROOT)), [str(dest_svg.relative_to(ROOT))])


def binary_dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    return ndimage.binary_dilation(mask, iterations=iterations)


def split_and_vectorize_lines(src: Path, out_dir: Path) -> list[JobResult]:
    results: list[JobResult] = []
    im = Image.open(src).convert("RGBA")
    mask = neon_mask_from_rgba(im, luma_min=24)
    mask = binary_dilate(mask, iterations=1)

    # Close small gaps along strokes with a light morphological close via dilate+erode-ish:
    # For speed, just use dilated mask for labeling (may merge nearby elements — acceptable if thresholds ok)
    labels, count = label_components(mask)
    boxes = component_bboxes(labels, count)
    classified = classify_line_boxes(boxes)

    # Also write a reusable spark (largest small diamond-ish?) — extract from ornate center later
    spark_svg = out_dir / "spark.svg"
    write_spark_svg(spark_svg)
    results.append(JobResult("svg", "generated", [str(spark_svg.relative_to(ROOT))]))

    used_names: dict[str, int] = {}
    for name, (lab, x0, y0, x1, y1) in classified:
        # Skip generic ornaments that heavily overlap already-named
        if name.startswith("ornament-"):
            continue
        pad = 8
        x0p, y0p = max(0, x0 - pad), max(0, y0 - pad)
        x1p, y1p = min(im.width, x1 + pad), min(im.height, y1 + pad)
        crop_mask = labels[y0p:y1p, x0p:x1p] == lab
        if crop_mask.sum() < 200:
            continue
        n = used_names.get(name, 0)
        used_names[name] = n + 1
        final_name = name if n == 0 else f"{name}-{n + 1}"
        dest = out_dir / f"{final_name}.svg"
        bitmap_to_svg(crop_mask, dest, turdsize=3, opttolerance=0.2)
        # Also save transparent webp crop for reference
        crop_rgba = make_black_transparent(im.crop((x0p, y0p, x1p, y1p)))
        webp_dest = ASSETS / "decorative" / "webp" / "lines" / f"{final_name}.webp"
        webp_dest.parent.mkdir(parents=True, exist_ok=True)
        save_webp(crop_rgba, webp_dest, quality=90)
        results.append(
            JobResult(
                "line",
                str(src.relative_to(ROOT)),
                [str(dest.relative_to(ROOT)), str(webp_dest.relative_to(ROOT))],
            )
        )
    return results


def write_spark_svg(dest: Path) -> None:
    """Clean four-pointed star motif used across the decorative system."""
    dest.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="{NEON}" role="img" aria-hidden="true">
  <path d="M32 2 L36.5 27.5 L62 32 L36.5 36.5 L32 62 L27.5 36.5 L2 32 L27.5 27.5 Z"/>
</svg>
''',
        encoding="utf-8",
    )


def convert_raster_set() -> list[JobResult]:
    results: list[JobResult] = []

    # Brand — keep originals, emit webp + transparent webp
    brand_map = {
        "logo.png": ("logo", 1200),
        "logo_white.png": ("logo-white", 1200),
        "logo_notext.png": ("logo-mark", 1400),
    }
    for src_name, (stem, max_side) in brand_map.items():
        src = ASSETS / "brand" / src_name
        if not src.exists():
            continue
        im = Image.open(src)
        opaque = resize_max(im.convert("RGB"), max_side)
        save_webp(opaque, ASSETS / "brand" / f"{stem}.webp", quality=85)
        trans = trim_alpha(make_black_transparent(im.convert("RGBA")))
        trans = resize_max(trans, max_side)
        save_webp(trans, ASSETS / "brand" / f"{stem}.transparent.webp", quality=88)
        # Optimized transparent PNG for cases needing alpha without webp
        trans.save(ASSETS / "brand" / f"{stem}.transparent.png", optimize=True)
        results.append(
            JobResult(
                "brand",
                str(src.relative_to(ROOT)),
                [
                    f"public/assets/brand/{stem}.webp",
                    f"public/assets/brand/{stem}.transparent.webp",
                    f"public/assets/brand/{stem}.transparent.png",
                ],
            )
        )

    # Environment photos
    env_jobs = [
        ("arcade.png", "arcade", 1920),
        ("bar.png", "bar", 1920),
        ("exterior_desktop.png", "exterior-desktop", 1920),
        ("exteriror_mobile.png", "exterior-mobile", 1200),  # fix typo in output name
        ("goth_lounge.png", "goth-lounge", 1600),
        ("lounge.png", "lounge", 1920),
        ("merch-store.png", "merch-store", 1920),
    ]
    for src_name, stem, max_side in env_jobs:
        src = ASSETS / "environment" / src_name
        if not src.exists():
            continue
        im = resize_max(Image.open(src).convert("RGB"), max_side)
        dest = ASSETS / "environment" / f"{stem}.webp"
        save_webp(im, dest, quality=80)
        # Medium size for cards
        med = resize_max(im, 960)
        save_webp(med, ASSETS / "environment" / f"{stem}.md.webp", quality=78)
        results.append(
            JobResult(
                "environment",
                str(src.relative_to(ROOT)),
                [str(dest.relative_to(ROOT)), f"public/assets/environment/{stem}.md.webp"],
            )
        )

    # Hero candidates from exterior
    for stem in ("exterior-desktop", "exterior-mobile"):
        src = ASSETS / "environment" / f"{stem}.webp"
        if src.exists():
            shutil.copy2(src, ASSETS / "hero" / f"{stem}.webp")
            results.append(JobResult("hero", str(src.relative_to(ROOT)), [f"public/assets/hero/{stem}.webp"]))

    # Textures — tile-friendly, higher compression OK
    tex_jobs = [
        ("brick.png", "brick", 1024),
        ("crumbled_paper.png", "crumbled-paper", 1024),
        ("noise.png", "noise", 512),
        ("stone.png", "stone", 1024),
    ]
    for src_name, stem, max_side in tex_jobs:
        src = ASSETS / "textures" / src_name
        if not src.exists():
            continue
        im = resize_max(Image.open(src).convert("RGB"), max_side)
        q = 70 if stem == "noise" else 75
        dest = ASSETS / "textures" / f"{stem}.webp"
        save_webp(im, dest, quality=q)
        results.append(JobResult("texture", str(src.relative_to(ROOT)), [str(dest.relative_to(ROOT))]))

    # Decorative raster webp (transparent)
    deco = [
        ("bat.png", "bat"),
        ("corner_decoration.png", "corner"),
        ("frame.png", "frame"),
        ("lines_reference.png", "lines-reference"),
    ]
    for src_name, stem in deco:
        src = ASSETS / "decorative" / src_name
        if not src.exists():
            continue
        im = trim_alpha(make_black_transparent(Image.open(src)))
        im = resize_max(im, 1600 if stem != "frame" else 1400)
        dest = ASSETS / "decorative" / "webp" / f"{stem}.webp"
        save_webp(im, dest, quality=90)
        results.append(JobResult("decorative-webp", str(src.relative_to(ROOT)), [str(dest.relative_to(ROOT))]))

    return results


def prepare_decorative_svgs() -> list[JobResult]:
    results: list[JobResult] = []
    svg_dir = ASSETS / "decorative" / "svg"

    # Flat neon graphics → SVG
    for src_name, out_name in [
        ("bat.png", "bat.svg"),
        ("corner_decoration.png", "corner.svg"),
    ]:
        src = ASSETS / "decorative" / src_name
        if src.exists():
            results.append(vectorize_neon_png(src, svg_dir / out_name, max_side=1400))

    # Frame is mixed photo+neon — provide SVG of neon mask AND keep webp
    frame = ASSETS / "decorative" / "frame.png"
    if frame.exists():
        results.append(vectorize_neon_png(frame, svg_dir / "frame.svg", max_side=1200))
        # Extractable pieces via components (large ones)
        im = trim_alpha(make_black_transparent(Image.open(frame)))
        im = resize_max(im, 1200)
        mask = binary_dilate(neon_mask_from_rgba(im), 1)
        labels, count = label_components(mask)
        boxes = sorted(component_bboxes(labels, count), key=lambda b: (b[3] - b[1]) * (b[4] - b[2]), reverse=True)
        piece_dir = svg_dir / "frame-parts"
        piece_dir.mkdir(exist_ok=True)
        # Keep a few largest meaningful pieces
        for i, (lab, x0, y0, x1, y1) in enumerate(boxes[:6]):
            pad = 6
            x0p, y0p = max(0, x0 - pad), max(0, y0 - pad)
            x1p, y1p = min(im.width, x1 + pad), min(im.height, y1 + pad)
            crop = labels[y0p:y1p, x0p:x1p] == lab
            if crop.sum() < 400:
                continue
            dest = piece_dir / f"part-{i + 1}.svg"
            bitmap_to_svg(crop, dest, turdsize=5)
            results.append(JobResult("frame-part", str(frame.relative_to(ROOT)), [str(dest.relative_to(ROOT))]))

    # Lines sheet
    lines = ASSETS / "decorative" / "lines_reference.png"
    if lines.exists():
        results.extend(split_and_vectorize_lines(lines, svg_dir / "lines"))

    # Hand-authored clean geometric line set (implementation-friendly, neon purple)
    # These complement traced SVGs when perfect geometry is preferred.
    write_clean_line_kit(svg_dir / "lines" / "clean")
    results.append(
        JobResult(
            "line-kit",
            "generated",
            [str((svg_dir / "lines" / "clean").relative_to(ROOT))],
        )
    )

    return results


def write_clean_line_kit(out_dir: Path) -> None:
    """Clean geometric SVGs matching the reference styles for reliable UI use."""
    out_dir.mkdir(parents=True, exist_ok=True)

    spark = '<path d="M0 -10 L1.6 -1.6 L10 0 L1.6 1.6 L0 10 L-1.6 1.6 L-10 0 L-1.6 -1.6 Z"/>'

    def wrap(view: str, body: str, name: str) -> None:
        (out_dir / f"{name}.svg").write_text(
            f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" fill="{NEON}" stroke="none" role="img" aria-hidden="true">
{body}
</svg>
''',
            encoding="utf-8",
        )

    # Ornate horizontal divider
    wrap(
        "0 0 400 40",
        f'''
  <path d="M8 20 H150" stroke="#7000F8" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  <path d="M250 20 H392" stroke="#7000F8" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  <path d="M150 20 H168 V12 H182" stroke="#7000F8" stroke-width="1.5" fill="none"/>
  <path d="M250 20 H232 V12 H218" stroke="#7000F8" stroke-width="1.5" fill="none"/>
  <g transform="translate(200 20) scale(1.35)">{spark}</g>
  <g transform="translate(175 12) scale(0.55)">{spark}</g>
  <g transform="translate(225 12) scale(0.55)">{spark}</g>
''',
        "divider-ornate",
    )

    # Wave divider
    wrap(
        "0 0 400 48",
        f'''
  <path d="M10 30 C70 30 90 12 140 12 S210 30 200 18 S230 30 390 30" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(200 16) scale(0.7)">{spark}</g>
''',
        "divider-wave",
    )

    # Circuit divider
    wrap(
        "0 0 400 48",
        f'''
  <path d="M8 28 H120 V14 H160 V28 H240 V14 H280 V28 H392" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="square"/>
  <g transform="translate(140 14) scale(0.55)">{spark}</g>
  <g transform="translate(200 28) scale(0.9)">{spark}</g>
  <g transform="translate(260 14) scale(0.55)">{spark}</g>
  <g transform="translate(100 28) scale(0.4)">{spark}</g>
  <g transform="translate(300 28) scale(0.4)">{spark}</g>
''',
        "divider-circuit",
    )

    # Sweep flourish
    wrap(
        "0 0 360 80",
        f'''
  <path d="M20 18 C80 10 120 8 160 28 S240 70 340 62" stroke="#7000F8" stroke-width="1.6" fill="none" stroke-linecap="round"/>
  <g transform="translate(110 16) scale(0.7)">{spark}</g>
  <g transform="translate(230 55) scale(0.7)">{spark}</g>
''',
        "flourish-sweep",
    )

    # Compact divider
    wrap(
        "0 0 160 36",
        f'''
  <path d="M8 18 H55" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M105 18 H152" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(80 18) scale(1.1)">{spark}</g>
  <g transform="translate(62 18) scale(0.45)">{spark}</g>
  <g transform="translate(98 18) scale(0.45)">{spark}</g>
''',
        "divider-compact",
    )

    # Vertical accents
    wrap(
        "0 0 24 200",
        f'''
  <path d="M12 8 V192" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(12 100) scale(0.7)">{spark}</g>
''',
        "accent-vertical-simple",
    )

    wrap(
        "0 0 40 200",
        f'''
  <path d="M20 8 C8 50 32 90 20 100 C8 120 32 160 20 192" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(20 100) scale(0.7)">{spark}</g>
''',
        "accent-vertical-curve",
    )

    wrap(
        "0 0 24 200",
        f'''
  <path d="M12 8 V192" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <g transform="translate(12 50) scale(0.65)">{spark}</g>
  <g transform="translate(12 100) scale(0.65)">{spark}</g>
  <g transform="translate(12 150) scale(0.65)">{spark}</g>
''',
        "accent-vertical-stars",
    )

    wrap(
        "0 0 48 220",
        f'''
  <path d="M24 8 V50 H12 V90 H24 V130 H36 V170 H24 V212" stroke="#7000F8" stroke-width="1.5" fill="none" stroke-linecap="square"/>
  <g transform="translate(24 50) scale(0.55)">{spark}</g>
  <g transform="translate(24 130) scale(0.7)">{spark}</g>
  <g transform="translate(24 170) scale(0.55)">{spark}</g>
''',
        "accent-vertical-circuit",
    )

    wrap("0 0 64 64", f'<g transform="translate(32 32) scale(2.2)">{spark}</g>', "spark")


def write_content_data() -> Path:
    """Structured site content for implementation. Location: Sanford, Florida."""
    data = {
        "brand": {
            "name": "The Batcave",
            "nameDisplay": "THE BATCAVE",
            "descriptor": "Kava & Kratom Lounge",
            "descriptorDisplay": "KAVA & KRATOM LOUNGE",
            "tagline": "An underground neon lair for kava, kratom, art, and arcade nights.",
            "shortIntro": "A gothic underground lounge combining art, live music, a vintage-style arcade, merchandise, signature kratom teas, signature kava mocktails, and kava-based ice cream.",
        },
        "location": {
            "city": "Sanford",
            "state": "FL",
            "stateFull": "Florida",
            "country": "US",
            "display": "Sanford, Florida",
            "streetAddress": None,
            "postalCode": None,
            "mapsQuery": "The Batcave Kava & Kratom Lounge Sanford Florida",
            "note": "City/state provided for launch prep. Exact street address, hours, and contact details still need client confirmation.",
        },
        "visit": {
            "phone": None,
            "email": None,
            "hours": None,
            "reservationsUrl": None,
            "parking": None,
            "ageRequirement": None,
            "socials": {
                "instagram": None,
                "facebook": None,
                "tiktok": None,
                "x": None,
            },
            "placeholders": {
                "streetAddress": "[Street address — client TBD]",
                "hours": "[Hours — client TBD]",
                "phone": "[Phone — client TBD]",
                "email": "[Email — client TBD]",
            },
        },
        "navigation": [
            {"id": "experience", "label": "The Experience"},
            {"id": "lounge", "label": "The Lounge"},
            {"id": "arcade", "label": "The Arcade"},
            {"id": "offerings", "label": "Signature"},
            {"id": "merchandise", "label": "Merchandise"},
            {"id": "visit", "label": "Visit"},
        ],
        "features": [
            {
                "id": "art-live-music",
                "label": "Art & Live Music",
                "labelDisplay": "ART & LIVE MUSIC",
                "description": "Live music and art-focused events.",
                "deckPhrase": "Art and Live Music Events",
            },
            {
                "id": "merchandise",
                "label": "Merchandise Store",
                "labelDisplay": "MERCHANDISE STORE",
                "description": "A dedicated merchandise and collectible retail space.",
                "deckPhrase": "Merchandise Store",
            },
            {
                "id": "arcade",
                "label": "Vintage Arcade",
                "labelDisplay": "VINTAGE STYLE ARCADE",
                "description": "A vintage-style arcade experience.",
                "deckPhrase": "Vintage Style Arcade",
            },
            {
                "id": "kratom-teas",
                "label": "Signature Kratom Teas",
                "labelDisplay": "EXCLUSIVE SIGNATURE KRATOM TEAS",
                "description": "Exclusive signature kratom teas.",
                "deckPhrase": "Exclusive Signature Kratom Teas",
            },
            {
                "id": "kava-mocktails",
                "label": "Signature Kava Mocktails",
                "labelDisplay": "EXCLUSIVE SIGNATURE KAVA MOCKTAILS",
                "description": "Exclusive signature kava mocktails.",
                "deckPhrase": "Exclusive Signature Kava Mocktails",
            },
            {
                "id": "kava-ice-cream",
                "label": "Kava-Based Ice Cream",
                "labelDisplay": "KAVA BASED ICE CREAM",
                "description": "Ice cream incorporating kava.",
                "deckPhrase": "Kava Based Ice Cream",
            },
        ],
        "sections": {
            "hero": {
                "eyebrow": "Sanford, Florida",
                "title": "THE BATCAVE",
                "subtitle": "KAVA & KRATOM LOUNGE",
                "supporting": "Step into an underground neon lair — gothic lounge energy, vintage arcade glow, and signature kava & kratom.",
                "primaryCta": {"label": "Plan Your Visit", "href": "#visit"},
                "secondaryCta": {"label": "Explore the Lair", "href": "#experience"},
                "assets": {
                    "desktop": "/assets/hero/exterior-desktop.webp",
                    "mobile": "/assets/hero/exterior-mobile.webp",
                },
            },
            "experience": {
                "id": "experience",
                "heading": "The Experience",
                "intro": "Art, live music, arcade nights, and a dark luxury lounge — one underground destination.",
            },
            "lounge": {
                "id": "lounge",
                "heading": "The Lounge",
                "intro": "Cave-inspired interiors, violet light, and late-night atmosphere.",
                "assets": [
                    "/assets/environment/lounge.webp",
                    "/assets/environment/goth-lounge.webp",
                    "/assets/environment/bar.webp",
                ],
            },
            "arcade": {
                "id": "arcade",
                "heading": "The Arcade",
                "intro": "A vintage-style arcade room built for retro play under neon.",
                "assets": ["/assets/environment/arcade.webp"],
            },
            "offerings": {
                "id": "offerings",
                "heading": "Signature Offerings",
                "intro": "Exclusive signature kratom teas, signature kava mocktails, and kava-based ice cream.",
                "items": ["kratom-teas", "kava-mocktails", "kava-ice-cream"],
            },
            "merchandise": {
                "id": "merchandise",
                "heading": "Merchandise",
                "intro": "A dedicated store for merch, art, and collectible culture.",
            },
            "visit": {
                "id": "visit",
                "heading": "Visit The Batcave",
                "intro": "Find us in Sanford, Florida.",
                "ctaLabel": "Get Directions",
            },
        },
        "seo": {
            "title": "The Batcave — Kava & Kratom Lounge | Sanford, FL",
            "description": "The Batcave is a gothic underground kava & kratom lounge in Sanford, Florida — featuring art and live music, a vintage arcade, merchandise, signature teas, mocktails, and kava-based ice cream.",
            "ogImage": "/assets/environment/exterior-desktop.webp",
        },
        "legalNotes": {
            "claims": "Deck phrases like “exclusive signature” are marketing copy from the concept deck, not independently verified claims.",
            "ip": "Do not use third-party comic/superhero character artwork unless the client confirms rights. Prefer original bat/cave/neon motifs.",
        },
        "assetHints": {
            "logoPrimary": "/assets/brand/logo.transparent.webp",
            "logoMark": "/assets/brand/logo-mark.transparent.webp",
            "logoMono": "/assets/brand/logo-white.transparent.webp",
            "decorativeBat": "/assets/decorative/svg/bat.svg",
            "decorativeCorner": "/assets/decorative/svg/corner.svg",
            "decorativeFrame": "/assets/decorative/webp/frame.webp",
            "lineDividers": "/assets/decorative/svg/lines/clean/",
            "textures": {
                "noise": "/assets/textures/noise.webp",
                "brick": "/assets/textures/brick.webp",
                "stone": "/assets/textures/stone.webp",
                "paper": "/assets/textures/crumbled-paper.webp",
            },
        },
        "clientTodo": [
            "Exact street address & ZIP",
            "Opening hours",
            "Phone & email",
            "Social profile URLs",
            "Reservation / booking link (if any)",
            "Age policy",
            "Parking / accessibility notes",
            "Confirm merchandise imagery rights",
        ],
    }

    json_path = SRC_DATA / "site-content.json"
    ts_path = SRC_DATA / "site.ts"
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    ts_path.write_text(
        f'''/**
 * Prepared site content for The Batcave (implementation-ready).
 * Location: Sanford, Florida — street/hours/contact still client TBD.
 * Source: batcave_website_content.txt + client prep notes.
 */
import content from './site-content.json';

export type SiteContent = typeof content;
export const site = content as SiteContent;
export default site;
''',
        encoding="utf-8",
    )
    return json_path


def write_manifest(results: list[JobResult]) -> Path:
    manifest = {
        "generatedFor": "The Batcave — Kava & Kratom Lounge",
        "phase": "asset-preparation",
        "neonFallback": NEON,
        "svgColor": "#7000F8",
        "jobs": [{"kind": r.kind, "src": r.src, "outputs": r.outputs} for r in results],
        "recommendedUsage": {
            "photos": "Prefer *.webp (full) or *.md.webp for cards",
            "logos": "Prefer *.transparent.webp on dark UI; keep source PNG as master",
            "lines": "Prefer /decorative/svg/lines/clean/*.svg for UI dividers (neon purple)",
            "tracedLines": "/decorative/svg/lines/*.svg are potrace extractions from the reference sheet",
            "batCorner": "Use SVG with text-violet / text-primary for neon tint",
            "frame": "Prefer webp/frame.webp for photographic rock detail; SVG is neon silhouette only",
        },
    }
    path = ASSETS / "MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def update_assets_readme() -> None:
    readme = ASSETS / "README.md"
    readme.write_text(
        '''# Public assets

Prepared for implementation. Prefer **WebP** for photos/textures and **SVG** for neon decorative linework.

## Brand
| File | Use |
| --- | --- |
| `brand/logo.transparent.webp` | Primary logo with alpha |
| `brand/logo-mark.transparent.webp` | Bat mark, no wordmark |
| `brand/logo-white.transparent.webp` | Mono / high-contrast logo |
| `brand/*.png` | Master source files (do not delete) |

## Environment / Hero
| File | Use |
| --- | --- |
| `environment/*.webp` | Full-width scene photos |
| `environment/*.md.webp` | Card / mid-size |
| `hero/exterior-desktop.webp` | Hero desktop candidate |
| `hero/exterior-mobile.webp` | Hero mobile candidate |

## Decorative
| Path | Use |
| --- | --- |
| `decorative/svg/bat.svg` | Neon bat motif (`#7000F8`) |
| `decorative/svg/corner.svg` | Corner frame (mirror/rotate in CSS) |
| `decorative/svg/frame.svg` | Neon silhouette of frame |
| `decorative/webp/frame.webp` | Full frame with rock detail |
| `decorative/svg/lines/clean/*.svg` | **Preferred** UI dividers/accents |
| `decorative/svg/lines/*.svg` | Traced extractions from `lines_reference.png` |
| `decorative/svg/lines/spark.svg` | Four-pointed star motif |

## Textures
`textures/*.webp` — noise, brick, stone, crumbled paper (keep opacity low in CSS).

## Content
Structured copy lives in `src/data/site-content.json` (+ `src/data/site.ts`).

## IP note
Do not add copyrighted Batman/Spider-Man character art. Original bat/cave/neon motifs only.
''',
        encoding="utf-8",
    )


def main() -> None:
    ensure_dirs()
    results: list[JobResult] = []
    print("→ Converting rasters to WebP…")
    results.extend(convert_raster_set())
    print("→ Vectorizing decorative assets & splitting lines…")
    results.extend(prepare_decorative_svgs())
    print("→ Writing site content data…")
    content_path = write_content_data()
    print("→ Writing manifest…")
    manifest_path = write_manifest(results)
    update_assets_readme()

    # Also refresh human content source with Sanford note
    content_txt = ROOT / "batcave_website_content.txt"
    if content_txt.exists():
        text = content_txt.read_text(encoding="utf-8")
        if "Sanford" not in text:
            text += (
                "\n\nLOCATION (CLIENT PREP)\n\n"
                "City/State: Sanford, Florida\n"
                "Exact street address, hours, and contact details: still required from client.\n"
            )
            content_txt.write_text(text, encoding="utf-8")

    print(f"Done. Jobs: {len(results)}")
    print(f"Content: {content_path.relative_to(ROOT)}")
    print(f"Manifest: {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
