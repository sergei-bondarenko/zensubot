import logging
from datetime import datetime, timedelta, time

from database import db_query
from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS


logger = logging.getLogger(__name__)


def send_notification(context):
    cur_date = datetime.now()
    yesterday = cur_date - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d') + f" {POST_HOUR}:{POST_MINUTE}:00"
    2days_ago = cur_date - timedelta(days=2)
    2days_ago_str = 2days_ago.strftime('%Y-%m-%d') + f" {POST_HOUR}:{POST_MINUTE}:00"

    jobs = db_query(
        'select t2.id, t2.message_id, t2.chat_id from (select min(id) as id, type from jobs group by type) t1 '
        'left join (select * from jobs) t2 on (t1.id = t2.id)',
        True,
    )
    for job_id, message_id, chat_id in jobs:
        # Get users which already have sent stickers today.
        completed_users = db_query(
            f"select user_id from jobs_updates where job_id = {job_id} and created > '{yesterday_str}'",
            True,
        )
        # Get users which have not sent stickers today, but sent it previous day.
        noncompleted_users = db_query(
            f"select user_id from jobs_updates where job_id = {job_id} and created >= '{2days_ago}' and created <= '{yesterday_str}'",
            True,
        )
        logger.info(f"{job_id}: completed {completed_users}, {type(completed_users)}")
        logger.info(f"{job_id}: noncompleted {noncompleted_users}, {type(noncompleted_users)}")


def reminder(job):
    # job.run_daily(callback = send_notification, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')

    job.run_repeating(callback = send_notification, interval = timedelta(seconds = 20), name = 'reminder_ok')
    pass
