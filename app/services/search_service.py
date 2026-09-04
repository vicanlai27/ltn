import re

from app.extensions import db
from app.models.content import Article, Category, Tag, TagRelation
from app.models.user import User, AuthorProfile
from app.repositories.articles import public_articles_query


def _tokenize(q: str) -> list[str]:
    """Split a search query into individual words, dropping empties."""
    return [t for t in re.split(r"\s+", q.strip()) if t]


def search_articles(
    q: str,
    category_slug: str | None = None,
    content_type: str | None = None,
    page: int = 1,
    per_page: int = 12,
):
    """
    Search articles by relevance across more than just the article's own
    text: matches against tags and author name too, so a search for e.g.
    a reporter's name or a topic tag surfaces related stories even when
    those exact words aren't in the title or body.

    Each word in the query must match *somewhere* (title/excerpt/body/
    tag/author) -- not necessarily the same field -- so multi-word
    queries find articles where the words are scattered across related
    fields (e.g. tag "basketball" + author "Nkurunziza"). Matching is
    done via correlated EXISTS subqueries rather than joins, so results
    stay one-row-per-article (no fan-out from articles with many tags)
    without needing a DISTINCT that Postgres would reject alongside an
    ORDER BY on columns outside the select list.

    SQLite-compatible LIKE search. Future-ready: swap for PostgreSQL
    full-text search or Meilisearch without changing the call site.
    """
    query = public_articles_query()

    if category_slug:
        query = query.join(Category, Category.id == Article.category_id) \
            .filter(Category.slug == category_slug)

    if content_type:
        query = query.filter(Article.content_type == content_type)

    if q:
        tokens = _tokenize(q)

        def matches(pattern):
            return db.or_(
                Article.title.ilike(pattern),
                Article.excerpt.ilike(pattern),
                Article.body.ilike(pattern),
                Article.tag_relations.any(TagRelation.tag.has(Tag.name.ilike(pattern))),
                Article.author.has(db.or_(
                    User.username.ilike(pattern),
                    User.author_profile.has(AuthorProfile.display_name.ilike(pattern)),
                )),
            )

        for token in tokens:
            query = query.filter(matches(f"%{token}%"))

        # A match in the title (or an exact tag hit) is a stronger signal
        # of relevance than a word merely appearing somewhere in the body.
        full_pattern = f"%{q.strip()}%"
        relevance = db.case(
            (Article.title.ilike(full_pattern), 0),
            (Article.tag_relations.any(TagRelation.tag.has(Tag.name.ilike(full_pattern))), 1),
            (Article.excerpt.ilike(full_pattern), 2),
            else_=3,
        )

        query = query.order_by(relevance, Article.published_at.desc().nullslast())
    else:
        query = query.order_by(Article.published_at.desc().nullslast())

    return query.paginate(page=page, per_page=per_page, error_out=False)
