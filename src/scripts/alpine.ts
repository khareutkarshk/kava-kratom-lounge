import type { Alpine } from 'alpinejs';
import intersect from '@alpinejs/intersect';

export default (Alpine: Alpine) => {
	Alpine.plugin(intersect);

	Alpine.data('siteNav', () => ({
		scrolled: false,
		hidden: false,
		menuOpen: false,
		active: '',
		lastY: 0,

		init() {
			this.onScroll();
			this.watchSections();
			window.addEventListener('scroll', () => this.onScroll(), { passive: true });
			window.addEventListener('batcave:scroll', () => this.onScroll());
			window.addEventListener('keydown', (e: KeyboardEvent) => {
				if (e.key === 'Escape' && this.menuOpen) this.closeMenu();
			});
		},

		watchSections() {
			const ids = ['lounge', 'bar', 'arcade', 'merchandise'];
			const observer = new IntersectionObserver(
				(entries) => {
					const visible = entries
						.filter((entry) => entry.isIntersecting)
						.sort((a, b) => b.intersectionRatio - a.intersectionRatio);
					const current = visible[0]?.target;
					if (current instanceof HTMLElement) this.active = current.id;
				},
				{ rootMargin: '-32% 0px -52% 0px', threshold: [0.12, 0.35, 0.6] },
			);

			for (const id of ids) {
				const section = document.getElementById(id);
				if (section) observer.observe(section);
			}
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
			window.dispatchEvent(new CustomEvent('batcave:nav', { detail: true }));
		},

		closeMenu() {
			this.menuOpen = false;
			document.documentElement.classList.remove('nav-lock');
			window.dispatchEvent(new CustomEvent('batcave:nav', { detail: false }));
		},

		toggleMenu() {
			if (this.menuOpen) this.closeMenu();
			else this.openMenu();
		},
	}));
};
