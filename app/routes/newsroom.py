"""
Newsroom blueprint — every logged-in account's personal workspace.

The /admin backend (admin.py) is the editorial *management* console and is
gated to editor-and-above (see app.utils.decorators.editor_required). That
left teacher_editor, author, student_journalist, student_contributor, and
alumni_contributor accounts with a login but nowhere to go and no way to
write anything. This blueprint gives every authenticated role:

  - a personal dashboard showing the status of their own articles
  - an article submission form (draft / submit for review)

Publishing controls and newsroom-wide curation flags (Featured, Breaking,
Editor's Pick) remain restricted to editor-and-above, matching the
separation-of-duties rules already enforced in app.services.article_service.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.articles import ArticleForm
from app.models.content import Article, Category
from app.models.editorial import SpecialEdition
from app.models.campus import House, Club
from app.models.user import User
from app.services.article_service import (
    create_article,
    update_article,
    submit_for_review,
    add_gallery_images,
    remove_gallery_image,
    set_article_poll,
    remove_article_poll,
)
from app.services.youtube_service import get_latest_videos, normalize_video_id
from app.services.media_service import (
    save_upload,
    get_audio_duration,
    validate_upload,
)


newsroom_bp = Blueprint(
    "newsroom",
    __name__,
    url_prefix="/newsroom",
)


def _is_staff() -> bool:
    """Editor-and-above already have the full /admin console."""
    return current_user.is_at_least(User.ROLE_EDITOR)


def _populate_choices(form: ArticleForm) -> None:
    form.category_id.choices = [(0, "— None —")] + [
        (c.id, c.name)
        for c in Category.query.filter_by(is_active=True).all()
    ]

    form.special_edition_id.choices = [(0, "— None —")] + [(e.id, e.title) for e in SpecialEdition.query.filter_by(is_active=True).order_by(SpecialEdition.title.asc()).all()]

    form.house_id.choices = [(0, "— None —")] + [
        (h.id, h.name)
        for h in House.query.filter_by(is_active=True).all()
    ]

    form.club_id.choices = [(0, "— None —")] + [
        (c.id, c.name)
        for c in Club.query.filter_by(is_active=True).all()
    ]


def _strip_staff_only_fields(form: ArticleForm) -> None:
    """Contributors can't self-publish or set newsroom curation flags."""
    del form.submit_publish
    del form.is_featured
    del form.is_breaking
    del form.is_editors_pick


@newsroom_bp.route("/")
@login_required
def dashboard():
    my_articles = (
        Article.query
        .filter_by(author_id=current_user.id)
        .order_by(Article.created_at.desc())
        .limit(25)
        .all()
    )

    counts = {
        status: Article.query.filter_by(
            author_id=current_user.id,
            status=status,
        ).count()
        for status in (
            Article.STATUS_DRAFT,
            Article.STATUS_PENDING_REVIEW,
            Article.STATUS_PENDING_AUDIT,
            Article.STATUS_PUBLISHED,
            Article.STATUS_REJECTED,
        )
    }

    return render_template(
        "newsroom/dashboard.html",
        articles=my_articles,
        counts=counts,
        is_staff=_is_staff(),
    )


@newsroom_bp.route("/articles/new", methods=["GET", "POST"])
@login_required
def articles_new():
    form = ArticleForm()

    _populate_choices(form)

    is_staff = _is_staff()

    if not is_staff:
        _strip_staff_only_fields(form)

    youtube_videos = get_latest_videos(limit=12)

    if form.validate_on_submit():
        data = form.data.copy()
        data["special_edition_id"] = data.get("special_edition_id") or None

        # ==============================
        # FEATURED IMAGE UPLOAD
        # ==============================
        featured_image = form.featured_image.data

        if (
            featured_image
            and hasattr(featured_image, "filename")
            and featured_image.filename
        ):
            data["featured_image"] = save_upload(
                featured_image,
                "articles",
            )

        # ==============================
        # AUDIO UPLOAD
        # ==============================
        audio_file = form.audio_file.data

        if (
            audio_file
            and hasattr(audio_file, "filename")
            and audio_file.filename
        ):
            audio_path = save_upload(
                audio_file,
                "audio",
            )

            data["audio_url"] = audio_path
            data["audio_duration"] = get_audio_duration(
                audio_path
            )

        # ==============================
        # YOUTUBE VIDEO
        # ==============================
        manual_youtube = (data.get("youtube_video_url") or "").strip()
        selected_youtube = data.get("youtube_video_id")
        data["youtube_video_id"] = normalize_video_id(manual_youtube or selected_youtube)

        # ==============================
        # TAGS
        # ==============================
        data["tags"] = [
            t.strip()
            for t in data.get("tags", "").split(",")
            if t.strip()
        ]

        # ==============================
        # CREATE ARTICLE
        # ==============================
        article = create_article(
            data,
            current_user.id,
        )

        # ==============================
        # ADDITIONAL GALLERY IMAGES
        # ==============================
        gallery_uploads = [
            f for f in (form.gallery_images.data or [])
            if f and hasattr(f, "filename") and f.filename
        ]
        if gallery_uploads:
            saved_paths = [save_upload(f, "articles") for f in gallery_uploads]
            add_gallery_images(article, saved_paths)

        # ==============================
        # POLL
        # ==============================
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

        # ==============================
        # STAFF-ONLY CURATION FLAGS
        # ==============================
        if is_staff:
            for flag in (
                "is_featured",
                "is_breaking",
                "is_editors_pick",
            ):
                setattr(
                    article,
                    flag,
                    data.get(flag, False),
                )

        # ==============================
        # ARTICLE STATUS ACTIONS
        # ==============================
        if form.submit_review.data:
            submit_for_review(article)

            flash(
                "Article submitted for review",
                "success",
            )

        elif is_staff and form.submit_publish.data:
            article.status = Article.STATUS_PUBLISHED
            article.is_audited = True
            article.audited_by_id = current_user.id
            article.published_at = db.func.now()

            db.session.commit()

            flash(
                "Article published",
                "success",
            )

        else:
            db.session.commit()

            flash(
                "Draft saved",
                "success",
            )

        return redirect(
            url_for("newsroom.dashboard")
        )

    return render_template(
        "newsroom/article_form.html",
        form=form,
        editing=False,
        is_staff=is_staff,
        youtube_videos=youtube_videos,
    )


@newsroom_bp.route(
    "/articles/<int:article_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def articles_edit(article_id):
    article = db.session.get(
        Article,
        article_id,
    )

    if (
        not article
        or article.author_id != current_user.id
    ):
        abort(404)

    is_staff = _is_staff()

    # Prevent editing articles already in review/publishing pipeline
    if article.status not in (
        Article.STATUS_DRAFT,
        Article.STATUS_REJECTED,
    ):
        flash(
            "This article is already in the review pipeline "
            "and can no longer be edited here.",
            "warning",
        )

        return redirect(
            url_for("newsroom.dashboard")
        )

    # ==========================================
    # INITIALIZE FORM WITH EXISTING ARTICLE DATA
    # ==========================================
    form = ArticleForm(
        obj=article
    )

    _populate_choices(form)

    if not is_staff:
        _strip_staff_only_fields(form)

    youtube_videos = get_latest_videos(limit=12)

    # ==========================================
    # POPULATE TAGS FOR GET REQUEST
    # ==========================================
    if not form.is_submitted():
        form.tags.data = ", ".join(
            tag.name
            for tag in article.tags
        )
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

    # ==========================================
    # HANDLE FORM SUBMISSION
    # ==========================================
    if form.validate_on_submit():
        data = form.data.copy()
        data["special_edition_id"] = data.get("special_edition_id") or None

        # ======================================
        # FEATURED IMAGE
        # ======================================
        # On an edit form, WTForms may contain
        # the existing database path as a string.
        # Only process actual uploaded files.
        featured_image = form.featured_image.data

        if (
            featured_image
            and hasattr(featured_image, "filename")
            and featured_image.filename
        ):
            data["featured_image"] = save_upload(
                featured_image,
                "articles",
            )

        else:
            # Keep the existing image
            data["featured_image"] = (
                article.featured_image
            )

        # ======================================
        # AUDIO FILE
        # ======================================
        # Only process an actual uploaded file.
        audio_file = form.audio_file.data

        if (
            audio_file
            and hasattr(audio_file, "filename")
            and audio_file.filename
        ):
            audio_path = save_upload(
                audio_file,
                "audio",
            )

            data["audio_url"] = audio_path

            data["audio_duration"] = (
                get_audio_duration(
                    audio_path
                )
            )

        else:
            # Keep existing audio
            data["audio_url"] = article.audio_url

            data["audio_duration"] = (
                article.audio_duration
            )

        # ======================================
        # YOUTUBE VIDEO
        # ======================================
        manual_youtube = (data.get("youtube_video_url") or "").strip()
        selected_youtube = data.get("youtube_video_id")
        data["youtube_video_id"] = normalize_video_id(manual_youtube or selected_youtube)

        # ======================================
        # TAGS
        # ======================================
        data["tags"] = [
            t.strip()
            for t in data.get("tags", "").split(",")
            if t.strip()
        ]

        # ======================================
        # UPDATE ARTICLE
        # ======================================
        update_article(
            article,
            data,
        )

        # ======================================
        # ADDITIONAL GALLERY IMAGES
        # ======================================
        gallery_uploads = [
            f for f in (form.gallery_images.data or [])
            if f and hasattr(f, "filename") and f.filename
        ]
        if gallery_uploads:
            saved_paths = [save_upload(f, "articles") for f in gallery_uploads]
            add_gallery_images(article, saved_paths)

        # ======================================
        # POLL
        # ======================================
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

        # ======================================
        # SUBMIT FOR REVIEW OR SAVE DRAFT
        # ======================================
        if form.submit_review.data:
            submit_for_review(article)

            flash(
                "Article submitted for review",
                "success",
            )

        else:
            flash(
                "Draft saved",
                "success",
            )

        return redirect(
            url_for("newsroom.dashboard")
        )

    return render_template(
        "newsroom/article_form.html",
        form=form,
        editing=True,
        is_staff=is_staff,
        article=article,
        youtube_videos=youtube_videos,
    )


@newsroom_bp.route(
    "/articles/<int:article_id>/images/<int:image_id>/delete",
    methods=["POST"],
)
@login_required
def article_image_delete(article_id, image_id):
    article = db.session.get(Article, article_id)

    if not article or article.author_id != current_user.id:
        abort(404)

    if article.status not in (Article.STATUS_DRAFT, Article.STATUS_REJECTED):
        flash(
            "This article is already in the review pipeline "
            "and can no longer be edited here.",
            "warning",
        )
        return redirect(url_for("newsroom.dashboard"))

    try:
        remove_gallery_image(article, image_id)
        flash("Image removed", "success")
    except ValueError:
        flash("Image not found", "error")

    return redirect(url_for("newsroom.articles_edit", article_id=article_id))


@newsroom_bp.route("/editor/upload-image", methods=["POST"])
@login_required
def editor_upload_image():
    """
    Inline image upload for the article body editor (TipTap).

    Any authenticated newsroom account can use this while drafting an
    article — it just saves the file and hands back a URL, it does not
    touch any Article record. Returns JSON so the editor's JS can insert
    the image without a page reload.
    """
    upload = request.files.get("file")

    if not upload or not upload.filename:
        return jsonify({"error": "No file provided"}), 400

    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        return jsonify({"error": "Only JPG, PNG, and WEBP images are allowed"}), 400

    is_valid, error = validate_upload(upload)
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        path = save_upload(upload, "articles")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"url": "/" + path})