from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.content import Article, Category, Tag, TagRelation


def public_articles_query():
    """Base query for articles visible to the public."""
    return Article.query.filter(
        Article.status == Article.STATUS_PUBLISHED,
        Article.is_audited.is_(True),
        db.or_(
            Article.published_at.is_(None),
            Article.published_at <= datetime.now(timezone.utc),
        ),
    )


def get_public_article_by_slug(slug: str) -> Article | None:
    return public_articles_query().filter(Article.slug == slug).first()


def list_articles(
    category_slug: str = None,
    author_slug: str = None,
    tag_slug: str = None,
    content_type: str = None,
    is_campus: bool = None,
    campus_section: str = None,
    page: int = 1,
    per_page: int = 12,
):
    q = public_articles_query()

    if category_slug:
        q = q.join(Category).filter(Category.slug == category_slug)
    if content_type:
        q = q.filter(Article.content_type == content_type)
    if is_campus is not None:
        q = q.filter(Article.is_campus == is_campus)
    if campus_section:
        q = q.filter(Article.campus_section == campus_section)

    if author_slug:
        from app.models.user import AuthorProfile
        q = q.join(AuthorProfile, Article.author_id == AuthorProfile.user_id)\
               .filter(AuthorProfile.slug == author_slug)

    if tag_slug:
        q = q.join(TagRelation).join(Tag).filter(Tag.slug == tag_slug)

    return q.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)


def get_related_articles(article: Article, limit: int = 4):
    """Related by shared tags, then same category, excluding self."""
    tag_ids = [tr.tag_id for tr in article.tag_relations]

    if tag_ids:
        related = public_articles_query()\
            .join(TagRelation)\
            .filter(TagRelation.tag_id.in_(tag_ids))\
            .filter(Article.id != article.id)
    elif article.category_id:
        related = public_articles_query()\
            .filter(Article.category_id == article.category_id, Article.id != article.id)
    else:
        return []

    return related.order_by(Article.published_at.desc().nullslast()).limit(limit).all()