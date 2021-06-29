ADMINS = ['okuaubro', 'dzendzee', 'z9503']
GROUP_TO_ID = {'pub_1': -1001547820476,'pub_2': -1001528853084,'chat_1':-1001185239661, 'chat_2':-1001211284566}

import logging

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
import psycopg2
import os


DATABASE_URL = os.environ.get('DATABASE_URL')
CONNECTION = psycopg2.connect(DATABASE_URL, sslmode='require')
with CONNECTION:
    with CONNECTION.cursor() as cur:
        cur.execute(f'select id from users')   
        res = cur.fetchall()[0][0]
        print(type(res))
        print(res)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

PARSE_START, PARSE_WHERE_TO_POST, CREATE_POST, = range(3)

def start(update, context) -> int:
    if update.effective_user.username in ADMINS:
        reply_keyboard = [[InlineKeyboardButton("Добавить пост", callback_data='add_post'),
                     InlineKeyboardButton("Пойти нахуй", callback_data='end')]]
        reply_markup = InlineKeyboardMarkup(reply_keyboard)
        update.message.reply_text("What to do?", reply_markup=reply_markup)

        return PARSE_START

    else:
        reply_keyboard = [[InlineKeyboardButton("Пойти нахуй", callback_data='end')]]
        reply_markup = InlineKeyboardMarkup(reply_keyboard)
        update.message.reply_text("What to do?", reply_markup=reply_markup)

        return ConversationHandler.END
    

def parse_start(update, context) -> int:
    query = update.callback_query
    if query.data == 'add_post':
        keyboard = [[InlineKeyboardButton('Паблик 1', callback_data='pub_1'),
                          InlineKeyboardButton('Паблик 2', callback_data='pub_2')],
                        [InlineKeyboardButton('Чат паблика 1', callback_data='chat_1'),
                          InlineKeyboardButton('Чат паблика 2', callback_data='chat_2')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.edit_message_text(text='Where to post?',
                                  reply_markup=reply_markup,
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
        return PARSE_WHERE_TO_POST
    if query.data == 'end':
        context.bot.delete_message(chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
        return ConversationHandler.END


def parse_where_to_post(update, context) -> int:
    query = update.callback_query
    context.user_data["chosen_group"] = GROUP_TO_ID[query.data]
    context.bot.edit_message_text(text='Write here your post',
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
    return CREATE_POST

def create_post(update, context) -> int:
    #context.bot.send_message(chat_id=update.effective_chat.id, text=context.user_data["chosen_group"] + '\n\n' + update.message.text)
    posted_message = context.bot.copy_message(chat_id=context.user_data["chosen_group"], from_chat_id = update.effective_chat.id, message_id = update.effective_message.message_id)
    
    with CONNECTION:
        with CONNECTION.cursor() as cur:
            cur.execute(f'insert into jobs(message_id, chat_id) values ({posted_message.message_id}, {context.user_data["chosen_group"]});')
    
    context.bot.send_message(chat_id = update.effective_chat.id, text = 'Done!')
    return ConversationHandler.END
  
def cancel(update, context) -> int:
    return ConversationHandler.END


def reply_and_confirm(update, context):
    chat_id = update.effective_chat
    message = update.effective_message
    user =  update.effective_user
    
    dict_message = message.to_dict()

    try:
        message_id = message.reply_to_message.forward_from_message_id
        group_id = message.reply_to_message.forward_from_chat.id
        text = message.reply_to_message.text
        
    except:
        message_id = message.reply_to_message.message_id
        group_id = message.reply_to_message.chat.id
        text = message.reply_to_message.text

    user_id = user.id
    username = user.username
    user_firstname = user.first_name

    with CONNECTION:
        with CONNECTION.cursor() as cur:
            cur.execute(f'select id, username, first_name from users where users.id = {user.id}')   
            res = cur.fetchall() 
            if len(res) == 0:
                cur.execute(f"insert into users values ({user_id}, '{username}', '{user_firstname}')")
    

def extract_status_change(
    chat_member_update,
):
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = (
        old_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    )
    is_member = (
        new_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    )

    return was_member, is_member


def track_chats(update: Update, context: CallbackContext) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            logger.info("%s started the bot", cause_name)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s with id %s", cause_name, chat.title, chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s with id %s", cause_name, chat.title, chat.id)
    else:
        if not was_member and is_member:
            logger.info("%s added the bot to the channel %s with id %s", cause_name, chat.title, chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the channel %s with id %s", cause_name, chat.title, chat.id)



def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater('1884842077:AAFlcCTfYyk-U14Q0Zem7doysM3pBCfQZLU')

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler('start', start)],
        states={
            PARSE_START: [CallbackQueryHandler(parse_start, pattern='add_post|end')],
            PARSE_WHERE_TO_POST: [CallbackQueryHandler(parse_where_to_post, pattern = r'(pub|chat)_\d')],
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

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    CONNECTION.close()


if __name__ == '__main__':
    main()
