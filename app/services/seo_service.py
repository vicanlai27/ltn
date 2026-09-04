from flask import request, url_for

from app.models.content import Article


def canonical_url(endpoint: str, **values) -> str:
    return request.host_url.rstrip("/") + url_for(endpoint, _external=False, **values)


def article_meta(article: Article) -> dict:
    """Build OpenGraph + Twitter Card + NewsArticle schema dict."""
    image = None
    if article.featured_image:
        image = request.host_url.rstrip("/") + "/" + article.featured_image.lstrip("/")

    return {
        "title": article.title,
        "description": article.excerpt or "",
        "url": canonical_url("public.article", slug=article.slug),
        "image": image,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        "author": article.author.author_profile.display_name if article.author and article.author.author_profile else None,
        "content_type": article.content_type,
        "site_name": "Lavisco News",
    }


def structured_data_article(article: Article) -> dict:
    """NewsArticle schema.org JSON-LD."""
    data = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": article.title,
        "description": article.excerpt or "",
        "datePublished": article.published_at.isoformat() if article.published_at else article.created_at.isoformat(),
        "dateModified": article.updated_at.isoformat() if article.updated_at else None,
        "url": canonical_url("public.article", slug=article.slug),
    }
    if article.featured_image:
        data["image"] = request.host_url.rstrip("/") + "/" + article.featured_image.lstrip("/")
    if article.author and article.author.author_profile:
        data["author"] = {
            "@type": "Person",
            "name": article.author.author_profile.display_name,
        }
    data["publisher"] = {
        "@type": "Organization",
        "name": "Lavisco News",
        "logo": {
            "@type": "ImageObject",
            "url": request.host_url.rstrip("/") + "/static/images/logo.png",
        },
    }
    return data