import logging
from database import db_query
from datetime import datetime, timedelta

def callback_minute(context):
    # context.bot.send_message(chat_id='@guhccssa', text='Тестирую отправку сообщения каждые 10 секунд.')
    job_types = db_query(
        'select job_type from post_templates',
        True,
    )
    for job_type in job_types:
        created = db_query(
            f"select max(created) from jobs where type = {job_type}",
            True,
        )
        logger.info(
            f"{job_type}: {created}"
        )

def create_post_sc(job):
    interval = timedelta(seconds = 20)
    job_minute = job.run_repeating(callback = callback_minute, interval = interval)
