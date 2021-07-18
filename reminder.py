import logging
from datetime import datetime, timedelta, time
from telegram import ParseMode

from database import db_query
from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS
from bot_functions import bot_message_to_chat


logger = logging.getLogger(__name__)

# TODO: remove this.
# post_time = f"{POST_HOUR}:{POST_MINUTE}:00"
post_time = f"21:00:00"


def send_notification(context):
    logger.info(f"context: {context}")
    logger.info(f"context dir: {dir(context)}")
    cur_date = datetime.now()
    yesterday = cur_date - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d') + f" {post_time}"
    two_days_ago = cur_date - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d') + f" {post_time}"

    # Check the participants of last week on Monday.
    if cur_date.weekday() == 0:
        jobs_types = db_query('select id from jobs_types', True)
        for job_type in jobs_types:
            jobs = db_query('select * from jobs where type = 1 order by id desc limit 2', True)
            logger.info(f"{job_type}: {jobs}")
            logger.info(f"{job_type}: {len(jobs)}")

    # Check the participants of last day on other work week days.
    else:
        jobs = db_query(
            'select t2.id, t2.message_id, t2.chat_id from (select max(id) as id, type from jobs group by type) t1 '
            'left join (select * from jobs) t2 on (t1.id = t2.id)',
            True,
        )
        for job_id, message_id, chat_id in jobs:
            # TODO: remove this.
            if job_id != 140:
                continue
    
            # Get users which already have sent stickers today.
            completed_users = set(db_query(
                f"select distinct(user_id) from jobs_updates where job_id = {job_id} and created > '{yesterday}'",
                True,
            ))
            # Get all users from two previous days.
            all_users = set(db_query(
                f"select distinct(user_id) from jobs_updates where job_id = {job_id} and created >= '{two_days_ago}'",
                True,
            ))
    
            text = ""
            for user_id in all_users - completed_users:
                first_name = db_query(
                    f"select first_name from users where id = {user_id[0]}",
                    True,
                )[0][0]
                text += f'<a href="tg://user?id={user_id[0]}">{first_name}</a>, '
    
            if text != "":
                text += f"день закончится через {REMINDER_DELTA} часа. Ты не забыл отметиться?"
                logger.info(text)
                # TODO: uncommit this.
                #bot_message_to_chat(context, chat_id, text, reply_to_message = message_id, parse_mode = ParseMode.HTML)


def reminder(job):
    # TODO: remove comments and "pass" here.
    # job.run_daily(callback = send_notification, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')
    # job.run_daily(callback = send_notification, time = time(10, 00), days = [6], name = 'reminder_ok')

    job.run_repeating(callback = send_notification, interval = timedelta(seconds = 20), name = 'reminder_ok')
    pass
