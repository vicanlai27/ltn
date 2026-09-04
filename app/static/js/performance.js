/**
 * Lavisco News — Performance helpers
 * Native lazy loading observer for below-fold images,
 * connection-aware image quality, and prefetch on hover.
 */
(function() {
    'use strict';

    // === Connection-aware image quality ===
    // On slow connections, prefer smaller images
    (function() {
        if (!('connection' in navigator)) return;
        var conn = navigator.connection;
        if (!conn) return;

        var slow = conn.saveData ||
                   conn.effectiveType === 'slow-2g' ||
                   conn.effectiveType === '2g' ||
                   conn.effectiveType === '3g';

        if (slow) {
            document.documentElement.setAttribute('data-connection', 'slow');
            // Replace srcset with small-only versions
            document.querySelectorAll('img[srcset]').forEach(function(img) {
                var srcset = img.getAttribute('srcset');
                // Keep only the smallest variant
                var small = srcset.split(',').find(function(s) {
                    return s.indexOf('400w') !== -1;
                });
                if (small) {
                    img.setAttribute('srcset', small.trim());
                    img.setAttribute('sizes', '100vw');
                }
            });
        }
    })();

    // === Prefetch on link hover ===
    // When user hovers a story link, prefetch the article HTML
    (function() {
        var prefetched = new Set();
        document.addEventListener('mouseover', function(e) {
            var link = e.target.closest('a[href^="/news/"]');
            if (!link) return;
            var href = link.getAttribute('href');
            if (prefetched.has(href)) return;
            prefetched.add(href);

            var hint = document.createElement('link');
            hint.rel = 'prefetch';
            hint.href = href;
            hint.as = 'document';
            document.head.appendChild(hint);
        });
    })();

    // === Debounced scroll handler for analytics ===
    // Track scroll depth for engagement metrics (future-ready)
    (function() {
        var maxDepth = 0;
        var reported = false;
        var articleBody = document.querySelector('.article-body');
        if (!articleBody) return;

        function onScroll() {
            var rect = articleBody.getBoundingClientRect();
            var viewportHeight = window.innerHeight;
            var scrolled = Math.max(0, -rect.top);
            var total = articleBody.offsetHeight;
            var pct = Math.min(100, Math.round((scrolled / total) * 100));

            if (pct > maxDepth) maxDepth = pct;

            // Report at 25%, 50%, 75%, 100%
            var thresholds = [25, 50, 75, 100];
            for (var i = 0; i < thresholds.length; i++) {
                if (maxDepth >= thresholds[i] && !reported) {
                    // Future: send to analytics endpoint
                    reported = (thresholds[i] === 100);
                    break;
                }
            }
        }

        var ticking = false;
        window.addEventListener('scroll', function() {
            if (!ticking) {
                window.requestAnimationFrame(function() {
                    onScroll();
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    })();

})();