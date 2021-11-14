import logging
from datetime import datetime, timedelta, time

from telegram import ParseMode

from bot_functions import send_job
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
        if job_type in [2,9,12,13]:
            try:
                send_job(context, cur_date, chat_id, job_type, order_number)
            except Exception as err: 
                logger.info(f"Could not create job in {chat_id}: {err}")
    
    if context.job.name == 'post_err':
        context.job.schedule_removal()
        create_post_sc(context.job_queue, completed=True)
            


def create_post_sc(job, completed = False):
    time_now = datetime.now()
    interval = timedelta(minutes = 2)
    job.run_repeating(callback = post_callback, interval = interval, last = time_now + timedelta(hours = 1), name = 'post')
