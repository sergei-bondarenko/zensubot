import logging
from database import db_query
from datetime import datetime, timedelta

def callback_minute(context):
    # context.bot.send_message(chat_id='@guhccssa', text='Тестирую отправку сообщения каждые 10 секунд.')
    data = db_query(
        'select type, max(created) from jobs group by type',
        True,
    )
    for job_type, created in data:
        logger.info(
            f"{job_type}: {created}"
        )

def create_post_sc(job):
    interval = timedelta(seconds = 20)
    job_minute = job.run_repeating(callback = callback_minute, interval = interval)
