# Lavisco Editorial — Debug Pass (2026-09-01)

## Issues addressed

1. **Legacy gallery URL compatibility**
   - `/media/gallery/<slug>` remains a supported compatibility URL for published galleries.
   - Canonical gallery URLs are under `/campus/gallery/<slug>`.
   - Admin gallery "View" links now point directly to the canonical route.
   - Gallery API responses now return the canonical `/campus/gallery/<slug>` URL.

2. **YouTube/Lavisco TV resilience**
   - YouTube channel ID can now be supplied with `YOUTUBE_CHANNEL_ID`.
   - Cache writes are best-effort and roll back safely if the database is temporarily unavailable.
   - Live detection accepts both `isLive` and `isLiveNow` JSON flags with optional whitespace/case differences.
   - Existing stale-cache fallback remains in place, so YouTube/DNS failures do not take down the page.

3. **Development server safety**
   - `run.py` no longer enables Flask debug mode by default.
   - Set `FLASK_DEBUG=1` when interactive debugging is explicitly desired.

## Important: the `/media/gallery/kali` 404

A 404 for a gallery slug means there is no **published** gallery matching that slug in the database. The uploaded image file alone does not create a Gallery database record.

The fixed application deliberately keeps drafts/non-existent galleries private. To make `/media/gallery/kali` resolve, create/publish a gallery whose slug is `kali` in **Admin → Galleries**, or use the slug shown for an existing published gallery.

The provided development database contained no `galleries` row for `kali`, so manufacturing one during this debug pass would create fake editorial data. No existing files or database records were deleted.

## Verification

- Python source files were compiled with `compileall`.
- The original project files were retained; only targeted fixes and this diagnostic note were added.

---

# Debug Pass 2 (2026-09-04) — the `/auth/login` 500

## Root cause

`migrations/versions/` was **empty** — `alembic.ini`, `env.py`, and
`script.py.mako` were all present and correctly wired to the app's
models, but no revision file had ever been generated. Running
`flask db upgrade` against that state is a silent no-op: it reports
success but creates zero tables.

That means the Supabase Postgres database this project points at
(`DATABASE_URL` in `.env`) never had its schema created through the
project's own migration flow. The moment `/auth/login` runs its first
query (`User.query.filter(...)` inside `AuthService.authenticate`),
Postgres returns `relation "users" does not exist`, which is an
unhandled exception → Flask's `500` handler (`errors/500.html`).
Every other page that touches the database (which, via the
`inject_nav_categories` context processor, is *every* page) would
fail the same way — login just happens to be the first thing most
people try.

This was confirmed by reproducing the whole request cycle locally
end-to-end with `Flask`'s test client, `PROPAGATE_EXCEPTIONS=True`,
and a from-scratch SQLite database:
- With a plain `db.create_all()` (bypassing migrations entirely, the
  way `seed.py` idempotently does for local dev), login, 2FA-less
  and 2FA flows, the post-login redirect, and every one of this
  project's 168 registered routes rendered cleanly (`200`/`302`, no
  exceptions) — both signed out and as `super_admin`.
- With **only** `flask db upgrade` (no `db.create_all()`), against
  the *empty* `migrations/versions/` this zip originally shipped
  with, the users table was never created and the same login flow
  fails exactly like the reported 500 — reproducing the bug
  precisely.

## Fix

Generated the missing baseline revision from the current models:
`migrations/versions/3ae86e2b18c1_baseline_schema.py`
(`flask db migrate -m "baseline schema"`, reviewed, then applied
with `flask db upgrade` against a throwaway SQLite DB to confirm it
builds every table — `users`, `activity_logs`, `articles`, and the
rest — with no errors).

**This does not touch your live Supabase database.** To pick up the
fix in the environment `DATABASE_URL` in `.env` points at, run once:

```
flask db upgrade
```

That will create every table your models define (`users` included)
without dropping or altering anything that's already there — if some
tables already exist from a previous manual `supabase_schema.sql`
run, Alembic will simply record this revision as applied going
forward (see note below).

If you're not sure whether some tables already exist in that
database and want to avoid `CREATE TABLE` erroring on a collision,
run `flask db stamp 3ae86e2b18c1` instead of `upgrade` to mark the
baseline as already-applied without re-running the DDL, then confirm
with `flask db current`. From there on, `flask db migrate` will
correctly generate real incremental migrations for any future model
changes, instead of the empty-folder no-op this project started
from.

## Full route/link audit (same pass)

Every one of the app's 168 registered routes was crawled with the
Flask test client — all static-path `GET` routes both signed out and
as `super_admin`, representative dynamic-slug routes (articles,
categories, clubs, etc.) with real seeded data, and the 404 path for
each of those with a nonexistent slug. Every `url_for(...)` reference
across `app/templates`, `app/routes`, `app/services`, and `app/utils`
(153 call sites, including the dynamic
`url_for('campus.' ~ person_type ~ '_show', ...)` builder in
`campus/people_index.html`) was cross-checked against the app's
actual `url_map` — no dangling endpoint references. No 500s, no
`BuildError`s, no broken links were found anywhere in the route
surface once the database has a schema to query against.

## Verification

- `python -m compileall app migrations run.py seed_media.py api` — clean.
- Full request-cycle regression (all 168 routes, signed out + as
  `super_admin`, plus comment/reaction/admin-article-creation POSTs)
  against a freshly migrated SQLite database — all passed.
- No existing files were deleted; only the missing migration and
  this note were added.
