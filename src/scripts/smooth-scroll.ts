import Lenis from 'lenis';

const NAV_OFFSET = -84;

const lenis = new Lenis({
	autoRaf: true,
	lerp: 0.085,
	wheelMultiplier: 0.92,
	stopInertiaOnNavigate: true,
	allowNestedScroll: true,
});

lenis.on('scroll', () => {
	window.dispatchEvent(new CustomEvent('batcave:scroll'));
});

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
