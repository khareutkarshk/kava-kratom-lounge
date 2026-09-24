# Public assets

Prefer **lossless WebP** for neon decorative line art (sharpness). Photos/textures use lossy WebP.

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

## Decorative (raster only — no SVGs)
| Path | Use |
| --- | --- |
| `decorative/bat.webp` | Neon bat motif |
| `decorative/corner.webp` | Corner frame (mirror/rotate in CSS) |
| `decorative/frame.webp` | Full decorative frame |
| `decorative/lines/*.webp` | Cropped dividers/accents from `lines_reference.png` |
| `decorative/lines/*.png` | PNG siblings if WebP is unavailable |

**Astro:** import from `src/assets/decorative/` and use `<Image />` from `astro:assets` (see `src/assets/decorative/index.ts`).

Re-crop lines after changing the reference:

```sh
.venv-assets/bin/python scripts/crop-decorative-rasters.py
```

## Textures
`textures/*.webp` — noise, brick, stone, crumbled paper (keep opacity low in CSS).

## Content
Structured copy: `src/data/site-content.json` (+ `site.ts`, `assets.ts`).

## IP note
Do not add copyrighted Batman/Spider-Man character art. Original bat/cave/neon motifs only.
