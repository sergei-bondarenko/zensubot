import logging
from datetime import datetime, timedelta, time

from database import db_query
from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS


logger = logging.getLogger(__name__)
# post_time = f"{POST_HOUR}:{POST_MINUTE}:00"
post_time = f"20:00:00"


def send_notification(context):
    cur_date = datetime.now()
    yesterday = cur_date - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d') + f" {post_time}"
    two_days_ago = cur_date - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d') + f" {post_time}"

    jobs = db_query(
        'select t2.id, t2.message_id, t2.chat_id from (select max(id) as id, type from jobs group by type) t1 '
        'left join (select * from jobs) t2 on (t1.id = t2.id)',
        True,
    )
    for job_id, message_id, chat_id in jobs:
        logger.info(f"{job_id}: {type(job_id)}")
        if job_id != 140:
            continue
        logger.info(f"{job_id}: {type(job_id)}")

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

        message = ""
        for user_id in all_users - completed_users:
            first_name = db_query(
                f"select first_name from users where id = {user_id[0]}",
                True,
            )[0]
            message += f"<a href="tg://user?id={user_id[0]}">{first_name}</a>, "
        message += f"день закончится через {REMINDER_DELTA} часа. Ты не забыл отметиться?"
        logger.info(message)

            #context.bot.send_message(chat_id = update.effective_message.chat_id, 
            #                         text = get_stat(update),
            #                         parse_mode = ParseMode.HTML)


def reminder(job):
    # job.run_daily(callback = send_notification, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')
    job.run_daily(callback = send_notification, time = time(9, 22), days = [6], name = 'reminder_ok')

    # job.run_repeating(callback = send_notification, interval = timedelta(seconds = 20), name = 'reminder_ok')
    pass
