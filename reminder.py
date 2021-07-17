import logging
from datetime import datetime, timedelta, time

from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS


logger = logging.getLogger(__name__)


def send_notification(context):
    cur_date = datetime.now()
    data = db_query(
        'select t2.id, t2.created, t2.message_id, t2.chat_id from (select min(id) as id, type from jobs group by type) t1 '
        'left join (select * from jobs) t2 on (t1.id = t2.id)',
        True,
    )
    for job_id, created, message_id, chat_id in data:
        logger.info(job_id, created, message_id, chat_id)

def reminder(job):
    # job.run_daily(callback = send_notification, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')

    job.run_repeating(callback = send_notification, interval = timedelta(seconds = 20), last = 0, name = 'reminder_ok')
