# The Batcave — Kava & Kratom Lounge

Single-page marketing site foundation for an underground neon kava & kratom lounge.

This repo currently contains **design-system initialization only** — no final page sections, hero, gallery, or marketing composition yet.

## Stack

- Astro 7 (static / server rendering preferred)
- TypeScript
- Tailwind CSS 4 (`@tailwindcss/vite`)
- Alpine.js (`@astrojs/alpinejs`) — reserved for small interactions
- `@lucide/astro` — UI icons only (not the brand mark)
- Fontsource — Space Grotesk Variable, Bebas Neue, Pirata One

No React / Vue / Svelte / Solid. No large UI kits.

## Commands

| Command | Action |
| --- | --- |
| `pnpm install` | Install dependencies |
| `pnpm dev` | Dev server (`astro dev`) |
| `pnpm build` | Production build |
| `pnpm preview` | Preview production build |

For background mode per project agents docs: `astro dev --background`.

## Structure

```text
/
├── public/assets/            # Prepared media (see README + MANIFEST.json)
│   ├── brand/
│   ├── environment/
│   ├── hero/
│   ├── textures/
│   └── decorative/
│       ├── bat.webp / corner.webp / frame.webp
│       ├── lines/*.webp      # cropped from lines_reference.png
│       └── lines_reference.png
├── src/assets/decorative/    # Astro <Image /> imports (+ index.ts)
├── src/data/                 # site-content.json, site.ts, assets.ts
├── src/components/ui/
├── scripts/
│   ├── prepare-assets.py
│   └── crop-decorative-rasters.py
├── astro.config.mjs
└── package.json
```

Re-crop decorative lines after changing the reference sheet:

```sh
pnpm prepare:decorative
```
## Design direction

Dark-first “underground neon lair”: gothic, nocturnal, theatrical, retro arcade — neon as accent, not flood fill. Avoid SaaS glassmorphism and rainbow cyberpunk.

## Next stage

Compose the actual single-page experience using these tokens and primitives.
