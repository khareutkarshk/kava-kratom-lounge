/**
 * Astro Image–ready imports for decorative neon art (lossless WebP).
 *
 * @example
 * import { Image } from 'astro:assets';
 * import { lines } from '../assets/decorative';
 * <Image src={lines.dividerOrnate} alt="" class="w-full h-auto" />
 */
import bat from './bat.webp';
import corner from './corner.webp';
import frame from './frame.webp';
import dividerOrnate from './lines/divider-ornate.webp';
import dividerWave from './lines/divider-wave.webp';
import dividerCircuit from './lines/divider-circuit.webp';
import flourishSweep from './lines/flourish-sweep.webp';
import dividerCompact from './lines/divider-compact.webp';
import verticalSimple from './lines/accent-vertical-simple.webp';
import verticalCurve from './lines/accent-vertical-curve.webp';
import verticalStars from './lines/accent-vertical-stars.webp';
import verticalCircuit from './lines/accent-vertical-circuit.webp';

export const decorative = {
	bat,
	corner,
	frame,
} as const;

export const lines = {
	dividerOrnate,
	dividerWave,
	dividerCircuit,
	flourishSweep,
	dividerCompact,
	verticalSimple,
	verticalCurve,
	verticalStars,
	verticalCircuit,
} as const;

export default { decorative, lines };
