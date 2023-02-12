import logging

from telegram import Update
from telegram.ext import (
    CallbackContext,
)

logger = logging.getLogger(__name__)


def unpin_channel_messages(update: Update, context: CallbackContext) -> None:
    """Unpins messages from channels in chats"""
    logger.info(f"Unpinning message: {update}")
    try:
        update.effective_message.unpin()
    except Exception as e:
        logger.info(f"Unpinning message failed: {e}")
