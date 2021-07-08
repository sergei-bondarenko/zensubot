import logging
import os

from telegram.ext import (CallbackQueryHandler, ChatMemberHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from chats_tracking import track_chats
from database import CONNECTION
from direct_messages import (CREATE_POST, EDIT_TEMPLATE, PARSE_START,
                             PARSE_TYPE, PARSE_WHERE_TO_POST, cancel,
                             create_post, edit_template, parse_start,
                             parse_type, parse_where_to_post, start)
from plus_tracking import plus
from post_scheduler import create_post_sc
from sticker_tracking import stickers

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

def bot_message_to_chat(context, chat_id, text, delete = 0, reply_to_message = None, parse_mode = None):
    posted_message = context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to_message,
        parse_mode = parse_mode
    )
    if delete != 0:
        context.job_queue.run_once(
            delete_message,
            delete,
            context=[posted_message.message_id, chat_id],
        )

def delete_message(context) -> None:
    job = context.job.context
    context.bot.delete_message(chat_id=job[1], message_id=job[0])


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
                CallbackQueryHandler(parse_start, pattern="add_post|edit_template|end")
            ],
            PARSE_WHERE_TO_POST: [
                CallbackQueryHandler(parse_where_to_post, pattern=r"-\d*")
            ],
            PARSE_TYPE: [CallbackQueryHandler(parse_type, pattern=r"\d*")],
            CREATE_POST: [MessageHandler(Filters.all, create_post)],
            EDIT_TEMPLATE: [MessageHandler(Filters.all, edit_template)],
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

    # Start the Bot
    updater.start_polling()

    # Schedule a post every 5 days.
    job = updater.job_queue
    create_post_sc(job)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    CONNECTION.close()


if __name__ == "__main__":
    main()
