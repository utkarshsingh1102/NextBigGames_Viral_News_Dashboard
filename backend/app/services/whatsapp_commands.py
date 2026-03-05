"""WhatsApp command handler with stateful numbered-menu conversation flow.

Conversation states per sender (keyed by phone number, stored in-memory):
  idle                    → no active menu
  awaiting_tag            → showed tag list, waiting for number selection
  awaiting_source         → showed source list, waiting for number selection
  awaiting_article_select → showed articles, waiting for comma-separated numbers

Flow examples
─────────────
  User: "articles"
  Bot:  numbered list of latest NOT_POSTED articles
  User: "1,3"
  Bot:  "✅ 2 articles queued"  → status set to IN_QUEUE

  User: "tags"
  Bot:  numbered tag list
  User: "2"
  Bot:  numbered articles filtered by that tag
  User: "all"
  Bot:  "✅ N articles queued"

  User: "source"
  Bot:  numbered source list
  User: "1"
  Bot:  numbered articles from that source
  User: "2"
  Bot:  "✅ 1 article queued"
"""

import logging
import uuid as _uuid

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.models.news import ArticleStatus, ViralGamingNews
from app.services.keyword_filter import TAG_RULES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory session state  {phone_number: {step, ...}}
# ---------------------------------------------------------------------------

_sessions: dict[str, dict] = {}

_HELP = (
    "\U0001f916 *Viral Gaming News Bot*\n\n"
    "Commands:\n"
    "• *articles* — browse & queue latest articles\n"
    "• *tags* — filter articles by tag\n"
    "• *source* — filter articles by source\n"
    "• *cancel* — exit current menu\n"
    "• *help* — show this message"
)

MAX_ARTICLES = 10  # max articles shown per menu page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear(phone: str) -> None:
    _sessions.pop(phone, None)


def _state(phone: str) -> dict:
    return _sessions.get(phone, {})


def _save(phone: str, data: dict) -> None:
    _sessions[phone] = data


def _short_title(title: str, max_len: int = 65) -> str:
    return (title[:max_len] + "…") if len(title) > max_len else title


def _articles_menu(articles: list[ViralGamingNews], header: str = "") -> str:
    lines = []
    if header:
        lines.append(header + "\n")
    lines.append("📋 *Select articles to queue:*\n")
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {_short_title(a.title)} _(score {a.virality_score:.1f})_")
    lines += [
        "",
        "Reply with numbers separated by commas *(e.g. 1,3)* or *all*",
        "Reply *cancel* to exit",
    ]
    return "\n".join(lines)


def _tags_menu() -> str:
    tag_names = [t for t, _ in TAG_RULES]
    lines = ["🏷️ *Select a tag:*\n"]
    for i, t in enumerate(tag_names, 1):
        lines.append(f"{i}. {t}")
    lines += ["", "Reply with a tag number", "Reply *cancel* to exit"]
    return "\n".join(lines)


def _sources_menu(db: Session) -> tuple[str, list[str]]:
    rows = db.query(distinct(ViralGamingNews.source)).order_by(ViralGamingNews.source).all()
    sources = [r[0] for r in rows]
    if not sources:
        return "No sources available yet.", []
    lines = ["📡 *Select a source:*\n"]
    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. {s}")
    lines += ["", "Reply with a source number", "Reply *cancel* to exit"]
    return "\n".join(lines), sources


def _queue(db: Session, article_ids: list[str]) -> int:
    """Set status to IN_QUEUE for the given article UUIDs. Returns count queued."""
    count = 0
    for id_str in article_ids:
        record = db.query(ViralGamingNews).filter(
            ViralGamingNews.id == _uuid.UUID(id_str)
        ).first()
        if record:
            record.status = ArticleStatus.IN_QUEUE
            count += 1
    db.commit()
    return count


def _parse_selection(text: str, max_idx: int) -> list[int] | None:
    """Parse '1,3,5' or 'all' into 0-based indices. Returns None on bad input."""
    lower = text.strip().lower()
    if lower == "all":
        return list(range(max_idx))
    try:
        indices = [int(x.strip()) - 1 for x in lower.split(",")]
        if any(i < 0 or i >= max_idx for i in indices):
            return None
        return indices
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def handle_command(body: str, from_number: str, db: Session) -> str:
    """Parse an incoming WhatsApp message and return a reply string."""
    text = body.strip()
    lower = text.lower()
    logger.info("WhatsApp [%s]: %r", from_number, text)

    # cancel / help always escape any active session
    if lower == "cancel":
        _clear(from_number)
        return "Menu closed.\n\n" + _HELP

    if lower in ("help", "hi", "hello", "start", "menu"):
        _clear(from_number)
        return _HELP

    session = _state(from_number)
    step = session.get("step")

    # ── No active session ────────────────────────────────────────────────────

    if not step:
        if lower == "articles":
            articles = (
                db.query(ViralGamingNews)
                .filter(ViralGamingNews.status == ArticleStatus.NOT_POSTED)
                .order_by(ViralGamingNews.virality_score.desc())
                .limit(MAX_ARTICLES)
                .all()
            )
            if not articles:
                return "No unposted articles found right now. Try again after the next scan."

            _save(from_number, {
                "step": "awaiting_article_select",
                "ids": [str(a.id) for a in articles],
            })
            return _articles_menu(articles)

        if lower == "tags":
            tag_names = [t for t, _ in TAG_RULES]
            if not tag_names:
                return "No tags configured."
            _save(from_number, {"step": "awaiting_tag", "tags": tag_names})
            return _tags_menu()

        if lower == "source":
            menu, sources = _sources_menu(db)
            if not sources:
                return menu
            _save(from_number, {"step": "awaiting_source", "sources": sources})
            return menu

        return _HELP

    # ── Awaiting tag selection ───────────────────────────────────────────────

    if step == "awaiting_tag":
        tag_names = session["tags"]
        indices = _parse_selection(text, len(tag_names))
        if indices is None or len(indices) != 1:
            return f"Please reply with a single number between 1 and {len(tag_names)}."

        selected_tag = tag_names[indices[0]]
        articles = (
            db.query(ViralGamingNews)
            .filter(
                ViralGamingNews.tags.contains([selected_tag]),
                ViralGamingNews.status == ArticleStatus.NOT_POSTED,
            )
            .order_by(ViralGamingNews.virality_score.desc())
            .limit(MAX_ARTICLES)
            .all()
        )
        if not articles:
            _clear(from_number)
            return f"No unposted articles found for tag *{selected_tag}*."

        _save(from_number, {
            "step": "awaiting_article_select",
            "ids": [str(a.id) for a in articles],
        })
        return _articles_menu(articles, header=f"🏷️ Articles tagged *{selected_tag}*")

    # ── Awaiting source selection ────────────────────────────────────────────

    if step == "awaiting_source":
        sources = session["sources"]
        indices = _parse_selection(text, len(sources))
        if indices is None or len(indices) != 1:
            return f"Please reply with a single number between 1 and {len(sources)}."

        selected_source = sources[indices[0]]
        articles = (
            db.query(ViralGamingNews)
            .filter(
                ViralGamingNews.source == selected_source,
                ViralGamingNews.status == ArticleStatus.NOT_POSTED,
            )
            .order_by(ViralGamingNews.virality_score.desc())
            .limit(MAX_ARTICLES)
            .all()
        )
        if not articles:
            _clear(from_number)
            return f"No unposted articles found from *{selected_source}*."

        _save(from_number, {
            "step": "awaiting_article_select",
            "ids": [str(a.id) for a in articles],
        })
        return _articles_menu(articles, header=f"📡 Articles from *{selected_source}*")

    # ── Awaiting article selection ───────────────────────────────────────────

    if step == "awaiting_article_select":
        article_ids = session["ids"]
        indices = _parse_selection(text, len(article_ids))
        if indices is None:
            return (
                f"Please reply with numbers between 1 and {len(article_ids)}, "
                "separated by commas (e.g. *1,3*), or *all*.\n"
                "Reply *cancel* to exit."
            )

        selected_ids = [article_ids[i] for i in indices]
        queued = _queue(db, selected_ids)
        _clear(from_number)

        return (
            f"✅ *{queued} article(s) added to queue!*\n\n"
            "Send *articles*, *tags*, or *source* to continue."
        )

    # Fallback — stale/unknown session state
    _clear(from_number)
    return _HELP
