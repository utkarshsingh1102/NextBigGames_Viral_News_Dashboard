"""WhatsApp webhook route — receives incoming messages from Twilio."""

import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.whatsapp_commands import handle_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
def whatsapp_webhook(
    Body: str = Form(default=""),
    From: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Twilio sends incoming WhatsApp messages here as form-encoded POST data.

    Responds with TwiML so Twilio can deliver the reply back to the sender.
    """
    logger.info("WhatsApp message from %s: %r", From, Body)
    reply = handle_command(Body, From, db)

    # Escape XML special characters in the reply
    safe_reply = (
        reply
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{safe_reply}</Message>"
        "</Response>"
    )
    return Response(content=twiml, media_type="application/xml")
