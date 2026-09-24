import type { Alpine } from 'alpinejs';
import intersect from '@alpinejs/intersect';

export default (Alpine: Alpine) => {
	Alpine.plugin(intersect);

	Alpine.data('siteNav', () => ({
		scrolled: false,
		hidden: false,
		menuOpen: false,
		lastY: 0,

		init() {
			this.onScroll();
			window.addEventListener('scroll', () => this.onScroll(), { passive: true });
			window.addEventListener('keydown', (e: KeyboardEvent) => {
				if (e.key === 'Escape' && this.menuOpen) this.closeMenu();
			});
		},

		onScroll() {
			const y = window.scrollY;
			const arrival = document.getElementById('top');
			const threshold = arrival ? arrival.offsetHeight * 0.75 : 400;
			this.scrolled = y > threshold;

			if (y > this.lastY && y > threshold + 80) {
				this.hidden = true;
			} else {
				this.hidden = false;
			}
			this.lastY = y;
		},

		openMenu() {
			this.menuOpen = true;
			document.documentElement.classList.add('nav-lock');
		},

		closeMenu() {
			this.menuOpen = false;
			document.documentElement.classList.remove('nav-lock');
		},

		toggleMenu() {
			if (this.menuOpen) this.closeMenu();
			else this.openMenu();
		},
	}));
};
