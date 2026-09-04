/**
 * Lavisco News — Comments module
 * Handles reaction clicks within the reader comment section.
 * Comment submission itself is a plain form POST (works without JS);
 * this only progressively enhances the per-comment reaction buttons.
 */
(function() {
    'use strict';

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-reaction-type]');
        if (!btn) return;

        const wrapper = btn.closest('[data-comment-reactions]');
        const commentEl = btn.closest('[data-comment-id]');
        if (!wrapper || !commentEl) return;

        const commentId = commentEl.getAttribute('data-comment-id');
        const type = btn.getAttribute('data-reaction-type');

        btn.disabled = true;

        fetch(`/api/v1/comments/${commentId}/reactions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type }),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            btn.disabled = false;
            if (data.error) {
                console.error(data.error);
                return;
            }
            wrapper.querySelectorAll('[data-reaction-type]').forEach(function(b) {
                const t = b.getAttribute('data-reaction-type');
                const countEl = b.querySelector(`[data-count-for="${t}"]`);
                if (countEl) countEl.textContent = data.counts[t] || 0;
                b.classList.toggle('active', t === data.user_reaction);
            });
        })
        .catch(function(err) {
            btn.disabled = false;
            console.error('Comment reaction failed:', err);
        });
    });

})();
