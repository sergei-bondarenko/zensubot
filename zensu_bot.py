import logging
import os

from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
from telegram.ext import (CallbackQueryHandler, ChatMemberHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater, InlineQueryHandler)
from telegram.utils.helpers import escape_markdown

from chats_tracking import track_chats
from database import clean_plus_data
from direct_messages import (CREATE_POST, EDIT_TEMPLATE, PARSE_START, SAVE_TEMPLATE,
                             PARSE_TYPE, PARSE_WHERE_TO_POST, 
                             EDIT_RESPONSE_TYPE, PARSE_RESPONSE_TYPE, WRITE_RESPONSES,
                             cancel, create_post, edit_template, parse_start, parse_type, 
                             parse_where_to_post, start, save_template,
                             edit_response_type, parse_response_type, write_response)
from plus_tracking import plus
from post_scheduler import create_post_sc
from responses import Responses
from sticker_tracking import stickers
from uuid import uuid4

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def inlinequery(update, context) -> None:
    """Handle the inline query."""
    query = update.inline_query.query

    if query == "":
        update.inline_query.answer([InlineQueryResultArticle(
            id=str(uuid4()),
            title="Получить статистику по пятидневкам",
            input_message_content=InputTextMessageContent("Медитации 2/3 54h 20m"),
        )])
        

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler("start", start)],
        states={
            PARSE_START: [
                CallbackQueryHandler(parse_start, pattern="add_post|edit_template|responses|end")
            ],
            PARSE_WHERE_TO_POST: [
                CallbackQueryHandler(parse_where_to_post, pattern=r"-\d*")
            ],
            PARSE_TYPE: [CallbackQueryHandler(parse_type, pattern=r"\d*")],
            CREATE_POST: [MessageHandler(Filters.all, create_post)],
            EDIT_TEMPLATE: [CallbackQueryHandler(edit_template, pattern=r"\d*")],
            SAVE_TEMPLATE: [MessageHandler(Filters.all, save_template)],
            EDIT_RESPONSE_TYPE: [CallbackQueryHandler(edit_response_type, pattern=r"\d*")],
            PARSE_RESPONSE_TYPE: [CallbackQueryHandler(parse_response_type, pattern=r"\d*")],
            WRITE_RESPONSES: [MessageHandler(Filters.document.txt, write_response)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(
        ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    stickers_handler = MessageHandler(Filters.sticker & Filters.reply, stickers)
    dispatcher.add_handler(stickers_handler)

    plus_handler = MessageHandler(Filters.reply & Filters.regex(r"^\+$"), plus)
    dispatcher.add_handler(plus_handler)

    dispatcher.add_handler(InlineQueryHandler(inlinequery))

    # Collect bot responses
    Responses.collect()

    # Start the Bot
    updater.start_polling()

    jobs = updater.job_queue

    # Schedule a post every 5 days.
    create_post_sc(jobs)

    # Clean plus_data every 2 days
    clean_plus_data(jobs)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
