EM_TRUE = '✅'
EM_FALSE = '⚫️'

from datetime import datetime, timedelta
import logging
import os

from chats_tracking import extract_status_change, track_chats
from database import db_query
from direct_messages import get_reply_keyboard, start, parse_start, parse_where_to_post, parse_type, create_post, cancel
from direct_messages import PARSE_START, PARSE_WHERE_TO_POST, PARSE_TYPE, CREATE_POST

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

        
        #updating users if sticker_day == 1
        if sticker_day == 1:
            db_query(f"update users set username = '{username}', first_name = '{user_firstname}' where id = {user_id}", False)

        #Getting current day since start of job
        cur_day = int(db_query(f"select DATE_PART('day', now()-created)+1 from jobs where id = {job_id}")[0][0])
        if sticker_day in (cur_day, cur_day + 1) and check_previous_days(job_id, user_id, sticker_day):
            db_query(f"insert into jobs_updates (user_id, job_id, sticker_id) values ({user_id}, {job_id}, {sticker_id})", False)
            
            data = db_query(f"""select coalesce(concat('@',username), first_name) as name, d1, d2, d3, d4, d5 
                            from 
                                (select user_id, sum(case when day=1 then 1 else 0 end) d1, sum(case when day=2 then 1 else 0 end) d2, sum(case when day=3 then 1 else 0 end) d3
                                    , sum(case when day =4 then 1 else 0 end) d4, sum(case when day =5 then 1 else 0 end) d5 
                                from jobs_updates join stickers on jobs_updates.sticker_id = stickers.id 
                                where job_id={job_id} 
                                group by user_id) as t 
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

                logger.info(f"Edited job with id {job_id} after posted sticker id {sticker_id} by @{username} with firstname {user_firstname}")

                posted_message = context.bot.send_message(chat_id = message.chat.id, reply_to_message_id = update.message.message_id, text = f"Молодец! День {sticker_day} выполнен!")

                context.job_queue.run_once(delete_message, 60, context = [posted_message.message_id, message.chat.id])

            except BadRequest:
                #May be exception because edited message stays the same
                try:
                    context.bot.edit_message_caption(chat_id = group_id, message_id = message_id, caption = text)

                    logger.info(f"Edited job with id {job_id} after posted sticker id {sticker_id} by @{username} with firstname {user_firstname}")

                    posted_message = context.bot.send_message(chat_id = message.chat.id, reply_to_message_id = update.message.message_id, text = f"Молодец! День {sticker_day} выполнен!")

                    context.job_queue.run_once(delete_message, 60, context = [posted_message.message_id, message.chat.id])

                except BadRequest:
                    pass

            


def delete_message(context) -> None:
    job = context.job.context
    context.bot.delete_message(chat_id = job[1], message_id = job[0])


def check_previous_days(job_id, user_id, sticker_day):
    data = db_query(f"select distinct day from jobs_updates join stickers on stickers.id = jobs_updates.sticker_id where job_id={job_id} and user_id = {user_id}")
    data = {x[0] for x in data}
    passed = True

    for i in range(1, sticker_day):
        passed = passed and (i in data)    

    return passed


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
    
    #queue example
    """
    job = updater.job_queue
    job_minute = job.run_repeating(callback = callback_minute, interval = timedelta(days = 5), first = datetime(2021, 7, 4, 18, 50))
    print(job_minute.jobs())
    def callback_minute(context):
        context.bot.send_message(chat_id='@guhccssa', text='Message')
    """

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    CONNECTION.close()


if __name__ == '__main__':
    main()
