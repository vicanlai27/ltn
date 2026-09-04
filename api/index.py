"""
Vercel entrypoint.

Vercel's Python runtime (@vercel/python) looks for a WSGI-compatible
`app` object in this file and calls it directly -- no extra server code
needed. Locally, this project still runs the normal way: `python run.py`.

FLASK_ENV is set to "production" via vercel.json's env block, which
selects ProductionConfig (Supabase Postgres + Supabase Storage, secure
cookies). See DEPLOYMENT.md for the full setup.
"""
import os
import sys

# Make the project root importable when this file is executed from /api.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "production"))
