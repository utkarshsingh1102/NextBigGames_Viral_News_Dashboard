"""Parser and handler for incoming WhatsApp commands."""

import logging

from sqlalchemy.orm import Session

from app.models.news import ViralGamingNews
from app.services.keyword_filter import TAG_RULES

logger = logging.getLogger(__name__)


def _format_article(article: ViralGamingNews) -> str:
    tags = ", ".join(article.tags or []) or "—"
    return (
        f"\U0001f4f0 *{article.title}*\n"
        f"Source: {article.source}\n"
        f"Tags: {tags}\n"
        f"Score: {article.virality_score:.1f}\n"
        f"{article.url}"
    )


def handle_command(body: str, db: Session) -> str:
    """Parse an incoming WhatsApp message body and return a reply string."""
    text = body.strip()
    lower = text.lower()
    logger.info("WhatsApp command received: %r", text)

    # "tags" — list all available tags
    if lower == "tags":
        tag_names = [tag for tag, _ in TAG_RULES]
        lines = (
            ["*Available tags:*"]
            + tag_names
            + ["\nReply with:\narticles <tag>\n\nExample:\narticles HybridCasual"]
        )
        return "\n".join(lines)

    # "articles" — latest 5 articles (no filter)
    if lower == "articles":
        articles = (
            db.query(ViralGamingNews)
            .order_by(ViralGamingNews.created_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            return "No articles found."
        return "\n\n---\n\n".join(_format_article(a) for a in articles)

    # "articles <tag>" — latest 5 articles filtered by tag
    if lower.startswith("articles "):
        tag = text[len("articles "):].strip()
        articles = (
            db.query(ViralGamingNews)
            .filter(ViralGamingNews.tags.contains([tag]))
            .order_by(ViralGamingNews.created_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            return f"No articles found for tag: {tag}"
        return "\n\n---\n\n".join(_format_article(a) for a in articles)

    # Unknown command — show help
    return (
        "\U0001f44b *Viral Gaming News Bot*\n\n"
        "Available commands:\n"
        "- *articles* — latest 5 viral articles\n"
        "- *tags* — list all available tags\n"
        "- *articles <tag>* — articles for a specific tag\n\n"
        "Example: articles Funding"
    )
