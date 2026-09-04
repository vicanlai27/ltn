/**
 * Lavisco News — Audio player module
 * Inline audio player with seek, skip, speed control.
 */
(function() {
    'use strict';

    document.querySelectorAll('[data-audio-player]').forEach(function(player) {
        const src = player.getAttribute('data-src');
        if (!src) return;

        const audio = new Audio(src);
        audio.preload = 'metadata';

        const playBtn = player.querySelector('[data-audio-play]');
        const iconPlay = playBtn.querySelector('.audio-player__icon-play');
        const iconPause = playBtn.querySelector('.audio-player__icon-pause');
        const progress = player.querySelector('[data-audio-progress]');
        const fill = player.querySelector('[data-audio-fill]');
        const timeEl = player.querySelector('[data-audio-time]');
        const speedSelect = player.querySelector('[data-audio-speed]');
        const skipBack = player.querySelector('[data-audio-skip-back]');
        const skipForward = player.querySelector('[data-audio-skip-forward]');

        function formatTime(seconds) {
            if (isNaN(seconds)) return '0:00';
            const m = Math.floor(seconds / 60);
            const s = Math.floor(seconds % 60);
            return `${m}:${s.toString().padStart(2, '0')}`;
        }

        function togglePlay() {
            if (audio.paused) {
                audio.play().catch(err => console.warn('Audio play failed:', err));
            } else {
                audio.pause();
            }
        }

        playBtn.addEventListener('click', togglePlay);

        audio.addEventListener('play', () => {
            iconPlay.hidden = true;
            iconPause.hidden = false;
            playBtn.setAttribute('aria-label', 'Pause');
        });

        audio.addEventListener('pause', () => {
            iconPlay.hidden = false;
            iconPause.hidden = true;
            playBtn.setAttribute('aria-label', 'Play');
        });

        audio.addEventListener('timeupdate', () => {
            if (audio.duration) {
                const pct = (audio.currentTime / audio.duration) * 100;
                fill.style.width = pct + '%';
                timeEl.textContent = formatTime(audio.currentTime) + ' / ' + formatTime(audio.duration);
            }
        });

        audio.addEventListener('ended', () => {
            fill.style.width = '0%';
            audio.currentTime = 0;
        });

        progress.addEventListener('click', function(e) {
            if (!audio.duration) return;
            const rect = progress.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            audio.currentTime = pct * audio.duration;
        });

        skipBack.addEventListener('click', () => {
            audio.currentTime = Math.max(0, audio.currentTime - 15);
        });

        skipForward.addEventListener('click', () => {
            audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 15);
        });

        speedSelect.addEventListener('change', function() {
            audio.playbackRate = parseFloat(this.value);
        });

        // Keyboard: space to play/pause when focused
        player.setAttribute('tabindex', '0');
        player.addEventListener('keydown', function(e) {
            if (e.key === ' ' || e.key === 'k') {
                e.preventDefault();
                togglePlay();
            }
        });
    });

})();