# Lavisco News

A modern, youth-focused digital newsroom born at **Holy Cross Lake View Wanyange**, serving the school community, Uganda, East Africa, and a wider digital audience.

**Tagline:** _News. Context. Truth._

---

## Status

Core platform, editorial pipeline, campus sections, media (audio/shorts/podcasts), theming, admin console, and the newsroom contributor workspace are all in place, including full role-based dashboards and login routing for every account type.

---

## Requirements

- Python 3.12+
- pip
- (Production) PostgreSQL 14+

---

## Installation

```bash
# 1. Clone and enter the project
git clone <repo-url> lavisco-news
cd lavisco-news

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY

# 5. Initialize the database
flask db init          # only the first time
flask db migrate -m "initial schema"
flask db upgrade

# 6. (Optional) Seed development data
# python seed.py       # available in Phase 11

# 7. Run the development server
flask run
# → http://127.0.0.1:5000

## Roles, Login, and Dashboards

Every account lands on a dashboard immediately after logging in — nobody is dropped on the public homepage with nothing to do.

| Roles | Lands on | Can do |
|-------|----------|--------|
| `super_admin`, `admin`, `editor` | `/admin/` (staff console) | Manage users, categories, themes, campus data; review, audit, and publish articles |
| `teacher_editor`, `author`, `student_journalist`, `student_contributor`, `alumni_contributor` | `/newsroom/` (personal workspace) | Write articles, save drafts, submit for review, track their own article statuses |

Both consoles link back to each other where relevant (staff see a "Newsroom"-style article list; the newsroom sidebar shows a "Staff Admin Console" link for editor-and-above). A **Dashboard** button in the site header, mobile menu, and footer takes any logged-in user to the right one automatically.

### Editorial pipeline

Articles move `draft → pending_review → pending_audit → published` (or `rejected` at either review step). Separation of duties is enforced in `app/services/article_service.py`: the author, the editor who approves for audit, and the admin/editor who does the final audit must all be three different people (super_admin is exempt). Contributors submitting from `/newsroom` cannot self-publish or set curation flags (Featured / Breaking / Editor's Pick) — those stay staff-only.

## Superadmin account management

After signing in with a `super_admin` account, the application opens the
editorial dashboard automatically. To create another account, use the
**Create User** link in the dashboard sidebar or visit:

```
http://127.0.0.1:5000/admin/users/new
```

Superadmins can create every newsroom role, including admins and other
superadmins. These accounts are activated immediately. Accounts created by
regular admins require verification from **Administration → Pending Accounts**.

## Performance Checklist

Lavisco targets the following Core Web Vitals:

| Metric | Target | How we achieve it |
|--------|--------|-------------------|
| LCP    | < 2.5s | Critical CSS inlined, hero image with `fetchpriority="high"`, font preloading |
| CLS    | < 0.1  | Explicit `width`/`height` on all images, aspect-ratio containers, reserved ad space |
| INP    | < 200ms | Vanilla JS (no framework), debounced scroll handlers, passive event listeners |

### Run Lighthouse locally

```bash
# Install Lighthouse CLI
npm install -g lighthouse

# Audit the homepage
lighthouse http://127.0.0.1:5000/ --view

# Audit an article page
lighthouse http://127.0.0.1:5000/news/sample-story-0 --view
## Editorial scope

Lavisco TV News is scoped to the **editorial team and readers**. The application does not include a parent portal, school-fees portal, attendance portal, or academic-results/parent-management workflow. Campus, sports, student, staff, alumni, events and clubs are retained only as editorial content and newsroom-managed coverage areas.

### Editorial controls now available
- Article drafting, review, audit and publishing workflow
- Homepage placement/curation controls
- Special editions with article assignment
- Reader-facing scheduled announcements
- Reader reports with moderation queues
- Editorial workflow notifications
- Media management and public media APIs
- YouTube-linked articles and Lavisco TV feed integration
- Scheduled advertisement management
- Analytics dashboard and engagement tracking
