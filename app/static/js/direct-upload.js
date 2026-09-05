/**
 * Direct-to-Supabase upload helper.
 *
 * Uploads a File straight to Supabase Storage using a short-lived signed
 * upload token, so the bytes never pass through our own serverless
 * function -- Vercel caps inbound request bodies at 4.5MB regardless of
 * anything set in the Flask app, so anything routed through the server
 * itself is capped there too.
 *
 * The actual upload step uses the official supabase-js SDK
 * (uploadToSignedUrl) rather than a hand-built fetch() PUT: a raw
 * cross-origin PUT to Supabase's signed-upload endpoint has a documented
 * CORS-preflight rough edge (github.com/supabase/supabase-js/issues/1662),
 * and the SDK is the maintained, tested way to call it correctly.
 *
 * Requires the supabase-js UMD build to be loaded on the page BEFORE this
 * file, e.g.:
 *   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
 *   <script src="{{ url_for('static', filename='js/direct-upload.js') }}"></script>
 *
 * Flow: ask the server for a signed upload token (tiny JSON request) ->
 * SDK uploads the file straight to Supabase -> ask the server to
 * "finalize" (it re-fetches the file itself, an outbound call with no
 * size limit, to generate thumbnails / read audio duration exactly like
 * the old server-side path did).
 */
window.DirectUpload = (function () {
    var _client = null;

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    function metaContent(name) {
        var meta = document.querySelector('meta[name="' + name + '"]');
        return meta ? meta.content : '';
    }

    function getClient() {
        if (_client) return _client;

        var url = metaContent('supabase-url');
        var anonKey = metaContent('supabase-anon-key');
        if (!url || !anonKey) {
            throw new Error('Supabase config missing (supabase-url / supabase-anon-key meta tags)');
        }
        if (!window.supabase || !window.supabase.createClient) {
            throw new Error('supabase-js SDK not loaded -- add the CDN <script> before direct-upload.js');
        }

        _client = window.supabase.createClient(url, anonKey);
        return _client;
    }

    function bucketName() {
        return metaContent('supabase-bucket') || 'media';
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
        var signData = await signResp.json(); // { key, token }

        var client = getClient();
        var uploadResult = await client.storage
            .from(bucketName())
            .uploadToSignedUrl(signData.key, signData.token, file);

        if (uploadResult.error) {
            throw new Error(uploadResult.error.message || 'Upload to storage failed');
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
