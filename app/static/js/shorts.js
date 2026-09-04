/**
 * Lavisco News — Shorts module
 * Vertical snap-scroll feed with IntersectionObserver autoplay.
 */
(function() {
    'use strict';

    // Individual short player controls
    document.querySelectorAll('[data-short-player]').forEach(function(player) {
        const video = player.querySelector('.short-player__video');
        const muteBtn = player.querySelector('[data-short-mute]');
        const iconMuted = muteBtn.querySelector('.short-player__icon-muted');
        const iconUnmuted = muteBtn.querySelector('.short-player__icon-unmuted');
        const playPauseBtn = player.querySelector('[data-short-playpause]');
        const ppPlay = playPauseBtn.querySelector('.short-player__pp-play');
        const ppPause = playPauseBtn.querySelector('.short-player__pp-pause');

        // Mute toggle
        muteBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            video.muted = !video.muted;
            iconMuted.hidden = !video.muted;
            iconUnmuted.hidden = video.muted;
        });

        // Play/pause toggle
        function togglePlay() {
            if (video.paused) {
                video.play().catch(() => {});
            } else {
                video.pause();
            }
        }

        playPauseBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            togglePlay();
        });

        video.addEventListener('click', togglePlay);

        video.addEventListener('play', () => {
            player.classList.remove('is-paused');
            ppPlay.hidden = true;
            ppPause.hidden = false;
        });

        video.addEventListener('pause', () => {
            player.classList.add('is-paused');
            ppPlay.hidden = false;
            ppPause.hidden = true;
        });
    });

    // Feed-level autoplay via IntersectionObserver
    const feed = document.querySelector('[data-shorts-feed]');
    if (feed && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                const player = entry.target;
                const video = player.querySelector('.short-player__video');
                if (!video) return;

                if (entry.isIntersecting && entry.intersectionRatio > 0.6) {
                    video.play().catch(() => {});
                } else {
                    video.pause();
                }
            });
        }, { threshold: [0, 0.6, 1.0] });

        feed.querySelectorAll('[data-short-player]').forEach(function(p) {
            observer.observe(p);
        });
    }

    // Share button
    document.querySelectorAll('[data-short-share]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const slug = btn.getAttribute('data-video-slug');
            const url = window.location.origin + '/shorts/' + slug;
            if (navigator.share) {
                navigator.share({ title: 'Lavisco Short', url: url }).catch(() => {});
            } else {
                navigator.clipboard.writeText(url).then(function() {
                    btn.style.background = 'var(--success)';
                    setTimeout(() => { btn.style.background = ''; }, 1500);
                });
            }
        });
    });

})();