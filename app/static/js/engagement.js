/**
 * Lavisco News — Engagement module
 * Handles poll voting, share tracking, and Instagram share modal.
 * Progressive enhancement: core content works without JS.
 */

(function() {
    'use strict';

    // Guard against double-init: this file can legitimately get included
    // twice on one page (e.g. a poll card's own <script> plus a page-level
    // <script> tag both reference it), and re-running would double-bind
    // every click handler below (double vote submits, double share counts).
    if (window.__laviscoEngagementInit) return;
    window.__laviscoEngagementInit = true;

    // === Poll Voting ===
    document.querySelectorAll('[data-poll-form]').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const card = form.closest('[data-poll-id]');
            const pollId = card.getAttribute('data-poll-id');
            const inputs = form.querySelectorAll('input[name="option"]:checked');

            if (inputs.length === 0) {
                alert('Please select an option');
                return;
            }

            const optionIds = Array.from(inputs).map(i => parseInt(i.value));

            form.querySelector('button[type="submit"]').disabled = true;

            fetch(`/api/v1/polls/${pollId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ option_ids: optionIds }),
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    form.querySelector('button[type="submit"]').disabled = false;
                    return;
                }
                renderPollResults(card, data);
            })
            .catch(err => {
                console.error('Poll vote failed:', err);
                form.querySelector('button[type="submit"]').disabled = false;
            });
        });
    });

    function renderPollResults(card, data) {
        const form = card.querySelector('[data-poll-form]');
        const results = card.querySelector('.poll-card__results');
        if (!form || !results) return;

        form.hidden = true;
        results.hidden = false;

        // Clear existing results
        results.innerHTML = '';

        data.options.forEach(opt => {
            const row = document.createElement('div');
            row.className = 'poll-card__result-row';
            row.innerHTML = `
                <div class="poll-card__result-label">${escapeHtml(opt.label)}</div>
                <div class="poll-card__result-bar">
                    <div class="poll-card__result-fill" style="width: ${opt.pct}%"></div>
                </div>
                <div class="poll-card__result-pct">${opt.pct}%</div>
            `;
            results.appendChild(row);
        });

        const total = document.createElement('div');
        total.className = 'poll-card__total';
        total.textContent = `${data.total_votes} vote${data.total_votes !== 1 ? 's' : ''}`;
        results.appendChild(total);
    }

    // === Share Tracking ===
    document.querySelectorAll('[data-share-track]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const articleId = btn.getAttribute('data-article-id');
            const platform = btn.getAttribute('data-platform');
            if (!articleId || !platform) return;

            fetch(`/api/v1/articles/${articleId}/share`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform }),
            }).catch(() => {}); // Silent fail — don't block the share
        });
    });

    // Instagram share button
    document.querySelectorAll('[data-ig-share]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (typeof window.openInstagramShare === 'function') {
                window.openInstagramShare();
            }
        });
    });

    // === Utility ===
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();