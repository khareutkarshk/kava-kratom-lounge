import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';

gsap.registerPlugin(ScrollTrigger);

const NAV_OFFSET = -84;
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const lenis = new Lenis({
	autoRaf: false,
	lerp: 0.085,
	wheelMultiplier: 0.92,
	stopInertiaOnNavigate: true,
	allowNestedScroll: true,
});

lenis.on('scroll', () => {
	ScrollTrigger.update();
	window.dispatchEvent(new CustomEvent('batcave:scroll'));
});

gsap.ticker.add((time) => {
	lenis.raf(time * 1000);
});
gsap.ticker.lagSmoothing(0);

if (!reduceMotion) {
	document.documentElement.classList.add('motion');
	initMotion();
	window.addEventListener('load', () => ScrollTrigger.refresh(), { once: true });
}

function initMotion() {
	const intro = gsap.utils.toArray<HTMLElement>('.arrival__intro > *');
	if (intro.length) {
		gsap.set(intro, { autoAlpha: 0, y: 16 });
		gsap.to(intro, {
			autoAlpha: 1,
			y: 0,
			duration: 0.75,
			stagger: 0.08,
			delay: 0.12,
			ease: 'power2.out',
		});
	}

	const reveals = gsap.utils.toArray<HTMLElement>('.reveal');
	if (reveals.length) {
		gsap.set(reveals, { autoAlpha: 0, y: 22 });
		ScrollTrigger.batch(reveals, {
			start: 'top 88%',
			once: true,
			onEnter: (batch) => {
				gsap.to(batch, {
					autoAlpha: 1,
					y: 0,
					duration: 0.8,
					stagger: 0.06,
					ease: 'power2.out',
					overwrite: 'auto',
				});
			},
		});
	}

	const hero = document.querySelector('.arrival__media .art-image__img');
	if (hero && window.matchMedia('(min-width: 768px)').matches) {
		gsap.fromTo(
			hero,
			{ yPercent: -2, scale: 1.04 },
			{
				yPercent: 3,
				scale: 1.04,
				ease: 'none',
				scrollTrigger: {
					trigger: '.arrival',
					start: 'top top',
					end: 'bottom top',
					scrub: 0.6,
				},
			},
		);
	}
}

window.addEventListener('batcave:nav', (event) => {
	const open = (event as CustomEvent<boolean>).detail;
	if (open) lenis.stop();
	else lenis.start();
});

document.addEventListener('click', (event) => {
	if (event.defaultPrevented || event.button !== 0) return;
	if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

	const link = (event.target as Element | null)?.closest?.('a[href^="#"]');
	if (!(link instanceof HTMLAnchorElement)) return;

	const hash = link.getAttribute('href');
	if (!hash || hash === '#') return;

	const target = document.querySelector(hash);
	if (!(target instanceof HTMLElement)) return;

	event.preventDefault();
	lenis.start();
	lenis.scrollTo(target, { offset: NAV_OFFSET, duration: 1.15 });
	if (window.location.hash !== hash) history.pushState(null, '', hash);
});
