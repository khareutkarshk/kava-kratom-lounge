/**
 * Implementation-ready asset path map for The Batcave.
 * Prefer Astro Image imports from src/assets/images and src/assets/decorative.
 */
export const assets = {
	brand: {
		logo: '/assets/brand/logo.transparent.webp',
		logoOpaque: '/assets/brand/logo.webp',
		logoMark: '/assets/brand/logo-mark.transparent.webp',
		logoWhite: '/assets/brand/logo-white.transparent.webp',
	},
	favicon: {
		svg: '/assets/favicon/favicon.svg',
		ico: '/assets/favicon/favicon.ico',
		png96: '/assets/favicon/favicon-96x96.png',
		appleTouch: '/assets/favicon/apple-touch-icon.png',
		manifest: '/assets/favicon/site.webmanifest',
	},
	textures: {
		brick: '/assets/textures/brick.webp',
		crumbledPaper: '/assets/textures/crumbled-paper.webp',
		noise: '/assets/textures/noise.webp',
		stone: '/assets/textures/stone.webp',
	},
	decorative: {
		bat: '/assets/decorative/bat.webp',
		corner: '/assets/decorative/corner.webp',
		frame: '/assets/decorative/frame.webp',
		lines: {
			dividerOrnate: '/assets/decorative/lines/divider-ornate.webp',
			dividerWave: '/assets/decorative/lines/divider-wave.webp',
			dividerCircuit: '/assets/decorative/lines/divider-circuit.webp',
			flourishSweep: '/assets/decorative/lines/flourish-sweep.webp',
			dividerCompact: '/assets/decorative/lines/divider-compact.webp',
			verticalSimple: '/assets/decorative/lines/accent-vertical-simple.webp',
			verticalCurve: '/assets/decorative/lines/accent-vertical-curve.webp',
			verticalStars: '/assets/decorative/lines/accent-vertical-stars.webp',
			verticalCircuit: '/assets/decorative/lines/accent-vertical-circuit.webp',
		},
	},
} as const;

export type Assets = typeof assets;
export default assets;
