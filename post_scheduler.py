import logging
from datetime import datetime, timedelta, timezone

from telegram import ParseMode

from bot_functions import fill_template
from database import db_query

logger = logging.getLogger(__name__)


def callback_minute(context):
    data = db_query(
        'select type, max(created), count(1) from jobs group by type',
        True,
    )
    for job_type, created, count in data:
        passed_time = datetime.now(timezone.utc) - created

        #if passed_time >= timedelta(days = 5):
        if job_type == 0:

            if job_type == 0:
                offset = 2
            elif job_type == 1:
                offset = 4
            elif job_type == 2:
                offset = 2
            elif job_type == 3:
                offset = 2
            elif job_type == 4:
                offset = 1

            photo_id, caption = db_query(
                f'select photo_id, caption from post_templates where job_type = {job_type}',
                True,
            )[0]
            caption = fill_template(caption, count + offset + 1)

            chat_id = db_query(f'select id from chats where jobs_type = {job_type}', True)[0][0]
            if photo_id == "None":
                posted_message = context.bot.send_message(chat_id, caption, parse_mode = ParseMode.HTML)
            else:
                posted_message = context.bot.send_photo(chat_id, photo_id, caption=caption, parse_mode = ParseMode.HTML)
            
            last_message_id = db_query(f"select max(message_id) from jobs where chat_id = {chat_id}")[0][0]
            context.bot.unpin_chat_message(chat_id = chat_id, message_id = last_message_id)

            db_query(
                f'insert into jobs(message_id, chat_id, type) values ({posted_message.message_id}, {chat_id}, {job_type})',
                False,
            )
            logger.info(f"Job type {job_type} posted to chat_id {chat_id}")
            # context.bot.unpin_all_chat_messages(chat_id=chat_id)
            context.bot.pin_chat_message(chat_id, posted_message.message_id)


def create_post_sc(job):
    interval = timedelta(seconds = 60)
    job_minute = job.run_repeating(callback = callback_minute, interval = interval)
