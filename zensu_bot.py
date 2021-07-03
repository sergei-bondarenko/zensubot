ADMINS = ['okuaubro', 'dzendzee', 'z9503']
EM_TRUE = '✅'
EM_FALSE = '⚫️'

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

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')
CONNECTION = psycopg2.connect(DATABASE_URL, sslmode='require')


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

PARSE_START, PARSE_WHERE_TO_POST, CREATE_POST, = range(3)

def db_query(line, fetching = True):
    with CONNECTION:
        with CONNECTION.cursor() as cur:
            cur.execute(line)
            if fetching:
                data = cur.fetchall()
                return data

def get_reply_keyboard():
    data = db_query(f"select id, title from chats")

    reply_keyboard = list()
    for item in data:
        reply_keyboard.append([InlineKeyboardButton(item[1], callback_data=item[0])])
        
    return reply_keyboard

def start(update, context) -> int:

    logger.info(f"@{update.effective_user.username}, {update.effective_user.first_name} started bot")

    if update.effective_user.username in ADMINS:
        reply_keyboard = [[InlineKeyboardButton("Добавить пост", callback_data='add_post')], [InlineKeyboardButton("Пойти нахуй", callback_data='end')]]
    else:
        reply_keyboard = [[InlineKeyboardButton("Я не дзендзи. Пойти нахуй", callback_data='end')]]
    
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    
    update.message.reply_text("What to do?", reply_markup=reply_markup)
    
    return PARSE_START
    

def parse_start(update, context) -> int:
    query = update.callback_query
    if query.data == 'add_post':

        keyboard = get_reply_keyboard()
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
    print(1)
    query = update.callback_query
    print(query)
    print(query.data)
    context.user_data["chosen_group"] = query.data

    logger.info(f"@{update.effective_user.username}, {update.effective_user.first_name} chosen to post at {query.data}")
    
    context.bot.edit_message_text(text='Write here your post',
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
    return CREATE_POST

def create_post(update, context) -> int:
    #context.bot.send_message(chat_id=update.effective_chat.id, text=context.user_data["chosen_group"] + '\n\n' + update.message.text)
    posted_message = context.bot.copy_message(chat_id=context.user_data["chosen_group"], from_chat_id = update.effective_chat.id, message_id = update.effective_message.message_id)
    
    db_query(f'insert into jobs(message_id, chat_id) values ({posted_message.message_id}, {context.user_data["chosen_group"]});', False)

    logger.info(f"@{update.effective_user.username}, {update.effective_user.first_name} posted message with text \n\n{posted_message.text} \n\ncaption \n\n{posted_message.caption}")
    
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
    
    if text is None:
        try:
            text = message['reply_to_message']['caption']    
        except:
            pass
    
    user_id = user.id
    username = user.username
    user_firstname = user.first_name

    job_id, sticker_id = None, None
    
    
    #Getting active jobs if they exist    
    data = db_query(f"select id from jobs where message_id = {message_id} and chat_id = {group_id} and DATE_PART('day', now()-created)<=4")
    if len(data) != 0:
        job_id = data[0][0]
    
    #Getting sticker id if it exist
    
    data = db_query(f"select id, day from stickers where text_id='{message.sticker.file_unique_id}'")
    if len(data) != 0:
        sticker_id = data[0][0]
        sticker_day = data[0][1]
    
    #Writing update to table if job_id and sticker_id is correct    
    
    if job_id and sticker_id:

        #Creating new users if they do not exist    
        data = db_query(f'select id from users where id = {user_id}')
        if len(data) == 0:
            db_query(f"insert into users values ({user_id}, '{username}', '{user_firstname}')", False)
            logger.info(f"User with id {user_id}, username {username}, firstname {user_firstname} added to database")

        #Getting current day since start of job
        cur_day = db_query(f"select DATE_PART('day', now()-created)+1 from jobs where id = {job_id}")[0][0]
        
        if cur_day == sticker_day:
            db_query(f"insert into jobs_updates (user_id, job_id, sticker_id) values ({user_id}, {job_id}, {sticker_id})", False)
            
            data = db_query(f"""select coalesce(concat('@',username), first_name) as name, d1, d2, d3, d4, d5 
                            from 
                                (select user_id, sum(case when day=1 then 1 else 0 end) d1, sum(case when day=2 then 1 else 0 end) d2, sum(case when day=3 then 1 else 0 end) d3
                                    , sum(case when day =4 then 1 else 0 end) d4, sum(case when day =5 then 1 else 0 end) d5 
                                from jobs_updates join stickers on jobs_updates.sticker_id = stickers.id 
                                where job_id={job_id} group by user_id) as t 
                            join users on users.id = t.user_id;""")

            text = text.split('\n\nУчастники:')[0]
            added_text = '\n\nУчастники:\n'
            for item in data:
                added_text += ''.join([EM_TRUE if int(x)>0 else EM_FALSE for x in item[1:]])+' '
                added_text += item[0]
                added_text += '\n'
            text += added_text
            try:
                context.bot.edit_message_text(text = text, chat_id = group_id, message_id = message_id)
            except:
                context.bot.edit_message_caption(chat_id = group_id, message_id = message_id, caption = text)

            logger.info(f"Edited job with id {job_id} after posted sticker id {sticker_id} by @{username} with firstname {user_firstname}")

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
            db_query(f"insert into chats values ({chat.id}, '{chat.title} чат')", False)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s with id %s", cause_name, chat.title, chat.id)
            db_query(f"delete from chats where id = {chat.id})", False)
    else:
        if not was_member and is_member:
            logger.info("%s added the bot to the channel %s with id %s", cause_name, chat.title, chat.id)
            db_query(f"insert into chats values ({chat.id}, '{chat.title} канал')", False)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the channel %s with id %s", cause_name, chat.title, chat.id)
            db_query(f"delete from chats where id = {chat.id})", False)



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
            PARSE_WHERE_TO_POST: [CallbackQueryHandler(parse_where_to_post, pattern = r'.* (чат|канал)')],
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
