from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.admin import CreateUserForm, EditUserForm
from app.forms.articles import ArticleForm, CategoryForm, TagForm
from app.forms.campus import (
    CampusEventForm, SportForm, TeamForm, FixtureForm,
    StudentForm, StaffForm, AlumniForm,
)
from app.forms.media import GalleryForm, GalleryImageForm, VideoForm, PodcastEpisodeForm
from app.forms.editorial import AnnouncementForm, PlacementForm, AdvertisementForm, SpecialEditionForm
from app.models.content import Article, Category, Tag
from app.models.campus import House, Club, CampusEvent
from app.models.media import Gallery, GalleryImage, Video, PodcastEpisode
from app.models.people import StudentProfile, StaffProfile, AlumniProfile
from app.models.sports import Sport, Team, Fixture
from app.models.user import AuthorProfile, User
from app.models.editorial import Theme, SpecialEdition, PlacementSlot, SiteAnnouncement
from app.models.system import Advertisement
from app.models.notifications import Notification
from app.models.engagement import Report
from app.services.article_service import (
    create_article, update_article, submit_for_review,
    approve_for_audit, reject_article, audit_approve, audit_reject,
    delete_article, add_gallery_images, remove_gallery_image,
    set_article_poll, remove_article_poll,
)
from app.services.audit_service import get_audit_queue, get_review_queue, count_pending_articles
from app.services.auth_service import auth_service
from app.services.analytics_service import get_dashboard_analytics
from app.services.media_service import save_upload, delete_upload, get_audio_duration
from app.services.youtube_service import get_latest_videos, normalize_video_id
from app.utils.decorators import admin_required, editor_required, role_required, super_admin_required
from app.utils.security import slugify, utcnow, local_naive_to_utc, utc_to_local_naive

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# === Dashboard ===

@admin_bp.route("/")
@editor_required
def dashboard():
    from app.models.campus import CampusEvent
    from app.models.engagement import Poll
    from app.models.system import ActivityLog

    reporting_days = request.args.get("days", 30, type=int)
    analytics = get_dashboard_analytics(reporting_days)
    reporting_days = analytics["days"]

    pending_counts = count_pending_articles()
    total_articles = Article.query.count()
    published_articles = Article.query.filter_by(status=Article.STATUS_PUBLISHED).count()
    drafts = Article.query.filter_by(status=Article.STATUS_DRAFT).count()
    total_users = User.query.count()
    pending_users = User.query.filter_by(account_status=User.STATUS_PENDING).count()
    upcoming_events = CampusEvent.query.filter(CampusEvent.start_at >= db.func.now()).count()
    active_polls = Poll.query.filter_by(status="active").count()
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        pending_review=pending_counts["pending_review"],
        pending_audit=pending_counts["pending_audit"],
        drafts=drafts,
        total_articles=total_articles,
        published_articles=published_articles,
        total_users=total_users,
        pending_users=pending_users,
        upcoming_events=upcoming_events,
        active_polls=active_polls,
        recent_activity=recent_activity,
        analytics=analytics,
        reporting_days=reporting_days,
    )


# === Articles ===

@admin_bp.route("/articles")
@editor_required
def articles_list():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status")
    query = Article.query

    if status:
        query = query.filter_by(status=status)
    else:
        # Show all except published (published are in archive)
        query = query.filter(Article.status != Article.STATUS_PUBLISHED)

    articles = query.order_by(Article.created_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/articles/list.html", articles=articles, status_filter=status)


@admin_bp.route("/articles/new", methods=["GET", "POST"])
@editor_required
def articles_new():
    form = ArticleForm()
    form.category_id.choices = [(0, "— None —")] + [(c.id, c.name) for c in Category.query.filter_by(is_active=True).all()]
    form.special_edition_id.choices = [(0, "— None —")] + [(e.id, e.title) for e in SpecialEdition.query.filter_by(is_active=True).order_by(SpecialEdition.title.asc()).all()]
    form.house_id.choices = [(0, "— None —")] + [(h.id, h.name) for h in House.query.filter_by(is_active=True).all()]
    form.club_id.choices = [(0, "— None —")] + [(c.id, c.name) for c in Club.query.filter_by(is_active=True).all()]
    youtube_videos = get_latest_videos(limit=12)

    is_valid = form.validate_on_submit() if request.method == "POST" else False
    if request.method == "POST" and not is_valid:
        for field_name, errors in form.errors.items():
            field = getattr(form, field_name, None)
            label = field.label.text if field is not None and hasattr(field, "label") else field_name
            for error in errors:
                flash(f"{label}: {error}", "error")

    if is_valid:
        data = form.data.copy()
        data["special_edition_id"] = data.get("special_edition_id") or None

        # Handle image upload
        image = form.featured_image.data

        if image and hasattr(image, "filename") and image.filename:
            data["featured_image"] = save_upload(image, "articles")

        # Handle audio upload
        if form.audio_file.data and form.audio_file.data.filename:
            audio_path = save_upload(form.audio_file.data, "audio")
            data["audio_url"] = audio_path
            from app.services.media_service import get_audio_duration
            data["audio_duration"] = get_audio_duration(audio_path)

        # Resolve the optional YouTube link/ID to its canonical 11-character ID.
        manual_youtube = (data.get("youtube_video_url") or "").strip()
        selected_youtube = data.get("youtube_video_id")
        data["youtube_video_id"] = normalize_video_id(manual_youtube or selected_youtube)

        # Parse tags
        data["tags"] = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]

        article = create_article(data, current_user.id)

        # Additional gallery images (beyond the single featured image)
        gallery_uploads = [
            f for f in (form.gallery_images.data or [])
            if f and hasattr(f, "filename") and f.filename
        ]
        if gallery_uploads:
            saved_paths = [save_upload(f, "articles") for f in gallery_uploads]
            add_gallery_images(article, saved_paths)

        # Poll
        if form.enable_poll.data:
            try:
                set_article_poll(
                    article,
                    form.poll_question.data,
                    form.poll_description.data,
                    form.poll_allow_multiple.data,
                    [
                        form.poll_option_1.data, form.poll_option_2.data,
                        form.poll_option_3.data, form.poll_option_4.data,
                    ],
                )
            except ValueError as e:
                flash(f"Article saved, but the poll wasn't: {e}", "warning")

        # Determine which action button was clicked directly from the raw
        # POST body — more robust than relying solely on WTForms' field
        # detection when a form has several submit buttons.
        wants_review = "submit_review" in request.form
        wants_publish = "submit_publish" in request.form

        if wants_review:
            submit_for_review(article)
            flash("Article submitted for review", "success")
        elif wants_publish and current_user.is_at_least("editor"):
            # Editors can publish directly (bypasses audit for now — in production, route through audit)
            article.status = Article.STATUS_PUBLISHED
            article.is_audited = True
            article.audited_by_id = current_user.id
            article.published_at = utcnow()
            db.session.commit()
            flash("Article published", "success")
        else:
            flash("Draft saved", "success")

        return redirect(url_for("admin.articles_list"))

    return render_template("admin/articles/form.html", form=form, editing=False, youtube_videos=youtube_videos)


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@editor_required
def articles_edit(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    # Check permissions: authors can edit own drafts, editors can edit any
    if article.author_id != current_user.id and not current_user.is_at_least("editor"):
        abort(403)

    form = ArticleForm(obj=article)
    form.category_id.choices = [(0, "— None —")] + [(c.id, c.name) for c in Category.query.filter_by(is_active=True).all()]
    form.special_edition_id.choices = [(0, "— None —")] + [(e.id, e.title) for e in SpecialEdition.query.filter_by(is_active=True).order_by(SpecialEdition.title.asc()).all()]
    form.house_id.choices = [(0, "— None —")] + [(h.id, h.name) for h in House.query.filter_by(is_active=True).all()]
    form.club_id.choices = [(0, "— None —")] + [(c.id, c.name) for c in Club.query.filter_by(is_active=True).all()]
    youtube_videos = get_latest_videos(limit=12)

    if request.method == "GET":
        form.tags.data = ", ".join([t.name for t in article.tags])
        if article.youtube_video_id and not any(v["video_id"] == article.youtube_video_id for v in youtube_videos):
            form.youtube_video_url.data = article.youtube_video_id
        if article.poll:
            form.enable_poll.data = True
            form.poll_question.data = article.poll.question
            form.poll_description.data = article.poll.description
            form.poll_allow_multiple.data = article.poll.allow_multiple
            options = article.poll.options
            for i in range(4):
                field = getattr(form, f"poll_option_{i + 1}")
                field.data = options[i].label if i < len(options) else ""

    is_valid_edit = form.validate_on_submit() if request.method == "POST" else False

    if request.method == "POST" and not is_valid_edit:
        for field_name, errors in form.errors.items():
            field = getattr(form, field_name, None)
            label = field.label.text if field is not None and hasattr(field, "label") else field_name
            for error in errors:
                flash(f"{label}: {error}", "error")

    if is_valid_edit:
        data = form.data.copy()
        data["special_edition_id"] = data.get("special_edition_id") or None

        # Handle image upload
        image = form.featured_image.data

        if image and hasattr(image, "filename") and image.filename:
            if article.featured_image:
                delete_upload(article.featured_image)

            data["featured_image"] = save_upload(image, "articles")
        else:
            data["featured_image"] = article.featured_image

        # Handle audio upload
        if form.audio_file.data and form.audio_file.data.filename:
            if article.audio_url:
                delete_upload(article.audio_url)
            audio_path = save_upload(form.audio_file.data, "audio")
            data["audio_url"] = audio_path
            from app.services.media_service import get_audio_duration
            data["audio_duration"] = get_audio_duration(audio_path)
        elif "audio_url" not in data:
            data["audio_url"] = article.audio_url
            data["audio_duration"] = article.audio_duration


        # Resolve the optional YouTube link/ID to its canonical 11-character ID.
        manual_youtube = (data.get("youtube_video_url") or "").strip()
        selected_youtube = data.get("youtube_video_id")
        data["youtube_video_id"] = normalize_video_id(manual_youtube or selected_youtube)

        # Parse tags
        data["tags"] = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]

        update_article(article, data)

        # Additional gallery images (beyond the single featured image)
        gallery_uploads = [
            f for f in (form.gallery_images.data or [])
            if f and hasattr(f, "filename") and f.filename
        ]
        if gallery_uploads:
            saved_paths = [save_upload(f, "articles") for f in gallery_uploads]
            add_gallery_images(article, saved_paths)

        # Poll
        if form.enable_poll.data:
            try:
                set_article_poll(
                    article,
                    form.poll_question.data,
                    form.poll_description.data,
                    form.poll_allow_multiple.data,
                    [
                        form.poll_option_1.data, form.poll_option_2.data,
                        form.poll_option_3.data, form.poll_option_4.data,
                    ],
                )
            except ValueError as e:
                flash(f"Article saved, but the poll wasn't: {e}", "warning")
        elif article.poll:
            remove_article_poll(article)

        # Determine which action button was clicked directly from the raw
        # POST body — more robust than relying solely on WTForms' field
        # detection when a form has several submit buttons.
        wants_review = "submit_review" in request.form
        wants_publish = "submit_publish" in request.form

        if wants_review and article.status == Article.STATUS_DRAFT:
            submit_for_review(article)
            flash("Article submitted for review", "success")
        elif wants_publish and current_user.is_at_least("editor"):
            # Editors/admins can publish directly (bypasses audit for now — in production, route through audit)
            article.status = Article.STATUS_PUBLISHED
            article.is_audited = True
            article.audited_by_id = current_user.id
            article.published_at = article.published_at or utcnow()
            db.session.commit()
            flash("Article published", "success")
        else:
            flash("Article updated", "success")

        return redirect(url_for("admin.articles_list"))

    return render_template("admin/articles/form.html", form=form, editing=True, article=article, youtube_videos=youtube_videos)


@admin_bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@super_admin_required
def articles_delete(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    if article.featured_image:
        delete_upload(article.featured_image)
    if article.audio_url:
        delete_upload(article.audio_url)

    title = article.title
    delete_article(article)

    flash(f"Article '{title}' deleted", "success")
    return redirect(url_for("admin.articles_list"))


@admin_bp.route("/articles/<int:article_id>/images/<int:image_id>/delete", methods=["POST"])
@editor_required
def article_image_delete(article_id, image_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    try:
        remove_gallery_image(article, image_id)
        flash("Image removed", "success")
    except ValueError:
        flash("Image not found", "error")

    return redirect(url_for("admin.articles_edit", article_id=article_id))


# === Review Queue ===

@admin_bp.route("/review")
@editor_required
def review_queue():
    articles = get_review_queue()
    return render_template("admin/articles/review.html", articles=articles)


@admin_bp.route("/articles/<int:article_id>/approve", methods=["POST"])
@editor_required
def articles_approve(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    try:
        approve_for_audit(article, current_user.id)
        flash("Article approved and moved to audit queue", "success")
    except (ValueError, PermissionError) as e:
        flash(str(e), "error")

    return redirect(url_for("admin.review_queue"))


@admin_bp.route("/articles/<int:article_id>/reject", methods=["POST"])
@editor_required
def articles_reject(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    notes = request.form.get("notes", "Rejected by editor")
    try:
        reject_article(article, current_user.id, notes)
        flash("Article rejected", "success")
    except (ValueError, PermissionError) as e:
        flash(str(e), "error")

    return redirect(url_for("admin.review_queue"))


# === Audit Queue ===

@admin_bp.route("/audit")
@editor_required
def audit_queue():
    articles = get_audit_queue(current_user.id)
    return render_template("admin/articles/audit.html", articles=articles)


@admin_bp.route("/articles/<int:article_id>/audit-approve", methods=["POST"])
@editor_required
def articles_audit_approve(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    try:
        audit_approve(article, current_user.id)
        flash("Article audit approved and published", "success")
    except (ValueError, PermissionError) as e:
        flash(str(e), "error")

    return redirect(url_for("admin.audit_queue"))


@admin_bp.route("/articles/<int:article_id>/audit-reject", methods=["POST"])
@editor_required
def articles_audit_reject(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)

    notes = request.form.get("notes", "Rejected in audit")
    try:
        audit_reject(article, current_user.id, notes)
        flash("Article rejected in audit", "success")
    except (ValueError, PermissionError) as e:
        flash(str(e), "error")

    return redirect(url_for("admin.audit_queue"))

def _can_manage_user(user: User) -> bool:
    """Admins can manage contributors; only super_admins manage administrators."""
    if current_user.role == User.ROLE_SUPER_ADMIN:
        return True
    return user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)


def _ensure_author_profile(user: User, display_name: str | None = None) -> None:
    """Keep author-facing roles usable when an account is promoted."""
    author_roles = {
        User.ROLE_AUTHOR,
        User.ROLE_EDITOR,
        User.ROLE_TEACHER_EDITOR,
        User.ROLE_STUDENT_JOURNALIST,
    }
    if user.role in author_roles and not user.author_profile:
        name = display_name or user.username
        db.session.add(AuthorProfile(
            user_id=user.id,
            display_name=name,
            slug=f"{slugify(name)}-{user.id}",
        ))


@admin_bp.route("/categories")
@admin_required
def categories_list():
    categories = Category.query.order_by(Category.display_order.asc(), Category.name.asc()).all()
    return render_template(
        "admin/reference.html",
        title="Categories",
        items=categories,
        public_endpoint="public.category",
    )


@admin_bp.route("/tags")
@admin_required
def tags_list():
    tags = Tag.query.order_by(Tag.name.asc()).all()
    return render_template(
        "admin/reference.html",
        title="Tags",
        items=tags,
        public_endpoint="public.tag",
    )


@admin_bp.route("/users")
@admin_required
def users_list():
    search = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)

    query = User.query
    if search:
        term = f"%{search}%"
        query = query.filter(or_(User.username.ilike(term), User.email.ilike(term)))
    if role_filter in User.ROLES:
        query = query.filter_by(role=role_filter)
    else:
        role_filter = ""
    if status_filter in {
        User.STATUS_ACTIVE,
        User.STATUS_PENDING,
        User.STATUS_SUSPENDED,
        User.STATUS_DEACTIVATED,
    }:
        query = query.filter_by(account_status=status_filter)
    else:
        status_filter = ""

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "admin/users/list.html",
        users=users,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def users_new():
    form = CreateUserForm(current_user.role)
    if form.validate_on_submit():
        try:
            user = auth_service.create_user(
                creator=current_user,
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                password=form.password.data,
                role=form.role.data,
                display_name=form.display_name.data.strip() if form.display_name.data else None,
            )
            status_message = (
                "active immediately"
                if user.account_status == User.STATUS_ACTIVE
                else "pending superadmin verification"
            )
            flash(f"User '{user.username}' created ({status_message}).", "success")
            return redirect(url_for("admin.users_list"))
        except (PermissionError, ValueError) as exc:
            flash(str(exc), "error")
        except IntegrityError:
            db.session.rollback()
            flash("That username or email is already in use.", "error")

    return render_template("admin/users/form.html", form=form, editing=False)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def users_edit(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if not _can_manage_user(user):
        abort(403)

    form = EditUserForm(current_user.role, obj=user)
    if form.validate_on_submit():
        duplicate = User.query.filter(
            User.email == form.email.data.strip().lower(),
            User.id != user.id,
        ).first()
        if duplicate:
            form.email.errors.append("Email already in use")
        elif user.id == current_user.id and (
            form.role.data != user.role
            or form.account_status.data != User.STATUS_ACTIVE
        ):
            flash("You cannot remove your own superadmin access.", "error")
        else:
            user.email = form.email.data.strip().lower()
            user.role = form.role.data
            user.account_status = form.account_status.data
            user.is_active = user.account_status == User.STATUS_ACTIVE
            if user.account_status == User.STATUS_ACTIVE and not user.verified_at:
                user.verified_at = utcnow()
                user.verified_by_id = current_user.id
            _ensure_author_profile(user)
            try:
                db.session.commit()
                from app.services.activity_service import log_activity
                log_activity(
                    current_user.id,
                    "user.update",
                    "user",
                    user.id,
                    f"Updated user {user.username}",
                )
                flash(f"User '{user.username}' updated.", "success")
                return redirect(url_for("admin.users_list"))
            except IntegrityError:
                db.session.rollback()
                flash("That email is already in use.", "error")

    return render_template(
        "admin/users/form.html",
        form=form,
        editing=True,
        user=user,
    )


@admin_bp.route("/users/<int:user_id>/verify", methods=["POST"])
@super_admin_required
def users_verify(user_id):
    try:
        user = auth_service.verify_account(current_user, user_id)
        flash(f"Account '{user.username}' verified.", "success")
    except (PermissionError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("admin.accounts_pending"))


@admin_bp.route("/users/pending")
@super_admin_required
def accounts_pending():
    page = request.args.get("page", 1, type=int)
    users = User.query.filter_by(
        account_status=User.STATUS_PENDING
    ).order_by(User.created_at.asc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template("admin/users/pending.html", users=users)


from app.forms.themes import ThemeForm
from app.services.theme_service import (
    activate_theme, deactivate_theme, preview_theme, render_theme_css,
)


# === Themes ===

@admin_bp.route("/themes")
@admin_required
def themes_list():
    themes = Theme.query.order_by(Theme.priority.desc(), Theme.name.asc()).all()
    from app.services.theme_service import resolve_active_theme
    active = resolve_active_theme()
    return render_template(
        "admin/themes/list.html",
        themes=themes,
        active_theme=active,
    )


@admin_bp.route("/themes/new", methods=["GET", "POST"])
@admin_required
def themes_new():
    form = ThemeForm()
    if form.validate_on_submit():
        data = form.data
        slug = data.get("slug") or slugify(data["name"])

        # Build decoration_config JSON
        decoration_config = {
            "motif": data.get("decoration_motif") or None,
            "density": data.get("decoration_density") or "low",
        }
        animation_config = {
            "enabled": [],
            "respect_reduced_motion": True,
        }
        if data.get("animation_snow"):
            animation_config["enabled"].append("snow")
        if data.get("animation_sparkle"):
            animation_config["enabled"].append("sparkle")
        if data.get("animation_float"):
            animation_config["enabled"].append("float")

        theme = Theme(
            name=data["name"],
            slug=slug,
            theme_type=data["theme_type"],
            description=data.get("description"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            primary_color=data.get("primary_color"),
            secondary_color=data.get("secondary_color"),
            accent_color=data.get("accent_color"),
            background_color=data.get("background_color"),
            text_color=data.get("text_color"),
            decoration_config=decoration_config,
            animation_config=animation_config,
            sound_enabled=data.get("sound_enabled", False),
            is_active=data.get("is_active", True),
            priority=data.get("priority", 0),
        )

        # Handle file uploads
        if form.header_logo.data:
            theme.header_logo = save_upload(form.header_logo.data, "themes")
        if form.banner_image.data:
            theme.banner_image = save_upload(form.banner_image.data, "themes")
        if form.background_image.data:
            theme.background_image = save_upload(form.background_image.data, "themes")

        db.session.add(theme)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "theme.create", "theme", theme.id, f"Created '{theme.name}'")

        flash(f"Theme '{theme.name}' created", "success")
        return redirect(url_for("admin.themes_list"))

    return render_template("admin/themes/form.html", form=form, editing=False)


@admin_bp.route("/themes/<int:theme_id>/edit", methods=["GET", "POST"])
@admin_required
def themes_edit(theme_id):
    theme = db.session.get(Theme, theme_id)
    if not theme:
        abort(404)

    form = ThemeForm(obj=theme)

    # Populate decoration fields from JSON
    if request.method == "GET":
        deco = theme.decoration_config or {}
        form.decoration_motif.data = deco.get("motif", "")
        form.decoration_density.data = deco.get("density", "low")
        anim = theme.animation_config or {}
        enabled = anim.get("enabled", [])
        form.animation_snow.data = "snow" in enabled
        form.animation_sparkle.data = "sparkle" in enabled
        form.animation_float.data = "float" in enabled

    if form.validate_on_submit():
        data = form.data
        theme.name = data["name"]
        theme.theme_type = data["theme_type"]
        theme.description = data.get("description")
        theme.start_date = data.get("start_date")
        theme.end_date = data.get("end_date")
        theme.primary_color = data.get("primary_color")
        theme.secondary_color = data.get("secondary_color")
        theme.accent_color = data.get("accent_color")
        theme.background_color = data.get("background_color")
        theme.text_color = data.get("text_color")
        theme.sound_enabled = data.get("sound_enabled", False)
        theme.is_active = data.get("is_active", True)
        theme.priority = data.get("priority", 0)

        # Rebuild decoration JSON
        theme.decoration_config = {
            "motif": data.get("decoration_motif") or None,
            "density": data.get("decoration_density") or "low",
        }
        enabled = []
        if data.get("animation_snow"): enabled.append("snow")
        if data.get("animation_sparkle"): enabled.append("sparkle")
        if data.get("animation_float"): enabled.append("float")
        theme.animation_config = {
            "enabled": enabled,
            "respect_reduced_motion": True,
        }

        # Handle file uploads
        if form.header_logo.data:
            if theme.header_logo:
                delete_upload(theme.header_logo)
            theme.header_logo = save_upload(form.header_logo.data, "themes")
        if form.banner_image.data:
            if theme.banner_image:
                delete_upload(theme.banner_image)
            theme.banner_image = save_upload(form.banner_image.data, "themes")
        if form.background_image.data:
            if theme.background_image:
                delete_upload(theme.background_image)
            theme.background_image = save_upload(form.background_image.data, "themes")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "theme.update", "theme", theme.id, f"Updated '{theme.name}'")

        flash(f"Theme '{theme.name}' updated", "success")
        return redirect(url_for("admin.themes_list"))

    return render_template("admin/themes/form.html", form=form, editing=True, theme=theme)


@admin_bp.route("/themes/<int:theme_id>/activate", methods=["POST"])
@admin_required
def themes_activate(theme_id):
    try:
        theme = activate_theme(theme_id, current_user.id)
        flash(f"Theme '{theme.name}' activated", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.themes_list"))


@admin_bp.route("/themes/<int:theme_id>/deactivate", methods=["POST"])
@admin_required
def themes_deactivate(theme_id):
    try:
        theme = deactivate_theme(theme_id, current_user.id)
        flash(f"Theme '{theme.name}' deactivated", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.themes_list"))


@admin_bp.route("/themes/<int:theme_id>/preview")
@admin_required
def themes_preview(theme_id):
    theme = preview_theme(theme_id)
    if not theme:
        abort(404)
    return render_template("admin/themes/preview.html", theme=theme)


@admin_bp.route("/themes/<int:theme_id>/delete", methods=["POST"])
@admin_required
def themes_delete(theme_id):
    theme = db.session.get(Theme, theme_id)
    if not theme:
        abort(404)

    # Delete associated files
    for field in ["header_logo", "banner_image", "background_image"]:
        path = getattr(theme, field, None)
        if path:
            delete_upload(path)

    name = theme.name
    db.session.delete(theme)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "theme.delete", "theme", theme_id, f"Deleted '{name}'")

    flash(f"Theme '{name}' deleted", "success")
    return redirect(url_for("admin.themes_list"))


# === Editorial control centre ===

@admin_bp.route("/special-editions")
@admin_required
def special_editions_list():
    editions = SpecialEdition.query.order_by(SpecialEdition.start_at.desc().nullslast(), SpecialEdition.id.desc()).all()
    return render_template("admin/editorial/special_editions_list.html", editions=editions)


def _populate_edition_theme_choices(form):
    form.theme_id.choices = [(0, "— No theme —")] + [(t.id, t.name) for t in Theme.query.order_by(Theme.name.asc()).all()]


@admin_bp.route("/special-editions/new", methods=["GET", "POST"])
@admin_required
def special_editions_new():
    form = SpecialEditionForm(); _populate_edition_theme_choices(form)
    if form.validate_on_submit():
        slug = form.slug.data.strip() if form.slug.data else slugify(form.title.data)
        edition = SpecialEdition(title=form.title.data.strip(), slug=slug, description=form.description.data,
                                 theme_id=form.theme_id.data or None, start_at=form.start_at.data, end_at=form.end_at.data,
                                 is_active=form.is_active.data)
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            edition.cover_image = save_upload(form.cover_image.data, "special-editions")
        db.session.add(edition); db.session.commit()
        from app.services.activity_service import log_activity
        log_activity(current_user.id, "special_edition.create", "special_edition", edition.id, f"Created '{edition.title}'")
        flash("Special edition created", "success")
        return redirect(url_for("admin.special_editions_list"))
    return render_template("admin/editorial/special_edition_form.html", form=form, editing=False)


@admin_bp.route("/special-editions/<int:edition_id>/edit", methods=["GET", "POST"])
@admin_required
def special_editions_edit(edition_id):
    edition=db.session.get(SpecialEdition, edition_id)
    if not edition: abort(404)
    form=SpecialEditionForm(obj=edition); _populate_edition_theme_choices(form)
    if form.validate_on_submit():
        edition.title=form.title.data.strip(); edition.slug=(form.slug.data.strip() if form.slug.data else slugify(edition.title))
        edition.description=form.description.data; edition.theme_id=form.theme_id.data or None
        edition.start_at=form.start_at.data; edition.end_at=form.end_at.data; edition.is_active=form.is_active.data
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            if edition.cover_image: delete_upload(edition.cover_image)
            edition.cover_image=save_upload(form.cover_image.data, "special-editions")
        db.session.commit(); flash("Special edition updated", "success")
        return redirect(url_for("admin.special_editions_list"))
    return render_template("admin/editorial/special_edition_form.html", form=form, editing=True, edition=edition)


@admin_bp.route("/special-editions/<int:edition_id>/delete", methods=["POST"])
@admin_required
def special_editions_delete(edition_id):
    edition=db.session.get(SpecialEdition, edition_id)
    if not edition: abort(404)
    if edition.cover_image: delete_upload(edition.cover_image)
    title=edition.title; db.session.delete(edition); db.session.commit()
    flash(f"Special edition '{title}' deleted", "success")
    return redirect(url_for("admin.special_editions_list"))


@admin_bp.route("/placements")
@editor_required
def placements_list():
    placements=PlacementSlot.query.order_by(PlacementSlot.zone.asc(), PlacementSlot.position.asc(), PlacementSlot.id.desc()).all()
    return render_template("admin/editorial/placements_list.html", placements=placements)


def _populate_placement_choices(form):
    form.article_id.choices=[(a.id, a.title) for a in Article.query.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).limit(300).all()]


@admin_bp.route("/placements/new", methods=["GET", "POST"])
@editor_required
def placements_new():
    form=PlacementForm(); _populate_placement_choices(form)
    if form.validate_on_submit():
        placement=PlacementSlot(zone=form.zone.data, article_id=form.article_id.data, position=form.position.data or 0,
                                is_manual_override=form.is_manual_override.data, start_at=form.start_at.data, end_at=form.end_at.data,
                                set_by_user_id=current_user.id)
        db.session.add(placement); db.session.commit(); flash("Homepage placement created", "success")
        return redirect(url_for("admin.placements_list"))
    return render_template("admin/editorial/placement_form.html", form=form, editing=False)


@admin_bp.route("/placements/<int:placement_id>/edit", methods=["GET", "POST"])
@editor_required
def placements_edit(placement_id):
    placement=db.session.get(PlacementSlot, placement_id)
    if not placement: abort(404)
    form=PlacementForm(obj=placement); _populate_placement_choices(form)
    if form.validate_on_submit():
        placement.zone=form.zone.data; placement.article_id=form.article_id.data; placement.position=form.position.data or 0
        placement.is_manual_override=form.is_manual_override.data; placement.start_at=form.start_at.data; placement.end_at=form.end_at.data
        placement.set_by_user_id=current_user.id; db.session.commit(); flash("Homepage placement updated", "success")
        return redirect(url_for("admin.placements_list"))
    return render_template("admin/editorial/placement_form.html", form=form, editing=True, placement=placement)


@admin_bp.route("/placements/<int:placement_id>/delete", methods=["POST"])
@editor_required
def placements_delete(placement_id):
    placement=db.session.get(PlacementSlot, placement_id)
    if not placement: abort(404)
    db.session.delete(placement); db.session.commit(); flash("Placement removed", "success")
    return redirect(url_for("admin.placements_list"))


@admin_bp.route("/announcements")
@admin_required
def announcements_list():
    announcements=SiteAnnouncement.query.order_by(SiteAnnouncement.priority.desc(), SiteAnnouncement.created_at.desc()).all()
    return render_template("admin/editorial/announcements_list.html", announcements=announcements)


def _save_announcement(form, announcement=None):
    if announcement is None:
        announcement=SiteAnnouncement(created_by=current_user.id); db.session.add(announcement)
    for name in ("title","message","display_type","severity","target_scope","cta_text","cta_url","dismissible","priority","start_at","end_at","is_active"):
        setattr(announcement, name, getattr(form, name).data)
    db.session.commit(); return announcement


@admin_bp.route("/announcements/new", methods=["GET", "POST"])
@admin_required
def announcements_new():
    form=AnnouncementForm()
    if form.validate_on_submit():
        _save_announcement(form); flash("Announcement published", "success"); return redirect(url_for("admin.announcements_list"))
    return render_template("admin/editorial/announcement_form.html", form=form, editing=False)


@admin_bp.route("/announcements/<int:announcement_id>/edit", methods=["GET", "POST"])
@admin_required
def announcements_edit(announcement_id):
    announcement=db.session.get(SiteAnnouncement, announcement_id)
    if not announcement: abort(404)
    form=AnnouncementForm(obj=announcement)
    if form.validate_on_submit():
        _save_announcement(form, announcement); flash("Announcement updated", "success"); return redirect(url_for("admin.announcements_list"))
    return render_template("admin/editorial/announcement_form.html", form=form, editing=True, announcement=announcement)


@admin_bp.route("/announcements/<int:announcement_id>/delete", methods=["POST"])
@admin_required
def announcements_delete(announcement_id):
    announcement=db.session.get(SiteAnnouncement, announcement_id)
    if not announcement: abort(404)
    db.session.delete(announcement); db.session.commit(); flash("Announcement deleted", "success")
    return redirect(url_for("admin.announcements_list"))


@admin_bp.route("/advertisements")
@admin_required
def advertisements_list():
    ads=Advertisement.query.order_by(Advertisement.placement.asc(), Advertisement.priority.desc(), Advertisement.id.desc()).all()
    return render_template("admin/editorial/advertisements_list.html", advertisements=ads)


def _save_ad(form, ad=None):
    if ad is None: ad=Advertisement(); db.session.add(ad)
    for name in ("name","placement","html_code","target_url","is_active","start_at","end_at","priority"):
        setattr(ad, name, getattr(form,name).data)
    if form.image.data:
        if ad.image: delete_upload(ad.image)
        ad.image=save_upload(form.image.data, "advertisements")
    db.session.commit(); return ad


@admin_bp.route("/advertisements/new", methods=["GET","POST"])
@admin_required
def advertisements_new():
    form=AdvertisementForm()
    if form.validate_on_submit(): _save_ad(form); flash("Advertisement created", "success"); return redirect(url_for("admin.advertisements_list"))
    return render_template("admin/editorial/advertisement_form.html", form=form, editing=False)


@admin_bp.route("/advertisements/<int:ad_id>/edit", methods=["GET","POST"])
@admin_required
def advertisements_edit(ad_id):
    ad=db.session.get(Advertisement, ad_id)
    if not ad: abort(404)
    form=AdvertisementForm(obj=ad)
    if form.validate_on_submit(): _save_ad(form, ad); flash("Advertisement updated", "success"); return redirect(url_for("admin.advertisements_list"))
    return render_template("admin/editorial/advertisement_form.html", form=form, editing=True, advertisement=ad)


@admin_bp.route("/advertisements/<int:ad_id>/delete", methods=["POST"])
@admin_required
def advertisements_delete(ad_id):
    ad=db.session.get(Advertisement, ad_id)
    if not ad: abort(404)
    if ad.image: delete_upload(ad.image)
    db.session.delete(ad); db.session.commit(); flash("Advertisement deleted", "success"); return redirect(url_for("admin.advertisements_list"))


@admin_bp.route("/reports")
@editor_required
def reports_list():
    status=request.args.get("status","open")
    if status not in ("open","reviewed","dismissed"): status="open"
    reports=Report.query.filter_by(status=status).order_by(Report.created_at.desc()).all()
    return render_template("admin/editorial/reports_list.html", reports=reports, status=status)


@admin_bp.route("/reports/<int:report_id>/<status>", methods=["POST"])
@editor_required
def report_update(report_id, status):
    if status not in ("reviewed","dismissed","open"): abort(400)
    report=db.session.get(Report, report_id)
    if not report: abort(404)
    report.status=status; db.session.commit(); flash("Report updated", "success")
    return redirect(request.referrer or url_for("admin.reports_list"))


@admin_bp.route("/notifications")
@login_required
def notifications_list():
    page=request.args.get("page",1,type=int)
    notifications=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).paginate(page=page,per_page=25,error_out=False)
    unread=Notification.query.filter_by(user_id=current_user.id, read_at=None).count()
    return render_template("admin/editorial/notifications.html", notifications=notifications, unread=unread)


@admin_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def notification_read(notification_id):
    item=Notification.query.filter_by(id=notification_id,user_id=current_user.id).first()
    if not item: abort(404)
    item.read_at=utcnow(); db.session.commit()
    return redirect(item.link_url or request.referrer or url_for("admin.notifications_list"))


# === Houses (super_admin only) ===

from app.forms.campus import HouseForm, ClubForm


def _unique_slug(model, base_slug: str, exclude_id: int | None = None) -> str:
    """Append -2, -3, ... until the slug is unique for the given model."""
    slug = base_slug
    n = 2
    while True:
        query = model.query.filter_by(slug=slug)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{n}"
        n += 1


@admin_bp.route("/houses")
@super_admin_required
def houses_list():
    houses = House.query.order_by(House.name.asc()).all()
    return render_template("admin/campus/houses_list.html", houses=houses)


@admin_bp.route("/houses/new", methods=["GET", "POST"])
@super_admin_required
def houses_new():
    form = HouseForm()
    if form.validate_on_submit():
        slug = _unique_slug(House, slugify(form.name.data))
        house = House(
            name=form.name.data.strip(),
            slug=slug,
            description=form.description.data,
            color=form.color.data,
            is_active=form.is_active.data,
        )
        if form.logo.data and form.logo.data.filename:
            house.logo = save_upload(form.logo.data, "houses")

        db.session.add(house)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "house.create", "house", house.id, f"Created '{house.name}'")

        flash(f"House '{house.name}' created", "success")
        return redirect(url_for("admin.houses_list"))

    return render_template("admin/campus/house_form.html", form=form, editing=False)


@admin_bp.route("/houses/<int:house_id>/edit", methods=["GET", "POST"])
@super_admin_required
def houses_edit(house_id):
    house = db.session.get(House, house_id)
    if not house:
        abort(404)

    form = HouseForm(obj=house)
    if form.validate_on_submit():
        if form.name.data.strip() != house.name:
            house.slug = _unique_slug(House, slugify(form.name.data), exclude_id=house.id)
        house.name = form.name.data.strip()
        house.description = form.description.data
        house.color = form.color.data
        house.is_active = form.is_active.data

        if form.logo.data and form.logo.data.filename:
            if house.logo:
                delete_upload(house.logo)
            house.logo = save_upload(form.logo.data, "houses")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "house.update", "house", house.id, f"Updated '{house.name}'")

        flash(f"House '{house.name}' updated", "success")
        return redirect(url_for("admin.houses_list"))

    return render_template("admin/campus/house_form.html", form=form, editing=True, house=house)


@admin_bp.route("/houses/<int:house_id>/delete", methods=["POST"])
@super_admin_required
def houses_delete(house_id):
    house = db.session.get(House, house_id)
    if not house:
        abort(404)

    in_use = (
        Article.query.filter_by(house_id=house.id).first()
        or house.students
        or house.author_profiles
    )
    if in_use:
        flash(
            f"'{house.name}' is still linked to articles, students, or authors. "
            "Reassign or remove those links first, or mark the house inactive instead.",
            "error",
        )
        return redirect(url_for("admin.houses_list"))

    if house.logo:
        delete_upload(house.logo)

    name = house.name
    db.session.delete(house)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "house.delete", "house", house_id, f"Deleted '{name}'")

    flash(f"House '{name}' deleted", "success")
    return redirect(url_for("admin.houses_list"))


# === Clubs (super_admin only) ===

@admin_bp.route("/clubs")
@super_admin_required
def clubs_list():
    clubs = Club.query.order_by(Club.name.asc()).all()
    return render_template("admin/campus/clubs_list.html", clubs=clubs)


@admin_bp.route("/clubs/new", methods=["GET", "POST"])
@super_admin_required
def clubs_new():
    form = ClubForm()
    if form.validate_on_submit():
        slug = _unique_slug(Club, slugify(form.name.data))
        club = Club(
            name=form.name.data.strip(),
            slug=slug,
            description=form.description.data,
            meeting_information=form.meeting_information.data,
            leader_name=form.leader_name.data,
            is_active=form.is_active.data,
        )
        if form.logo.data and form.logo.data.filename:
            club.logo = save_upload(form.logo.data, "clubs")
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            club.cover_image = save_upload(form.cover_image.data, "clubs")

        db.session.add(club)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "club.create", "club", club.id, f"Created '{club.name}'")

        flash(f"Club '{club.name}' created", "success")
        return redirect(url_for("admin.clubs_list"))

    return render_template("admin/campus/club_form.html", form=form, editing=False)


@admin_bp.route("/clubs/<int:club_id>/edit", methods=["GET", "POST"])
@super_admin_required
def clubs_edit(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        abort(404)

    form = ClubForm(obj=club)
    if form.validate_on_submit():
        if form.name.data.strip() != club.name:
            club.slug = _unique_slug(Club, slugify(form.name.data), exclude_id=club.id)
        club.name = form.name.data.strip()
        club.description = form.description.data
        club.meeting_information = form.meeting_information.data
        club.leader_name = form.leader_name.data
        club.is_active = form.is_active.data

        if form.logo.data and form.logo.data.filename:
            if club.logo:
                delete_upload(club.logo)
            club.logo = save_upload(form.logo.data, "clubs")
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            if club.cover_image:
                delete_upload(club.cover_image)
            club.cover_image = save_upload(form.cover_image.data, "clubs")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "club.update", "club", club.id, f"Updated '{club.name}'")

        flash(f"Club '{club.name}' updated", "success")
        return redirect(url_for("admin.clubs_list"))

    return render_template("admin/campus/club_form.html", form=form, editing=True, club=club)


@admin_bp.route("/clubs/<int:club_id>/delete", methods=["POST"])
@super_admin_required
def clubs_delete(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        abort(404)

    in_use = Article.query.filter_by(club_id=club.id).first()
    if in_use:
        flash(
            f"'{club.name}' is still linked to articles. "
            "Reassign or remove those links first, or mark the club inactive instead.",
            "error",
        )
        return redirect(url_for("admin.clubs_list"))

    if club.logo:
        delete_upload(club.logo)
    if club.cover_image:
        delete_upload(club.cover_image)

    name = club.name
    db.session.delete(club)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "club.delete", "club", club_id, f"Deleted '{name}'")

    flash(f"Club '{name}' deleted", "success")
    return redirect(url_for("admin.clubs_list"))


# === Sports (super_admin only) ===

@admin_bp.route("/sports")
@super_admin_required
def sports_list():
    sports = Sport.query.order_by(Sport.name.asc()).all()
    return render_template("admin/campus/sports_list.html", sports=sports)


@admin_bp.route("/sports/new", methods=["GET", "POST"])
@super_admin_required
def sports_new():
    form = SportForm()
    if form.validate_on_submit():
        slug = _unique_slug(Sport, slugify(form.name.data))
        sport = Sport(
            name=form.name.data.strip(),
            slug=slug,
            description=form.description.data,
            is_active=form.is_active.data,
        )
        if form.icon.data and form.icon.data.filename:
            sport.icon = save_upload(form.icon.data, "sports")

        db.session.add(sport)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "sport.create", "sport", sport.id, f"Created '{sport.name}'")

        flash(f"Sport '{sport.name}' created", "success")
        return redirect(url_for("admin.sports_list"))

    return render_template("admin/campus/sport_form.html", form=form, editing=False)


@admin_bp.route("/sports/<int:sport_id>/edit", methods=["GET", "POST"])
@super_admin_required
def sports_edit(sport_id):
    sport = db.session.get(Sport, sport_id)
    if not sport:
        abort(404)

    form = SportForm(obj=sport)
    if form.validate_on_submit():
        if form.name.data.strip() != sport.name:
            sport.slug = _unique_slug(Sport, slugify(form.name.data), exclude_id=sport.id)
        sport.name = form.name.data.strip()
        sport.description = form.description.data
        sport.is_active = form.is_active.data

        if form.icon.data and form.icon.data.filename:
            if sport.icon:
                delete_upload(sport.icon)
            sport.icon = save_upload(form.icon.data, "sports")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "sport.update", "sport", sport.id, f"Updated '{sport.name}'")

        flash(f"Sport '{sport.name}' updated", "success")
        return redirect(url_for("admin.sports_list"))

    return render_template("admin/campus/sport_form.html", form=form, editing=True, sport=sport)


@admin_bp.route("/sports/<int:sport_id>/delete", methods=["POST"])
@super_admin_required
def sports_delete(sport_id):
    sport = db.session.get(Sport, sport_id)
    if not sport:
        abort(404)

    if sport.teams:
        flash(
            f"'{sport.name}' still has teams linked to it. "
            "Reassign or remove those teams first, or mark the sport inactive instead.",
            "error",
        )
        return redirect(url_for("admin.sports_list"))

    if sport.icon:
        delete_upload(sport.icon)

    name = sport.name
    db.session.delete(sport)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "sport.delete", "sport", sport_id, f"Deleted '{name}'")

    flash(f"Sport '{name}' deleted", "success")
    return redirect(url_for("admin.sports_list"))


# === Teams (super_admin only) ===

def _populate_team_choices(form: TeamForm) -> None:
    form.sport_id.choices = [
        (s.id, s.name) for s in Sport.query.order_by(Sport.name.asc()).all()
    ]


@admin_bp.route("/teams")
@super_admin_required
def teams_list():
    teams = Team.query.order_by(Team.name.asc()).all()
    return render_template("admin/campus/teams_list.html", teams=teams)


@admin_bp.route("/teams/new", methods=["GET", "POST"])
@super_admin_required
def teams_new():
    form = TeamForm()
    _populate_team_choices(form)

    if form.validate_on_submit():
        team = Team(
            name=form.name.data.strip(),
            sport_id=form.sport_id.data,
            season=form.season.data,
            is_active=form.is_active.data,
        )
        if form.logo.data and form.logo.data.filename:
            team.logo = save_upload(form.logo.data, "teams")

        db.session.add(team)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "team.create", "team", team.id, f"Created '{team.name}'")

        flash(f"Team '{team.name}' created", "success")
        return redirect(url_for("admin.teams_list"))

    return render_template("admin/campus/team_form.html", form=form, editing=False)


@admin_bp.route("/teams/<int:team_id>/edit", methods=["GET", "POST"])
@super_admin_required
def teams_edit(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)

    form = TeamForm(obj=team)
    _populate_team_choices(form)

    if form.validate_on_submit():
        team.name = form.name.data.strip()
        team.sport_id = form.sport_id.data
        team.season = form.season.data
        team.is_active = form.is_active.data

        if form.logo.data and form.logo.data.filename:
            if team.logo:
                delete_upload(team.logo)
            team.logo = save_upload(form.logo.data, "teams")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "team.update", "team", team.id, f"Updated '{team.name}'")

        flash(f"Team '{team.name}' updated", "success")
        return redirect(url_for("admin.teams_list"))

    return render_template("admin/campus/team_form.html", form=form, editing=True, team=team)


@admin_bp.route("/teams/<int:team_id>/delete", methods=["POST"])
@super_admin_required
def teams_delete(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)

    if team.home_fixtures or team.away_fixtures:
        flash(
            f"'{team.name}' still has fixtures linked to it. "
            "Remove those fixtures first, or mark the team inactive instead.",
            "error",
        )
        return redirect(url_for("admin.teams_list"))

    if team.logo:
        delete_upload(team.logo)

    name = team.name
    db.session.delete(team)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "team.delete", "team", team_id, f"Deleted '{name}'")

    flash(f"Team '{name}' deleted", "success")
    return redirect(url_for("admin.teams_list"))


# === Fixtures (editor and above) ===

def _populate_fixture_choices(form: FixtureForm) -> None:
    team_choices = [(t.id, f"{t.name} ({t.sport.name})") for t in Team.query.order_by(Team.name.asc()).all()]
    form.home_team_id.choices = team_choices
    form.away_team_id.choices = team_choices


@admin_bp.route("/fixtures")
@editor_required
def fixtures_list():
    fixtures = Fixture.query.order_by(Fixture.match_date.desc()).all()
    return render_template("admin/campus/fixtures_list.html", fixtures=fixtures)


@admin_bp.route("/fixtures/new", methods=["GET", "POST"])
@editor_required
def fixtures_new():
    form = FixtureForm()
    _populate_fixture_choices(form)

    if form.validate_on_submit():
        if form.home_team_id.data == form.away_team_id.data:
            flash("Home team and away team must be different", "error")
            return render_template("admin/campus/fixture_form.html", form=form, editing=False)

        fixture = Fixture(
            home_team_id=form.home_team_id.data,
            away_team_id=form.away_team_id.data,
            competition=form.competition.data,
            venue=form.venue.data,
            match_date=form.match_date.data,
            status=form.status.data,
            home_score=form.home_score.data,
            away_score=form.away_score.data,
            notes=form.notes.data,
        )
        db.session.add(fixture)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "fixture.create", "fixture", fixture.id, f"Created fixture #{fixture.id}")

        flash("Fixture created", "success")
        return redirect(url_for("admin.fixtures_list"))

    return render_template("admin/campus/fixture_form.html", form=form, editing=False)


@admin_bp.route("/fixtures/<int:fixture_id>/edit", methods=["GET", "POST"])
@editor_required
def fixtures_edit(fixture_id):
    fixture = db.session.get(Fixture, fixture_id)
    if not fixture:
        abort(404)

    form = FixtureForm(obj=fixture)
    _populate_fixture_choices(form)

    if form.validate_on_submit():
        if form.home_team_id.data == form.away_team_id.data:
            flash("Home team and away team must be different", "error")
            return render_template("admin/campus/fixture_form.html", form=form, editing=True, fixture=fixture)

        fixture.home_team_id = form.home_team_id.data
        fixture.away_team_id = form.away_team_id.data
        fixture.competition = form.competition.data
        fixture.venue = form.venue.data
        fixture.match_date = form.match_date.data
        fixture.status = form.status.data
        fixture.home_score = form.home_score.data
        fixture.away_score = form.away_score.data
        fixture.notes = form.notes.data

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "fixture.update", "fixture", fixture.id, f"Updated fixture #{fixture.id}")

        flash("Fixture updated", "success")
        return redirect(url_for("admin.fixtures_list"))

    return render_template("admin/campus/fixture_form.html", form=form, editing=True, fixture=fixture)


@admin_bp.route("/fixtures/<int:fixture_id>/delete", methods=["POST"])
@editor_required
def fixtures_delete(fixture_id):
    fixture = db.session.get(Fixture, fixture_id)
    if not fixture:
        abort(404)

    db.session.delete(fixture)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "fixture.delete", "fixture", fixture_id, f"Deleted fixture #{fixture_id}")

    flash("Fixture deleted", "success")
    return redirect(url_for("admin.fixtures_list"))


# === Campus Events (editor and above) ===

@admin_bp.route("/events")
@editor_required
def events_list():
    events = CampusEvent.query.order_by(CampusEvent.start_at.desc()).all()
    return render_template("admin/campus/events_list.html", events=events)


@admin_bp.route("/events/new", methods=["GET", "POST"])
@editor_required
def events_new():
    form = CampusEventForm()
    if form.validate_on_submit():
        slug = _unique_slug(CampusEvent, slugify(form.title.data))
        event = CampusEvent(
            title=form.title.data.strip(),
            slug=slug,
            description=form.description.data,
            event_type=form.event_type.data or None,
            start_at=form.start_at.data,
            end_at=form.end_at.data,
            location=form.location.data,
            organizer=form.organizer.data,
            status=form.status.data,
        )
        if form.image.data and form.image.data.filename:
            event.image = save_upload(form.image.data, "events")

        db.session.add(event)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "event.create", "campus_event", event.id, f"Created '{event.title}'")

        flash(f"Event '{event.title}' created", "success")
        return redirect(url_for("admin.events_list"))

    return render_template("admin/campus/event_form.html", form=form, editing=False)


@admin_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@editor_required
def events_edit(event_id):
    event = db.session.get(CampusEvent, event_id)
    if not event:
        abort(404)

    form = CampusEventForm(obj=event)
    if form.validate_on_submit():
        if form.title.data.strip() != event.title:
            event.slug = _unique_slug(CampusEvent, slugify(form.title.data), exclude_id=event.id)
        event.title = form.title.data.strip()
        event.description = form.description.data
        event.event_type = form.event_type.data or None
        event.start_at = form.start_at.data
        event.end_at = form.end_at.data
        event.location = form.location.data
        event.organizer = form.organizer.data
        event.status = form.status.data

        if form.image.data and form.image.data.filename:
            if event.image:
                delete_upload(event.image)
            event.image = save_upload(form.image.data, "events")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "event.update", "campus_event", event.id, f"Updated '{event.title}'")

        flash(f"Event '{event.title}' updated", "success")
        return redirect(url_for("admin.events_list"))

    return render_template("admin/campus/event_form.html", form=form, editing=True, event=event)


@admin_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@editor_required
def events_delete(event_id):
    event = db.session.get(CampusEvent, event_id)
    if not event:
        abort(404)

    if event.poll:
        flash(
            f"'{event.title}' still has a linked poll. Remove the poll first.",
            "error",
        )
        return redirect(url_for("admin.events_list"))

    if event.image:
        delete_upload(event.image)

    title = event.title
    db.session.delete(event)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "event.delete", "campus_event", event_id, f"Deleted '{title}'")

    flash(f"Event '{title}' deleted", "success")
    return redirect(url_for("admin.events_list"))


# === Students (editor and above) ===

def _populate_student_choices(form: StudentForm) -> None:
    form.house_id.choices = [(0, "— None —")] + [
        (h.id, h.name) for h in House.query.order_by(House.name.asc()).all()
    ]


@admin_bp.route("/students")
@editor_required
def students_list():
    students = StudentProfile.query.order_by(StudentProfile.name.asc()).all()
    return render_template("admin/campus/students_list.html", students=students)


@admin_bp.route("/students/new", methods=["GET", "POST"])
@editor_required
def students_new():
    form = StudentForm()
    _populate_student_choices(form)

    if form.validate_on_submit():
        slug = _unique_slug(StudentProfile, slugify(form.name.data))
        student = StudentProfile(
            name=form.name.data.strip(),
            slug=slug,
            class_or_level=form.class_or_level.data,
            house_id=form.house_id.data or None,
            achievements=form.achievements.data,
            bio=form.bio.data,
            is_featured=form.is_featured.data,
        )
        if form.photo.data and form.photo.data.filename:
            student.photo = save_upload(form.photo.data, "students")

        db.session.add(student)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "student.create", "student_profile", student.id, f"Created '{student.name}'")

        flash(f"Student profile '{student.name}' created", "success")
        return redirect(url_for("admin.students_list"))

    return render_template("admin/campus/student_form.html", form=form, editing=False)


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@editor_required
def students_edit(student_id):
    student = db.session.get(StudentProfile, student_id)
    if not student:
        abort(404)

    form = StudentForm(obj=student)
    _populate_student_choices(form)
    if not form.is_submitted():
        form.house_id.data = student.house_id or 0

    if form.validate_on_submit():
        if form.name.data.strip() != student.name:
            student.slug = _unique_slug(StudentProfile, slugify(form.name.data), exclude_id=student.id)
        student.name = form.name.data.strip()
        student.class_or_level = form.class_or_level.data
        student.house_id = form.house_id.data or None
        student.achievements = form.achievements.data
        student.bio = form.bio.data
        student.is_featured = form.is_featured.data

        if form.photo.data and form.photo.data.filename:
            if student.photo:
                delete_upload(student.photo)
            student.photo = save_upload(form.photo.data, "students")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "student.update", "student_profile", student.id, f"Updated '{student.name}'")

        flash(f"Student profile '{student.name}' updated", "success")
        return redirect(url_for("admin.students_list"))

    return render_template("admin/campus/student_form.html", form=form, editing=True, student=student)


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@editor_required
def students_delete(student_id):
    student = db.session.get(StudentProfile, student_id)
    if not student:
        abort(404)

    if student.photo:
        delete_upload(student.photo)

    name = student.name
    db.session.delete(student)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "student.delete", "student_profile", student_id, f"Deleted '{name}'")

    flash(f"Student profile '{name}' deleted", "success")
    return redirect(url_for("admin.students_list"))


# === Staff (editor and above) ===

@admin_bp.route("/staff")
@editor_required
def staff_list():
    staff = StaffProfile.query.order_by(StaffProfile.name.asc()).all()
    return render_template("admin/campus/staff_list.html", staff=staff)


@admin_bp.route("/staff/new", methods=["GET", "POST"])
@editor_required
def staff_new():
    form = StaffForm()

    if form.validate_on_submit():
        slug = _unique_slug(StaffProfile, slugify(form.name.data))
        staff_member = StaffProfile(
            name=form.name.data.strip(),
            slug=slug,
            role=form.role.data,
            department=form.department.data,
            bio=form.bio.data,
            is_featured=form.is_featured.data,
        )
        if form.photo.data and form.photo.data.filename:
            staff_member.photo = save_upload(form.photo.data, "staff")

        db.session.add(staff_member)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "staff.create", "staff_profile", staff_member.id, f"Created '{staff_member.name}'")

        flash(f"Staff profile '{staff_member.name}' created", "success")
        return redirect(url_for("admin.staff_list"))

    return render_template("admin/campus/staff_form.html", form=form, editing=False)


@admin_bp.route("/staff/<int:staff_id>/edit", methods=["GET", "POST"])
@editor_required
def staff_edit(staff_id):
    staff_member = db.session.get(StaffProfile, staff_id)
    if not staff_member:
        abort(404)

    form = StaffForm(obj=staff_member)
    if form.validate_on_submit():
        if form.name.data.strip() != staff_member.name:
            staff_member.slug = _unique_slug(StaffProfile, slugify(form.name.data), exclude_id=staff_member.id)
        staff_member.name = form.name.data.strip()
        staff_member.role = form.role.data
        staff_member.department = form.department.data
        staff_member.bio = form.bio.data
        staff_member.is_featured = form.is_featured.data

        if form.photo.data and form.photo.data.filename:
            if staff_member.photo:
                delete_upload(staff_member.photo)
            staff_member.photo = save_upload(form.photo.data, "staff")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "staff.update", "staff_profile", staff_member.id, f"Updated '{staff_member.name}'")

        flash(f"Staff profile '{staff_member.name}' updated", "success")
        return redirect(url_for("admin.staff_list"))

    return render_template("admin/campus/staff_form.html", form=form, editing=True, staff_member=staff_member)


@admin_bp.route("/staff/<int:staff_id>/delete", methods=["POST"])
@editor_required
def staff_delete(staff_id):
    staff_member = db.session.get(StaffProfile, staff_id)
    if not staff_member:
        abort(404)

    if staff_member.photo:
        delete_upload(staff_member.photo)

    name = staff_member.name
    db.session.delete(staff_member)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "staff.delete", "staff_profile", staff_id, f"Deleted '{name}'")

    flash(f"Staff profile '{name}' deleted", "success")
    return redirect(url_for("admin.staff_list"))


# === Alumni (editor and above) ===

@admin_bp.route("/alumni")
@editor_required
def alumni_list():
    alumni = AlumniProfile.query.order_by(AlumniProfile.graduation_year.desc().nullslast(), AlumniProfile.name.asc()).all()
    return render_template("admin/campus/alumni_list.html", alumni=alumni)


@admin_bp.route("/alumni/new", methods=["GET", "POST"])
@editor_required
def alumni_new():
    form = AlumniForm()

    if form.validate_on_submit():
        slug = _unique_slug(AlumniProfile, slugify(form.name.data))
        alum = AlumniProfile(
            name=form.name.data.strip(),
            slug=slug,
            graduation_year=form.graduation_year.data,
            current_role=form.current_role.data,
            location=form.location.data,
            story=form.story.data,
            is_featured=form.is_featured.data,
        )
        if form.photo.data and form.photo.data.filename:
            alum.photo = save_upload(form.photo.data, "alumni")

        db.session.add(alum)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "alumni.create", "alumni_profile", alum.id, f"Created '{alum.name}'")

        flash(f"Alumni profile '{alum.name}' created", "success")
        return redirect(url_for("admin.alumni_list"))

    return render_template("admin/campus/alumni_form.html", form=form, editing=False)


@admin_bp.route("/alumni/<int:alumni_id>/edit", methods=["GET", "POST"])
@editor_required
def alumni_edit(alumni_id):
    alum = db.session.get(AlumniProfile, alumni_id)
    if not alum:
        abort(404)

    form = AlumniForm(obj=alum)
    if form.validate_on_submit():
        if form.name.data.strip() != alum.name:
            alum.slug = _unique_slug(AlumniProfile, slugify(form.name.data), exclude_id=alum.id)
        alum.name = form.name.data.strip()
        alum.graduation_year = form.graduation_year.data
        alum.current_role = form.current_role.data
        alum.location = form.location.data
        alum.story = form.story.data
        alum.is_featured = form.is_featured.data

        if form.photo.data and form.photo.data.filename:
            if alum.photo:
                delete_upload(alum.photo)
            alum.photo = save_upload(form.photo.data, "alumni")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "alumni.update", "alumni_profile", alum.id, f"Updated '{alum.name}'")

        flash(f"Alumni profile '{alum.name}' updated", "success")
        return redirect(url_for("admin.alumni_list"))

    return render_template("admin/campus/alumni_form.html", form=form, editing=True, alum=alum)


@admin_bp.route("/alumni/<int:alumni_id>/delete", methods=["POST"])
@editor_required
def alumni_delete(alumni_id):
    alum = db.session.get(AlumniProfile, alumni_id)
    if not alum:
        abort(404)

    if alum.photo:
        delete_upload(alum.photo)

    name = alum.name
    db.session.delete(alum)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "alumni.delete", "alumni_profile", alumni_id, f"Deleted '{name}'")

    flash(f"Alumni profile '{name}' deleted", "success")
    return redirect(url_for("admin.alumni_list"))


# === Galleries / GalleryImage (editor and above) ===

def _populate_gallery_choices(form: GalleryForm) -> None:
    form.event_id.choices = [(0, "— None —")] + [
        (e.id, e.title)
        for e in CampusEvent.query.order_by(CampusEvent.start_at.desc()).all()
    ]


@admin_bp.route("/galleries")
@editor_required
def galleries_list():
    galleries = Gallery.query.order_by(Gallery.created_at.desc()).all()
    return render_template("admin/media/galleries_list.html", galleries=galleries)


@admin_bp.route("/galleries/new", methods=["GET", "POST"])
@editor_required
def galleries_new():
    form = GalleryForm()
    _populate_gallery_choices(form)

    if form.validate_on_submit():
        slug = _unique_slug(Gallery, slugify(form.title.data))
        gallery = Gallery(
            title=form.title.data.strip(),
            slug=slug,
            description=form.description.data,
            event_id=form.event_id.data or None,
            published_at=local_naive_to_utc(form.published_at.data),
        )
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            gallery.cover_image = save_upload(form.cover_image.data, "galleries")

        db.session.add(gallery)
        db.session.flush()

        uploads = [f for f in (form.images.data or []) if f and getattr(f, "filename", None)]
        for order, upload in enumerate(uploads):
            path = save_upload(upload, "galleries")
            db.session.add(GalleryImage(gallery_id=gallery.id, image=path, display_order=order))

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "gallery.create", "gallery", gallery.id, f"Created '{gallery.title}'")

        flash(f"Gallery '{gallery.title}' created", "success")
        return redirect(url_for("admin.galleries_edit", gallery_id=gallery.id))

    return render_template("admin/media/gallery_form.html", form=form, editing=False)


@admin_bp.route("/galleries/<int:gallery_id>/edit", methods=["GET", "POST"])
@editor_required
def galleries_edit(gallery_id):
    gallery = db.session.get(Gallery, gallery_id)
    if not gallery:
        abort(404)

    form = GalleryForm(obj=gallery)
    _populate_gallery_choices(form)
    if not form.is_submitted():
        form.event_id.data = gallery.event_id or 0
        form.published_at.data = utc_to_local_naive(gallery.published_at)

    if form.validate_on_submit():
        if form.title.data.strip() != gallery.title:
            gallery.slug = _unique_slug(Gallery, slugify(form.title.data), exclude_id=gallery.id)
        gallery.title = form.title.data.strip()
        gallery.description = form.description.data
        gallery.event_id = form.event_id.data or None
        gallery.published_at = local_naive_to_utc(form.published_at.data)

        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            if gallery.cover_image:
                delete_upload(gallery.cover_image)
            gallery.cover_image = save_upload(form.cover_image.data, "galleries")

        uploads = [f for f in (form.images.data or []) if f and getattr(f, "filename", None)]
        if uploads:
            next_order = max([img.display_order for img in gallery.images], default=-1) + 1
            for i, upload in enumerate(uploads):
                path = save_upload(upload, "galleries")
                db.session.add(GalleryImage(gallery_id=gallery.id, image=path, display_order=next_order + i))

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "gallery.update", "gallery", gallery.id, f"Updated '{gallery.title}'")

        flash(f"Gallery '{gallery.title}' updated", "success")
        return redirect(url_for("admin.galleries_edit", gallery_id=gallery.id))

    return render_template("admin/media/gallery_form.html", form=form, editing=True, gallery=gallery)


@admin_bp.route("/galleries/<int:gallery_id>/delete", methods=["POST"])
@editor_required
def galleries_delete(gallery_id):
    gallery = db.session.get(Gallery, gallery_id)
    if not gallery:
        abort(404)

    if gallery.cover_image:
        delete_upload(gallery.cover_image)
    for image in gallery.images:
        delete_upload(image.image)

    title = gallery.title
    db.session.delete(gallery)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "gallery.delete", "gallery", gallery_id, f"Deleted '{title}'")

    flash(f"Gallery '{title}' deleted", "success")
    return redirect(url_for("admin.galleries_list"))


@admin_bp.route("/galleries/<int:gallery_id>/images/<int:image_id>/delete", methods=["POST"])
@editor_required
def gallery_image_delete(gallery_id, image_id):
    gallery = db.session.get(Gallery, gallery_id)
    if not gallery:
        abort(404)

    image = db.session.get(GalleryImage, image_id)
    if not image or image.gallery_id != gallery.id:
        abort(404)

    delete_upload(image.image)
    db.session.delete(image)
    db.session.commit()

    flash("Image removed", "success")
    return redirect(url_for("admin.galleries_edit", gallery_id=gallery_id))


# === Videos (editor and above) ===

def _populate_video_choices(form: VideoForm) -> None:
    form.category_id.choices = [(0, "— None —")] + [
        (c.id, c.name)
        for c in Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    ]


@admin_bp.route("/videos")
@editor_required
def videos_list():
    videos = Video.query.order_by(Video.published_at.desc().nullslast()).all()
    return render_template("admin/media/videos_list.html", videos=videos)


@admin_bp.route("/videos/new", methods=["GET", "POST"])
@editor_required
def videos_new():
    form = VideoForm()
    _populate_video_choices(form)

    if form.validate_on_submit():
        if not (form.video_file.data and form.video_file.data.filename):
            flash("A video file is required", "error")
            return render_template("admin/media/video_form.html", form=form, editing=False)

        slug = _unique_slug(Video, slugify(form.title.data))
        video = Video(
            title=form.title.data.strip(),
            slug=slug,
            description=form.description.data,
            video_url=save_upload(form.video_file.data, "videos"),
            duration=form.duration.data,
            category_id=form.category_id.data or None,
            author_id=current_user.id,
            published_at=local_naive_to_utc(form.published_at.data),
        )
        if form.thumbnail.data and form.thumbnail.data.filename:
            video.thumbnail = save_upload(form.thumbnail.data, "videos")

        db.session.add(video)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "video.create", "video", video.id, f"Created '{video.title}'")

        flash(f"Video '{video.title}' created", "success")
        return redirect(url_for("admin.videos_list"))

    return render_template("admin/media/video_form.html", form=form, editing=False)


@admin_bp.route("/videos/<int:video_id>/edit", methods=["GET", "POST"])
@editor_required
def videos_edit(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        abort(404)

    form = VideoForm(obj=video)
    _populate_video_choices(form)
    if not form.is_submitted():
        form.category_id.data = video.category_id or 0
        form.published_at.data = utc_to_local_naive(video.published_at)

    if form.validate_on_submit():
        if form.title.data.strip() != video.title:
            video.slug = _unique_slug(Video, slugify(form.title.data), exclude_id=video.id)
        video.title = form.title.data.strip()
        video.description = form.description.data
        video.duration = form.duration.data
        video.category_id = form.category_id.data or None
        video.published_at = local_naive_to_utc(form.published_at.data)

        if form.video_file.data and form.video_file.data.filename:
            delete_upload(video.video_url)
            video.video_url = save_upload(form.video_file.data, "videos")

        if form.thumbnail.data and form.thumbnail.data.filename:
            if video.thumbnail:
                delete_upload(video.thumbnail)
            video.thumbnail = save_upload(form.thumbnail.data, "videos")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "video.update", "video", video.id, f"Updated '{video.title}'")

        flash(f"Video '{video.title}' updated", "success")
        return redirect(url_for("admin.videos_list"))

    return render_template("admin/media/video_form.html", form=form, editing=True, video=video)


@admin_bp.route("/videos/<int:video_id>/delete", methods=["POST"])
@editor_required
def videos_delete(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        abort(404)

    if video.video_url:
        delete_upload(video.video_url)
    if video.thumbnail:
        delete_upload(video.thumbnail)

    title = video.title
    db.session.delete(video)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "video.delete", "video", video_id, f"Deleted '{title}'")

    flash(f"Video '{title}' deleted", "success")
    return redirect(url_for("admin.videos_list"))


# === Podcast Episodes (editor and above) ===

@admin_bp.route("/podcasts")
@editor_required
def podcasts_list():
    episodes = PodcastEpisode.query.order_by(PodcastEpisode.published_at.desc().nullslast()).all()
    return render_template("admin/media/podcasts_list.html", episodes=episodes)


@admin_bp.route("/podcasts/new", methods=["GET", "POST"])
@editor_required
def podcasts_new():
    form = PodcastEpisodeForm()

    if form.validate_on_submit():
        if not (form.audio_file.data and form.audio_file.data.filename):
            flash("An audio file is required", "error")
            return render_template("admin/media/podcast_form.html", form=form, editing=False)

        slug = _unique_slug(PodcastEpisode, slugify(form.title.data))
        audio_path = save_upload(form.audio_file.data, "podcasts")
        episode = PodcastEpisode(
            title=form.title.data.strip(),
            slug=slug,
            description=form.description.data,
            audio_url=audio_path,
            duration=form.duration.data or get_audio_duration(audio_path),
            episode_number=form.episode_number.data,
            published_at=local_naive_to_utc(form.published_at.data),
        )
        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            episode.cover_image = save_upload(form.cover_image.data, "podcasts")

        db.session.add(episode)
        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "podcast.create", "podcast_episode", episode.id, f"Created '{episode.title}'")

        flash(f"Episode '{episode.title}' created", "success")
        return redirect(url_for("admin.podcasts_list"))

    return render_template("admin/media/podcast_form.html", form=form, editing=False)


@admin_bp.route("/podcasts/<int:episode_id>/edit", methods=["GET", "POST"])
@editor_required
def podcasts_edit(episode_id):
    episode = db.session.get(PodcastEpisode, episode_id)
    if not episode:
        abort(404)

    form = PodcastEpisodeForm(obj=episode)
    if not form.is_submitted():
        form.published_at.data = utc_to_local_naive(episode.published_at)

    if form.validate_on_submit():
        if form.title.data.strip() != episode.title:
            episode.slug = _unique_slug(PodcastEpisode, slugify(form.title.data), exclude_id=episode.id)
        episode.title = form.title.data.strip()
        episode.description = form.description.data
        episode.episode_number = form.episode_number.data
        episode.published_at = local_naive_to_utc(form.published_at.data)

        if form.audio_file.data and form.audio_file.data.filename:
            delete_upload(episode.audio_url)
            audio_path = save_upload(form.audio_file.data, "podcasts")
            episode.audio_url = audio_path
            episode.duration = form.duration.data or get_audio_duration(audio_path)
        else:
            episode.duration = form.duration.data or episode.duration

        if form.cover_image.data and getattr(form.cover_image.data, "filename", None):
            if episode.cover_image:
                delete_upload(episode.cover_image)
            episode.cover_image = save_upload(form.cover_image.data, "podcasts")

        db.session.commit()

        from app.services.activity_service import log_activity
        log_activity(current_user.id, "podcast.update", "podcast_episode", episode.id, f"Updated '{episode.title}'")

        flash(f"Episode '{episode.title}' updated", "success")
        return redirect(url_for("admin.podcasts_list"))

    return render_template("admin/media/podcast_form.html", form=form, editing=True, episode=episode)


@admin_bp.route("/podcasts/<int:episode_id>/delete", methods=["POST"])
@editor_required
def podcasts_delete(episode_id):
    episode = db.session.get(PodcastEpisode, episode_id)
    if not episode:
        abort(404)

    if episode.audio_url:
        delete_upload(episode.audio_url)
    if episode.cover_image:
        delete_upload(episode.cover_image)

    title = episode.title
    db.session.delete(episode)
    db.session.commit()

    from app.services.activity_service import log_activity
    log_activity(current_user.id, "podcast.delete", "podcast_episode", episode_id, f"Deleted '{title}'")

    flash(f"Episode '{title}' deleted", "success")
    return redirect(url_for("admin.podcasts_list"))
