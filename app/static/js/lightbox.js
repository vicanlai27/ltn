/**
 * Lavisco News — Lightbox module
 * Keyboard + touch + zoom image viewer.
 */
(function() {
    'use strict';

    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    const img = lightbox.querySelector('[data-lightbox-img]');
    const caption = lightbox.querySelector('[data-lightbox-caption]');
    const counter = lightbox.querySelector('[data-lightbox-counter]');
    const prevBtn = lightbox.querySelector('[data-lightbox-prev]');
    const nextBtn = lightbox.querySelector('[data-lightbox-next]');
    const closeBtn = lightbox.querySelector('[data-lightbox-close]');
    const zoomBtn = lightbox.querySelector('[data-lightbox-zoom]');
    const spinner = lightbox.querySelector('[data-lightbox-spinner]');

    let images = [];
    let currentIndex = 0;
    let isZoomed = false;
    let touchStartX = 0;
    let touchEndX = 0;

    function open(index) {
        currentIndex = index;
        isZoomed = false;
        img.classList.remove('zoomed');
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
        show();
    }

    function close() {
        lightbox.hidden = true;
        document.body.style.overflow = '';
        img.classList.remove('zoomed');
        isZoomed = false;
    }

    function show() {
        const item = images[currentIndex];
        if (!item) return;

        spinner.hidden = false;
        img.style.opacity = '0';

        const newImg = new Image();
        newImg.onload = function() {
            img.src = item.src;
            img.alt = item.alt || '';
            img.style.opacity = '1';
            spinner.hidden = true;
        };
        newImg.onerror = function() {
            spinner.hidden = true;
            img.style.opacity = '1';
        };
        newImg.src = item.src;

        caption.textContent = item.caption || '';
        counter.textContent = `${currentIndex + 1} / ${images.length}`;

        prevBtn.disabled = currentIndex === 0;
        nextBtn.disabled = currentIndex === images.length - 1;
    }

    function next() {
        if (currentIndex < images.length - 1) {
            currentIndex++;
            show();
        }
    }

    function prev() {
        if (currentIndex > 0) {
            currentIndex--;
            show();
        }
    }

    function toggleZoom() {
        isZoomed = !isZoomed;
        img.classList.toggle('zoomed', isZoomed);
    }

    // Collect all lightbox triggers on the page
    function collectImages() {
        images = [];
        document.querySelectorAll('[data-lightbox]').forEach((el, idx) => {
            el.setAttribute('data-lightbox-index', idx);
            images.push({
                src: el.getAttribute('href') || el.getAttribute('data-lightbox'),
                alt: el.getAttribute('data-lightbox-alt') || '',
                caption: el.getAttribute('data-lightbox-caption') || '',
            });
        });
    }

    // Event delegation for triggers
    document.addEventListener('click', function(e) {
        const trigger = e.target.closest('[data-lightbox]');
        if (!trigger) return;
        e.preventDefault();
        collectImages();
        const idx = parseInt(trigger.getAttribute('data-lightbox-index'), 10);
        open(idx);
    });

    // Controls
    closeBtn.addEventListener('click', close);
    prevBtn.addEventListener('click', prev);
    nextBtn.addEventListener('click', next);
    zoomBtn.addEventListener('click', toggleZoom);
    img.addEventListener('click', toggleZoom);

    // Click backdrop to close
    lightbox.addEventListener('click', function(e) {
        if (e.target === lightbox || e.target.classList.contains('lightbox__stage')) {
            close();
        }
    });

    // Keyboard
    document.addEventListener('keydown', function(e) {
        if (lightbox.hidden) return;
        switch (e.key) {
            case 'Escape': close(); break;
            case 'ArrowLeft': prev(); break;
            case 'ArrowRight': next(); break;
            case ' ': e.preventDefault(); toggleZoom(); break;
        }
    });

    // Touch swipe
    lightbox.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    lightbox.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        const diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) next();
            else prev();
        }
    }, { passive: true });

})();