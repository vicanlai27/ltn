# Deploying Lavisco News: GitHub → Vercel → Supabase

This app now stores **everything** — database rows and uploaded files
(images, video, audio) — in Supabase instead of local disk. That's what
makes it deployable to Vercel, whose serverless functions have no
persistent filesystem: nothing written to local disk survives past the
request that wrote it.

Read this once end-to-end before running commands — the order matters
(Supabase must exist before you can point Vercel at it).

---

## 0. What changed, in one paragraph

Database access already went through `DATABASE_URL` (SQLAlchemy), so
pointing it at Supabase Postgres instead of SQLite is a config change, not
a code change. File uploads used to be written to
`app/static/uploads/...` on local disk; they're now uploaded to a Supabase
Storage bucket via `app/services/storage_service.py`, and the database
stores a short **object key** (e.g. `articles/2026/09/ab12cd34.jpg`)
instead of a local path. Templates resolve that key to a real URL at
render time with the `media_url()` helper. Nothing about how you use the
admin/newsroom upload forms changes — this is all internal plumbing.

---

## 1. Push the code to GitHub

```bash
cd lavisco-news
git init                                  # if not already a repo
git add .
git commit -m "Restructure for Supabase + Vercel"
git branch -M main
git remote add origin https://github.com/<you>/lavisco-news.git
git push -u origin main
```

`.vercelignore` already excludes `instance/`, `app/static/uploads/`, and
`.env` — don't remove those exclusions, and don't commit `.env` (commit
`.env.example` instead, which is safe — it has no real secrets).

---

## 2. Set up Supabase

### 2.1 Create the project
1. [supabase.com](https://supabase.com) → **New project**.
2. Pick a region close to your users (this becomes part of your DB host
   and Storage URL).
3. Set a strong database password — you'll need it in a moment.

### 2.2 Get the database connection string
**Project Settings → Database → Connection string → URI.**

Supabase gives you two relevant variants:
- **Direct connection** (port `5432`) — fine for local development and for
  running migrations from your own machine.
- **Transaction pooler** (port `6543`, host has `pooler` in it) — **use
  this one for `DATABASE_URL` on Vercel.** Serverless functions open a new
  DB connection on every cold start; without pgbouncer's transaction
  pooling you'll exhaust Supabase's connection limit under any real
  traffic. `app/config.py`'s `ProductionConfig` is already set up to pair
  correctly with the pooler (`NullPool` + `sslmode=require`).

Either way, the string looks like:
```
postgresql://postgres.xxxxxxxxxxxx:YOUR-PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
```
(Supabase sometimes shows `postgres://` — the app normalizes that to
`postgresql://` automatically, so either form works.)

### 2.3 Create the schema
Run migrations **from your own machine**, pointed at Supabase — Vercel's
serverless functions can't run one-off commands like `flask db upgrade`.

```bash
cd lavisco-news
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set DATABASE_URL to Supabase's *direct* connection string
# (port 5432) for this step — migrations work better on the direct
# connection than through the pooler.

flask db init            # only if there's no migrations/ folder yet
flask db migrate -m "initial schema"
flask db upgrade
```

Re-run `flask db upgrade` (pointed at Supabase) any time you change a
model and generate a new migration — same workflow as before, just against
a remote database now.

### 2.4 Create the Storage bucket
**Storage → New bucket** in the Supabase dashboard:
- Name: `media` (matches `SUPABASE_STORAGE_BUCKET` in `.env.example` — use
  a different name if you like, just keep the env var in sync).
- **Public bucket: ON.** The app builds public URLs directly
  (`.../storage/v1/object/public/media/...`); if you'd rather keep the
  bucket private, you'll need to switch `storage_service.get_public_url()`
  to issue signed URLs instead (a small change, not covered by this
  default setup).

No folder structure to create manually — `media_service.py` creates
`{subfolder}/{year}/{month}/...` keys on the fly as things get uploaded.

### 2.5 Get your Storage API credentials
**Project Settings → API:**
- **Project URL** → `SUPABASE_URL`
- **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`

The service_role key bypasses Row Level Security and can read/write/delete
any object in the bucket — that's intentional (the Flask backend is the
only thing that should ever touch Storage directly), but it means this key
is as sensitive as a database password. It only ever goes into a Vercel
**Environment Variable**, never into client-side code, never committed.

---

## 3. Deploy to Vercel

### 3.1 Import the project
[vercel.com/new](https://vercel.com/new) → import the GitHub repo. Vercel
will detect `vercel.json` and use the Python builder automatically
(`api/index.py` is the entrypoint — see below for how that works).

### 3.2 Set environment variables
**Project Settings → Environment Variables** — add everything from
`.env.example` with real values, at minimum:

| Variable | Value |
|---|---|
| `SECRET_KEY` | a long random string (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `SESSION_HASH_SALT` | another random string |
| `DATABASE_URL` | Supabase **pooler** connection string (port 6543) |
| `SUPABASE_URL` | from step 2.5 |
| `SUPABASE_SERVICE_ROLE_KEY` | from step 2.5 |
| `SUPABASE_STORAGE_BUCKET` | `media` (or whatever you named it) |
| `FLASK_ENV` | `production` (already set by `vercel.json`, but fine to set explicitly too) |

Mail (`MAIL_*`) and YouTube (`YOUTUBE_*`) vars are optional — only set
them if you use those features.

### 3.3 Deploy
Click **Deploy**. Vercel installs `requirements.txt` and builds
`api/index.py` as a Python serverless function; `vercel.json` routes every
request to it, so Flask's own routing (including the `/static/...` route)
handles everything.

### 3.4 Verify
- Visit the deployed URL — homepage should render.
- Log into `/admin/` and upload an image somewhere (an article's featured
  image is an easy test). If it appears correctly, Supabase Storage is
  wired up right — you can also check **Storage → media** in the Supabase
  dashboard and see the object land under e.g. `articles/2026/09/...`.
- Hit `/api/v1/health` — should return a 200.

---

## 4. How requests, database, and files fit together

```
Browser
  │
  ▼
Vercel (api/index.py, Flask app, serverless)
  │                              │
  ▼                              ▼
Supabase Postgres          Supabase Storage
(via DATABASE_URL,         (via SUPABASE_URL +
 pgbouncer pooler)          service_role key,
                             REST API)
```

- **Reads/writes to the database** go through SQLAlchemy exactly as
  before — only the connection string changed.
- **File uploads** (`save_upload()` in `app/services/media_service.py`)
  read the uploaded bytes, generate WebP thumbnails in memory (no temp
  files), and PUT everything to Supabase Storage over HTTPS. The function
  returns a storage key, which is what gets saved in the relevant DB
  column (`featured_image`, `logo`, `photo`, `video_url`, etc.) — same as
  a local path used to be saved there.
- **Rendering a file** — templates call `{{ media_url(some_key) }}`
  (registered as a Jinja global in `app/__init__.py`), which turns the key
  into `https://<project>.supabase.co/storage/v1/object/public/media/...`.
  The browser then fetches the file straight from Supabase's CDN, not
  through your Vercel function.

---

## 5. Local development after this change

You have two options, either works:

**A. Keep using local SQLite + local disk** (fastest for UI-only work):
leave `DATABASE_URL` unset in `.env` — `DevelopmentConfig` falls back to
`instance/lavisco.db`. However, `media_service.py` now *always* uploads to
Supabase Storage regardless of `FLASK_ENV`, so you still need valid
`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` in `.env` for any upload-related
feature to work locally. If you don't set them, everything except file
uploads works fine (you'll get a clear `StorageError` if you try to
upload without credentials configured).

**B. Develop against Supabase directly** (closest to production): set
`DATABASE_URL` in `.env` to Supabase's *direct* connection string (port
5432 — the pooler isn't necessary for a single local dev process) plus the
`SUPABASE_*` Storage vars. Run `flask run` as usual.

---

## 6. Moving existing local uploads to Supabase (if you have any)

If your current SQLite database has rows pointing at
`static/uploads/...` paths from before this restructure, those references
won't resolve through `media_url()` (Supabase Storage doesn't have those
files). Two ways to handle it:

- **Start fresh** (simplest): re-upload media through the admin/newsroom
  forms after deploying — every new upload goes to Supabase automatically.
- **Migrate old files**: write a one-off script that reads each affected
  model, opens the old local file from `app/static/uploads/...`, calls
  `storage_service.upload_bytes(new_key, data)` for it and its thumbs, and
  updates the DB column to the new key. Ask if you'd like this script
  written out — it's a straightforward loop over the same models
  `seed_media.py` already touches (`Gallery`, `GalleryImage`, `Video`,
  `PodcastEpisode`, plus `Article.featured_image`, profile photos, logos,
  etc.), just not included by default since it depends on which rows you
  actually have.

---

## 7. Things worth knowing about this setup

- **Rate limiting** (`Flask-Limiter`) uses in-memory storage by default,
  which resets on every cold start and isn't shared across concurrent
  Vercel instances — so it's a soft guard in production, not a hard one.
  Fine for now; point `RATELIMIT_STORAGE_URI` at a shared store (e.g.
  Upstash Redis, which pairs naturally with Vercel) if you need real
  cross-instance limits later.
- **Cold starts**: the first request after idle time will be slower
  (new Postgres connection + Python import). Subsequent requests within
  the same warm instance are fast.
- **Static assets** (`app/static/css`, `/js`, `icon.png`) are currently
  served by Flask itself through the same serverless function, per
  `vercel.json`'s catch-all route. That's correct and simple; if you want
  faster static delivery later, Vercel can serve `app/static/` directly
  via its own CDN with a small `vercel.json` route change — not necessary
  to get this working, just a possible follow-up optimization.
- **Secrets**: `SECRET_KEY`, `SESSION_HASH_SALT`, `SUPABASE_SERVICE_ROLE_KEY`,
  and `DATABASE_URL` should only ever live in Vercel's Environment
  Variables and your local `.env` (gitignored) — never in code or
  `vercel.json`.
