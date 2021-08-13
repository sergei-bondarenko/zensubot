import logging
from datetime import datetime, timedelta, time

from telegram import ParseMode

from bot_functions import fill_template
from constants import POST_WEEKDAY, POST_HOUR, POST_MINUTE
from database import db_query

logger = logging.getLogger(__name__)


def post_callback(context):
    cur_date = datetime.now()
    data = db_query(
        """select id, jobs_type, coalesce(order_number, 0) + 1
            from chats left join (select type, max(order_number) as order_number from jobs group by type) t on t.type = chats.jobs_type 
            where jobs_type is not null"""
    )
    for chat_id, job_type, order_number in data:

        if job_type != 0:
            photo_id, caption = db_query(
                f'select photo_id, caption from post_templates where job_type = {job_type}',
                True,
            )[0]
            caption = fill_template(caption, order_number)
            
            if photo_id == "None":
                posted_message = context.bot.send_message(chat_id, caption, parse_mode = ParseMode.HTML)
            else:
                posted_message = context.bot.send_photo(chat_id, photo_id, caption=caption, parse_mode = ParseMode.HTML)
            
            last_message_id = db_query(f"select coalesce(max(message_id), 0) from jobs where chat_id = {chat_id}")[0][0]

            
            db_query(f"""insert into jobs(message_id, chat_id, type, order_number, created) values 
                        ({posted_message.message_id}, {chat_id}, {job_type}, {order_number}
                        , '{cur_date.year}-{cur_date.month}-{cur_date.day} {POST_HOUR}:00')""",
                False,
            )
            logger.info(f"Job type {job_type} posted to chat_id {chat_id}")
            
            try:
                context.bot.unpin_chat_message(chat_id = chat_id, message_id = last_message_id)
            except:
                logger.info(f"Unpin didn't work in chat_id {chat_id}")
            
            try:
                context.bot.pin_chat_message(chat_id, posted_message.message_id)
            except:
                logger.info(f"Pin didn't work in chat_id {chat_id}")
    
    if context.job.name == 'post_err':
        context.job.schedule_removal()
        create_post_sc(context.job_queue, completed=True)
            


def create_post_sc(job, completed = False):
    time_now = datetime.now()

    if time_now.weekday() == POST_WEEKDAY and POST_HOUR <= time_now.hour <= POST_HOUR+1 and not completed:
        interval = timedelta(minutes = 2)
        job.run_repeating(callback = post_callback, interval = interval, last = time_now + timedelta(hours = 1), name = 'post_err')
    else:
        job.run_daily(callback = post_callback, time = time(POST_HOUR, POST_MINUTE), days = [POST_WEEKDAY], name = 'post_ok')
