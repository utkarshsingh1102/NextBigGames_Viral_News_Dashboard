"""WhatsApp notification service using Twilio."""

import logging
import os

logger = logging.getLogger(__name__)

_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
_FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")  # e.g. +14155238886

# Comma-separated list of recipient numbers, e.g. "+919876543210,+14155551234"
_TO_NUMBERS: list[str] = [
    n.strip()
    for n in os.getenv("USER_WHATSAPP_NUMBERS", "").split(",")
    if n.strip()
]


def _get_client():
    """Lazily import and return a Twilio REST client."""
    from twilio.rest import Client
    return Client(_ACCOUNT_SID, _AUTH_TOKEN)


def _format_message(article: dict) -> str:
    tags = ", ".join(article.get("tags") or []) or "—"
    score = article.get("virality_score", 0)
    return (
        f"\U0001f6a8 *Viral Gaming News*\n\n"
        f"*Title:*\n{article['title']}\n\n"
        f"*Source:*\n{article['source']}\n\n"
        f"*Tags:*\n{tags}\n\n"
        f"*Score:*\n{score:.1f}\n\n"
        f"*Read:*\n{article['url']}"
    )


def send_article(article: dict) -> None:
    """Send a single article as a WhatsApp message to all configured recipients."""
    if not _ACCOUNT_SID or not _AUTH_TOKEN or not _FROM_NUMBER:
        logger.warning("Twilio credentials not configured — skipping WhatsApp notification.")
        return
    if not _TO_NUMBERS:
        logger.warning("USER_WHATSAPP_NUMBERS not set — skipping WhatsApp notification.")
        return

    body = _format_message(article)
    client = _get_client()

    for number in _TO_NUMBERS:
        try:
            msg = client.messages.create(
                from_=f"whatsapp:{_FROM_NUMBER}",
                to=f"whatsapp:{number}",
                body=body,
            )
            logger.info(
                "WhatsApp sent to %s | SID=%s | title=%r",
                number, msg.sid, article.get("title", ""),
            )
        except Exception as exc:
            logger.error("Failed to send WhatsApp to %s: %s", number, exc, exc_info=True)


def send_articles(articles: list[dict]) -> None:
    """Send each article in *articles* as a separate WhatsApp message."""
    for article in articles:
        send_article(article)
