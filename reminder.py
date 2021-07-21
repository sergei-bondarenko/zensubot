import logging
from datetime import datetime, timedelta, time
from telegram import ParseMode

from database import db_query
from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS
from bot_functions import bot_message_to_chat


logger = logging.getLogger(__name__)
post_time = f"{POST_HOUR}:{POST_MINUTE}:00"


def send_notification(context, chat_id, message_id, completed_users_query, all_users_query):
    completed_users = set(db_query(completed_users_query, True))
    all_users = set(db_query(all_users_query, True))
    text = ""
    for user_id in all_users - completed_users:
        first_name = db_query(
            f"select first_name from users where id = {user_id[0]}",
            True,
        )[0][0]
        text += f'{chr(8206)}<a href="tg://user?id={user_id[0]}">{first_name}</a>, '
    if text != "":
        text += f"день закончится через {REMINDER_DELTA} часа. Ты не забыл отметиться?"

        # Check if we are in a cannel or in a chat.
        data = db_query(f"select child, parent from chats_connection where parent = '{chat_id}'", True)
        if len(data) == 1:
            context.bot.send_message(chat_id=data[0][0], text=text, parse_mode=ParseMode.HTML)
        else:
            bot_message_to_chat(context, chat_id, text, reply_to_message = message_id, parse_mode = ParseMode.HTML)


def reminder_callback(context):
    cur_date = datetime.now()
    yesterday = cur_date - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d') + f" {post_time}"
    two_days_ago = cur_date - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d') + f" {post_time}"

    # Check the participants of the last week on Monday.
    if cur_date.weekday() == 0:
        jobs_types = db_query('select id from jobs_types', True)
        for job_type in jobs_types:
            jobs = db_query(f"select id, message_id, chat_id from jobs where type = {job_type[0]} order by id desc limit 2", True)
            if len(jobs) == 2:
                job_id, message_id, chat_id = jobs[0]
                old_job_id, _, _ = jobs[1]
                send_notification(context, chat_id, message_id,
                    f"select distinct(user_id) from jobs_updates where job_id = {job_id}",
                    f"select distinct(user_id) from jobs_updates where job_id = {old_job_id}")

    # Check the participants of last day on other work week days.
    else:
        jobs = db_query(
            'select t2.id, t2.message_id, t2.chat_id from (select max(id) as id, type from jobs group by type) t1 '
            'left join (select * from jobs) t2 on (t1.id = t2.id)',
            True,
        )
        for job_id, message_id, chat_id in jobs:
            send_notification(context, chat_id, message_id,
                f"select distinct(user_id) from jobs_updates where job_id = {job_id} and created > '{yesterday}'",
                f"select distinct(user_id) from jobs_updates where job_id = {job_id} and created >= '{two_days_ago}'")


def reminder(job):
    job.run_daily(callback = reminder_callback, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')
