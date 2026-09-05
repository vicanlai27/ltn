/**
 * Direct-to-Supabase upload helper.
 *
 * Uploads a File straight to Supabase Storage using a short-lived signed
 * URL, so the bytes never pass through our own serverless function --
 * Vercel caps inbound request bodies at 4.5MB regardless of anything set
 * in the Flask app, so anything routed through the server itself is
 * capped there too.
 *
 * Flow: ask the server for a signed PUT URL (tiny JSON request) -> PUT the
 * file straight to Supabase -> ask the server to "finalize" (it re-fetches
 * the file itself, an outbound call with no size limit, to generate
 * thumbnails / read audio duration exactly like the old server-side path
 * did).
 */
window.DirectUpload = (function () {
    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    async function parseErrorBody(resp) {
        try {
            var data = await resp.json();
            return data.error || ('Request failed (' + resp.status + ')');
        } catch (e) {
            return 'Request failed (' + resp.status + ')';
        }
    }

    /**
     * @param {File} file
     * @param {string} subfolder - one of "articles", "audio", "gallery"
     * @returns {Promise<{key: string, audio_duration?: number}>}
     */
    async function uploadFile(file, subfolder) {
        var signResp = await fetch('/media/sign-upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify({ filename: file.name, subfolder: subfolder }),
        });
        if (!signResp.ok) {
            throw new Error(await parseErrorBody(signResp));
        }
        var signData = await signResp.json();

        var putResp = await fetch(signData.upload_url, {
            method: 'PUT',
            headers: {
                'Content-Type': file.type || 'application/octet-stream',
                'x-upsert': 'false',
            },
            body: file,
        });
        if (!putResp.ok) {
            throw new Error('Upload to storage failed (' + putResp.status + ')');
        }

        var finalizeResp = await fetch('/media/finalize-upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify({ key: signData.key }),
        });
        if (!finalizeResp.ok) {
            throw new Error(await parseErrorBody(finalizeResp));
        }
        return await finalizeResp.json();
    }

    return { uploadFile: uploadFile };
})();
