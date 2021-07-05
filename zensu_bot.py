from datetime import datetime, timedelta
import logging
import os

from chats_tracking import extract_status_change, track_chats
from database import db_query, CONNECTION
from direct_messages import get_reply_keyboard, start, parse_start, parse_where_to_post, parse_type, create_post, cancel
from direct_messages import PARSE_START, PARSE_WHERE_TO_POST, PARSE_TYPE, CREATE_POST
from sticker_tracking import reply_and_confirm
from post_scheduler import create_post

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ChatMember, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    ChatMemberHandler,
    CallbackQueryHandler,
)
from telegram.error import BadRequest


TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler('start', start)],
        states={
            PARSE_START: [CallbackQueryHandler(parse_start, pattern='add_post|end')],
            PARSE_WHERE_TO_POST: [CallbackQueryHandler(parse_where_to_post, pattern = r'-\d*')],
            PARSE_TYPE: [CallbackQueryHandler(parse_type, pattern = r'\d*')],
            CREATE_POST: [MessageHandler(Filters.all, create_post)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))

    q_handler = MessageHandler(Filters.sticker & Filters.reply, reply_and_confirm)
    dispatcher.add_handler(q_handler)

    # Start the Bot
    updater.start_polling()
    
    # Schedule a post every 5 days.
    job = updater.job_queue
    create_post(job)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    CONNECTION.close()


if __name__ == '__main__':
    main()
