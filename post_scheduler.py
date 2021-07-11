import logging
from database import db_query
from datetime import datetime, timedelta, timezone
from bot_functions import fill_template

logger = logging.getLogger(__name__)

def callback_minute(context):
    # context.bot.send_message(chat_id='@guhccssa', text='Тестирую отправку сообщения каждые 10 секунд.')
    data = db_query(
        'select type, max(created), count(1) from jobs group by type',
        True,
    )
    for job_type, created, count in data:
        passed_time = datetime.now(timezone.utc) - created

        if job_type == 0:
        # TODO: Uncomment if below.
        # if passed_time >= timedelta(days = 5):

            # TODO: offset for different job_types.
            photo_id, caption = db_query(
                f'select photo_id, caption from post_templates where job_type = {job_type}',
                True,
            )[0]
            caption = fill_template(caption, count + 1)

            chat_id = db_query(f'select id from chats where jobs_type = {job_type}', True)[0]
            if photo_id == "None":
                posted_message = context.bot.send_message(chat_id, caption)
            else:
                posted_message = context.bot.send_photo(chat_id, photo_id, caption=caption)
            db_query(
                f'insert into jobs(message_id, chat_id, type) values ({posted_message.message_id}, {chat_id}, {job_type})',
                False,
            )

def create_post_sc(job):
    interval = timedelta(seconds = 120)
    # job_minute = job.run_repeating(callback = callback_minute, interval = interval)
