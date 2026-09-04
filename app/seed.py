"""
Seed script for Lavisco News development data.
Run: python seed.py
"""

from app import create_app
from app.extensions import db
from app.models.user import User, AuthorProfile
from app.models.content import Category, Article, Tag
from app.models.campus import House, Club, CampusEvent
from app.models.sports import Sport, Team, Fixture
from app.models.people import StudentProfile, StaffProfile, AlumniProfile
from app.models.editorial import Theme
from app.models.system import SiteSetting
from app.utils.security import utcnow, slugify
from app.services.calendar_theme_service import seed_calendar_themes
from datetime import datetime, timezone, timedelta


def seed():
    app = create_app()
    with app.app_context():
        print("Seeding Lavisco News...")
        # Ensure the schema exists before the idempotent seed queries run.
        # Production installations should use their normal Flask-Migrate flow.
        db.create_all()

        # Create super_admin if not exists
        if not User.query.filter_by(role=User.ROLE_SUPER_ADMIN).first():
            admin = User(
                username="superadmin",
                email="admin@lavisco.news",
                role=User.ROLE_SUPER_ADMIN,
                account_status=User.STATUS_ACTIVE,
                verified_at=utcnow(),
            )
            admin.set_password("super2026")
            db.session.add(admin)
            db.session.commit()
            print("✓ Created super_admin (username: superadmin, password: super2026)")

        admin = User.query.filter_by(role=User.ROLE_SUPER_ADMIN).first()

        # Create categories
        cats = [
            ("Campus News", "campus-news", "School developments and announcements"),
            ("Politics", "politics", "Ugandan and East African politics"),
            ("Business", "business", "Markets, companies, and the economy"),
            ("Sports", "sports", "Local, national, and international sports"),
            ("Entertainment", "entertainment", "Music, film, culture"),
            ("Technology", "technology", "Tech news and innovation"),
            ("Lifestyle", "lifestyle", "Living, wellness, trends"),
            ("Opinion", "opinion", "Commentary and analysis"),
            ("Viral & Culture", "viral-culture", "What's trending online"),
        ]
        for name, slug, desc in cats:
            if not Category.query.filter_by(slug=slug).first():
                db.session.add(Category(name=name, slug=slug, description=desc))
        db.session.commit()
        print(f"✓ Seeded {len(cats)} categories")

        # Create one published sample article per category, so every
        # homepage section (and each /category/<slug> page) has something
        # to preview instead of showing an empty state. Safe to re-run:
        # skipped per-article if a matching slug already exists.
        sample_articles = [
            dict(
                title="Holy Cross Lake View Hosts Inter-House Debate Finals",
                category_slug="campus-news",
                excerpt="Four houses faced off in the season's closing debate, drawing the largest crowd yet.",
                body="The inter-house debate finals brought students, staff, and parents together for an evening of sharp arguments and sharper rebuttals. Judges praised the standard of research and delivery across all four houses, with the winning team crediting weeks of after-class preparation.",
                is_campus=True,
                is_featured=True,
                is_editors_pick=True,
            ),
            dict(
                title="Uganda's Parliament Debates New Education Funding Bill",
                category_slug="politics",
                excerpt="Lawmakers weighed proposals that could reshape how secondary schools are funded nationwide.",
                body="The bill, tabled this week, proposes changes to how capitation grants are calculated for secondary schools. Supporters argue it closes funding gaps for rural institutions; critics want clearer accountability measures before it passes.",
                is_breaking=True,
            ),
            dict(
                title="Local SACCOs See Growth as Youth Embrace Savings Culture",
                category_slug="business",
                excerpt="Savings and credit cooperatives report rising youth membership across the region.",
                body="Several community SACCOs report double-digit growth in youth membership this year, a shift finance officers attribute to school-based financial literacy programs and easier mobile-money integration.",
            ),
            dict(
                title="School Football Team Advances to Regional Finals",
                category_slug="sports",
                excerpt="A last-minute goal sealed the win and a place in next month's regional finals.",
                body="The team's disciplined second-half performance turned the match around after a scoreless first half. Coaches say the squad's focus now shifts to conditioning ahead of the regional finals.",
                is_featured=True,
            ),
            dict(
                title="Wanyange Talent Show Set to Return This Term",
                category_slug="entertainment",
                excerpt="Auditions open next week for the school's annual talent showcase.",
                body="After a well-received run last year, the talent show returns with expanded categories including spoken word and dance. Organizers expect this year's lineup to be the largest yet.",
            ),
            dict(
                title="Students Build Solar-Powered Charging Station",
                category_slug="technology",
                excerpt="A science club project now powers device charging for the whole dormitory block.",
                body="The Science Club's solar charging station, built from salvaged panels and a repurposed battery bank, now serves an entire dormitory block. The team plans to document the build for other schools to replicate.",
            ),
            dict(
                title="Balancing Boarding School Life and Wellness",
                category_slug="lifestyle",
                excerpt="Students and counselors share practical routines for managing boarding-school stress.",
                body="Between early wake-ups, prep sessions, and extracurriculars, boarding life leaves little room for rest. Counselors shared simple routines students can build into an already packed schedule.",
            ),
            dict(
                title="Why Student Journalism Matters More Than Ever",
                category_slug="opinion",
                excerpt="A case for why campus newsrooms deserve more support, not less.",
                body="Student newsrooms are often the first place young writers learn to verify a claim, weigh a source, and own a correction. That training matters well beyond the school gates, and it deserves more institutional support than it typically gets.",
                content_type=Article.TYPE_OPINION,
            ),
            dict(
                title="Campus TikTok Trend Has Everyone Talking",
                category_slug="viral-culture",
                excerpt="A dance challenge filmed in the school courtyard has racked up thousands of views.",
                body="What started as a between-classes joke has turned into the school's most-shared video this term, with students from neighboring schools filming their own versions.",
            ),
        ]

        articles_created = 0
        for i, data in enumerate(sample_articles):
            slug = slugify(data["title"])
            if Article.query.filter_by(slug=slug).first():
                continue
            category = Category.query.filter_by(slug=data["category_slug"]).first()
            article = Article(
                title=data["title"],
                slug=slug,
                excerpt=data["excerpt"],
                body=data["body"],
                category_id=category.id if category else None,
                author_id=admin.id if admin else None,
                content_type=data.get("content_type", Article.TYPE_NEWS),
                status=Article.STATUS_PUBLISHED,
                is_audited=True,
                audited_by_id=admin.id if admin else None,
                audited_at=utcnow(),
                is_campus=data.get("is_campus", False),
                is_featured=data.get("is_featured", False),
                is_breaking=data.get("is_breaking", False),
                is_editors_pick=data.get("is_editors_pick", False),
                published_at=utcnow() - timedelta(hours=i * 3),
            )
            db.session.add(article)
            articles_created += 1
        db.session.commit()
        print(f"✓ Seeded {articles_created} sample articles")

        # Create clubs
        clubs_data = [
            ("Debate Club", "debate-club", "Public speaking and critical thinking"),
            ("Science Club", "science-club", "Exploring STEM through experiments"),
            ("Environmental Club", "environmental-club", "Sustainability and conservation"),
        ]
        for name, slug, desc in clubs_data:
            if not Club.query.filter_by(slug=slug).first():
                db.session.add(Club(name=name, slug=slug, description=desc, leader_name=f"Prefect {name.split()[0]}"))
        db.session.commit()
        print(f"✓ Seeded {len(clubs_data)} clubs")

        # Create sports
        if not Sport.query.filter_by(slug='football').first():
            db.session.add(Sport(name="Football", slug="football", description="The beautiful game"))
            db.session.add(Sport(name="Netball", slug="netball", description="Fast-paced team sport"))
            db.session.add(Sport(name="Volleyball", slug="volleyball", description="Indoor and beach volleyball"))
            db.session.commit()
        print("✓ Seeded sports")

        # Seed calendar themes
        created = seed_calendar_themes()
        print(f"✓ Seeded {created} calendar themes")

        # Create default site settings
        defaults = {
            "footer_credit": "Made By: CKS-Tech & D@in Corp. All rights reserved {current_year}",
            "site_description": "News. Context. Truth. A digital newsroom born at Holy Cross Lake View Wanyange.",
        }
        for key, value in defaults.items():
            if not SiteSetting.query.filter_by(key=key).first():
                db.session.add(SiteSetting(key=key, value=value))
        db.session.commit()
        print("✓ Seeded site settings")

        print("\n✅ Seed complete!")
        print("\nNext steps:")
        print("  1. Run: flask run")
        print("  2. Visit: http://127.0.0.1:5000/auth/login")
        print("  3. Log in as: superadmin / super2026")
        print("  4. Change your password immediately!")


if __name__ == "__main__":
    seed()
