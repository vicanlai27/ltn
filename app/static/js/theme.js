/**
 * Lavisco News — Theme module
 * Handles dark mode switching with system preference detection and persistence.
 * Prevents flash of unstyled content (FOUC) via inline script in <head>.
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'lavisco-theme';

    function getStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'system';
        } catch (e) {
            return 'system';
        }
    }

    function getEffectiveTheme() {
        var stored = getStoredTheme();
        return stored === 'system' ? getSystemPreference() : stored;
    }

    function setStoredTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // Storage unavailable — fail silently
        }
    }

    function getSystemPreference() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const effectiveTheme = theme === 'system' ? getSystemPreference() : theme;
        if (effectiveTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }

    function initThemeSwitcher() {
        const toggle = document.getElementById('theme-toggle');
        if (!toggle) return;

        // Set initial title based on current theme
        updateToggleTitle();

        toggle.addEventListener('click', function() {
            // Simple light <-> dark toggle, based on the theme currently
            // in effect (which may have come from the system preference).
            const next = getEffectiveTheme() === 'dark' ? 'light' : 'dark';

            setStoredTheme(next);
            applyTheme(next);
            updateToggleTitle();
        });

        // Listen for system preference changes (only matters if user chose 'system')
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            if (getStoredTheme() === 'system') {
                applyTheme('system');
            }
        });
    }

    function updateToggleTitle() {
        const toggle = document.getElementById('theme-toggle');
        if (!toggle) return;

        const label = getEffectiveTheme() === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
        toggle.setAttribute('aria-label', label);
        toggle.setAttribute('title', label);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initThemeSwitcher);
    } else {
        initThemeSwitcher();
    }

    // Apply theme immediately (in case this script loads after DOM)
    applyTheme(getStoredTheme());

})();