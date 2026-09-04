from datetime import datetime, timezone

from flask import (
    Blueprint, abort, render_template, request, Response, url_for, current_app,
    redirect, flash,
)
from flask_login import current_user

from app.forms.engagement import CommentForm, ReportForm
from app.models.content import Article, Category, Tag
from app.models.editorial import SpecialEdition
from app.models.media import PodcastEpisode, Video
from app.models.user import AuthorProfile
from app.repositories import homepage as home_repo
from app.repositories.articles import list_articles, get_related_articles
from app.services.article_service import (
    get_article_for_reading, increment_view, estimate_reading_time,
)
from app.services.report_service import create_report
from app.services.engagement_service import (
    post_comment, get_comments_for_article,
    get_comment_reaction_counts_bulk, get_user_comment_reactions,
)
from app.services.search_service import search_articles
from app.services.seo_service import article_meta, structured_data_article
from app.services import youtube_service
from app.utils.security import make_session_hash

public_bp = Blueprint("public", __name__)


@public_bp.context_processor
def inject_nav_categories():
    """Top navigation categories for templates."""
    categories = Category.query.filter_by(is_active=True, parent_id=None)\
        .order_by(Category.display_order.asc(), Category.name.asc()).all()
    return {
        "nav_categories": categories,
        "has_shorts": Video.query.filter(
            Video.published_at.isnot(None),
            Video.published_at <= datetime.now(timezone.utc),
            Video.duration.isnot(None),
            Video.duration <= 90,
        ).first() is not None,
        "has_podcasts": PodcastEpisode.query.filter(
            PodcastEpisode.published_at.isnot(None),
            PodcastEpisode.published_at <= datetime.now(timezone.utc),
        ).first() is not None,
        # Cached lookup (see youtube_service) — cheap even on every request,
        # drives the sitewide "LIVE" badge on the Lavisco TV nav link.
        "lavisco_tv_live": youtube_service.get_live_status(),
        "active_special_editions": SpecialEdition.query.filter_by(is_active=True).order_by(SpecialEdition.start_at.desc().nullslast(), SpecialEdition.id.desc()).limit(6).all(),
    }


# === Homepage ===

@public_bp.route("/")
def index():
    return render_template(
        "home/index.html",
        hero_primary=home_repo.hero_primary(),
        hero_secondary=home_repo.hero_secondary(),
        lavisco_tv_videos=youtube_service.get_latest_videos(limit=4),
        trending=home_repo.trending_now(),
        whats_happening=home_repo.whats_happening(),
        latest=home_repo.latest_news(),
        campus_highlights=home_repo.campus_highlights(),
        editors_choice=home_repo.editors_choice(),
        explain_this=home_repo.explain_this(),
        politics=home_repo.category_section_articles("politics"),
        business=home_repo.category_section_articles("business"),
        sports=home_repo.category_section_articles("sports"),
        entertainment=home_repo.category_section_articles("entertainment"),
        technology=home_repo.category_section_articles("technology"),
        lifestyle=home_repo.category_section_articles("lifestyle"),
        viral_culture=home_repo.category_section_articles("viral-culture"),
        opinion=home_repo.category_section_articles("opinion"),
    )


# === Articles ===

@public_bp.route("/news/<slug>")
def article(slug):
    a = get_article_for_reading(slug)
    if not a:
        abort(404)

    # Record view (anonymous, deduped)
    session_hash = make_session_hash()
    user_id = current_user.id if current_user.is_authenticated else None
    device_type = "mobile" if request.user_agent.platform in ("android", "iphone", "blackberry") else \
                  "tablet" if request.user_agent.platform in ("ipad",) else "desktop"
    increment_view(
        a, session_hash, user_id,
        referrer=request.referrer,
        device_type=device_type,
        dedup_minutes=current_app.config["VIEW_DEDUP_MINUTES"],
    )

    related = get_related_articles(a)
    reading_time = estimate_reading_time(a.body)
    meta = article_meta(a)
    schema = structured_data_article(a)

    comments = get_comments_for_article(a.id)
    comment_ids = [c.id for c in comments]
    comment_reaction_counts = get_comment_reaction_counts_bulk(comment_ids)
    user_comment_reactions = get_user_comment_reactions(comment_ids, session_hash)

    return render_template(
        "articles/show.html",
        article=a,
        related=related,
        reading_time=reading_time,
        meta=meta,
        schema=schema,
        comments=comments,
        comment_form=CommentForm(),
        report_form=ReportForm(),
        comment_reaction_counts=comment_reaction_counts,
        user_comment_reactions=user_comment_reactions,
    )


@public_bp.route("/news/<slug>/comments", methods=["POST"])
def article_post_comment(slug):
    a = get_article_for_reading(slug)
    if not a:
        abort(404)

    form = CommentForm()
    if form.validate_on_submit():
        session_hash = make_session_hash()
        user_id = current_user.id if current_user.is_authenticated else None
        try:
            post_comment(
                a.id,
                form.display_name.data,
                form.body.data,
                session_hash,
                user_id,
            )
        except ValueError as e:
            flash(str(e), "error")
        else:
            flash("Comment posted", "success")
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "error")

    return redirect(url_for("public.article", slug=slug) + "#comments")


# === Archives ===

@public_bp.route("/news/<slug>/comments/<int:comment_id>/report", methods=["POST"])
def comment_report(slug, comment_id):
    a = get_article_for_reading(slug)
    if not a: abort(404)
    from app.models.engagement import Comment
    comment = Comment.query.filter_by(id=comment_id, article_id=a.id).first()
    if not comment: abort(404)
    form = ReportForm()
    if form.validate_on_submit():
        try:
            _, created = create_report("comment", comment.id, form.reason.data, make_session_hash())
            flash("Thanks. Your report has been sent to the editorial team." if created else "You already reported this comment.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
    else:
        flash("Please provide a reason for the report.", "error")
    return redirect(url_for("public.article", slug=slug) + "#comments")


@public_bp.route("/news/<slug>/report", methods=["POST"])
def article_report(slug):
    a = get_article_for_reading(slug)
    if not a: abort(404)
    form = ReportForm()
    if form.validate_on_submit():
        try:
            _, created = create_report("article", a.id, form.reason.data, make_session_hash())
            flash("Thanks. Your report has been sent to the editorial team." if created else "You already reported this article.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
    else:
        flash("Please provide a reason for the report.", "error")
    return redirect(url_for("public.article", slug=slug) + "#article-report")


@public_bp.route("/category/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    articles = list_articles(category_slug=slug, page=page)
    return render_template("articles/category.html", category=cat, articles=articles)


@public_bp.route("/author/<slug>")
def author(slug):
    profile = AuthorProfile.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    articles = list_articles(author_slug=slug, page=page)
    return render_template("articles/author.html", profile=profile, articles=articles)


@public_bp.route("/tag/<slug>")
def tag(slug):
    t = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    articles = list_articles(tag_slug=slug, page=page)
    return render_template("articles/tag.html", tag=t, articles=articles)


# === Search ===

@public_bp.route("/editions")
def special_editions():
    editions = SpecialEdition.query.filter_by(is_active=True).order_by(SpecialEdition.start_at.desc().nullslast(), SpecialEdition.id.desc()).all()
    return render_template("articles/special_editions.html", editions=editions)


@public_bp.route("/edition/<slug>")
def special_edition(slug):
    from app.models.editorial import SpecialEdition
    edition = SpecialEdition.query.filter_by(slug=slug, is_active=True).first()
    if not edition: abort(404)
    now = datetime.now(timezone.utc)
    start = edition.start_at.replace(tzinfo=timezone.utc) if edition.start_at and edition.start_at.tzinfo is None else edition.start_at
    end = edition.end_at.replace(tzinfo=timezone.utc) if edition.end_at and edition.end_at.tzinfo is None else edition.end_at
    if start and start > now: abort(404)
    if end and end < now: abort(404)
    articles = Article.query.filter(Article.special_edition_id == edition.id, Article.status == Article.STATUS_PUBLISHED, Article.is_audited.is_(True)).order_by(Article.published_at.desc()).all()
    return render_template("articles/special_edition.html", edition=edition, articles=articles)


@public_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    category_slug = request.args.get("category")
    content_type = request.args.get("type")
    page = request.args.get("page", 1, type=int)

    results = None
    if q or category_slug or content_type:
        results = search_articles(
            q=q, category_slug=category_slug, content_type=content_type, page=page,
        )

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()

    return render_template(
        "search/index.html",
        q=q,
        results=results,
        categories=categories,
        active_category=category_slug,
        active_type=content_type,
    )


# === SEO ===

@public_bp.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {request.host_url.rstrip('/')}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@public_bp.route("/sitemap.xml")
def sitemap():
    """
    Generate sitemap.xml. Articles, categories, authors, tags.
    Kept simple; cache in production via reverse proxy.
    """
    from flask import render_template
    articles = Article.query.filter_by(status=Article.STATUS_PUBLISHED, is_audited=True).all()
    categories = Category.query.filter_by(is_active=True).all()
    authors = AuthorProfile.query.all()
    tags = Tag.query.all()
    return render_template(
        "public/sitemap.xml",
        articles=articles,
        categories=categories,
        authors=authors,
        tags=tags,
    ), 200, {"Content-Type": "application/xml"}


@public_bp.route("/rss.xml")
def rss():
    """RSS 2.0 feed of latest published articles."""
    articles = Article.query.filter_by(
        status=Article.STATUS_PUBLISHED, is_audited=True
    ).order_by(Article.published_at.desc().nullslast()).limit(50).all()
    return render_template(
        "public/rss.xml",
        articles=articles,
    ), 200, {"Content-Type": "application/rss+xml"}