/**
 * Lavisco News — Micro-interactions
 * Subtle hover effects, button feedback, and scroll-triggered reveals.
 */
(function() {
    'use strict';

    // Respect reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    // === Scroll-triggered fade-in ===
    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

        document.querySelectorAll('.story-card, .house-card, .club-card, .event-card').forEach(function(el) {
            el.classList.add('reveal-on-scroll');
            observer.observe(el);
        });
    }

    // === Button press feedback ===
    document.querySelectorAll('.btn').forEach(function(btn) {
        btn.addEventListener('mousedown', function() {
            btn.style.transform = 'scale(0.97)';
        });
        btn.addEventListener('mouseup', function() {
            btn.style.transform = '';
        });
        btn.addEventListener('mouseleave', function() {
            btn.style.transform = '';
        });
    });

})();