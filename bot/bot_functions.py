import logging
import re
from datetime import datetime, timedelta

from telegram import ParseMode
from telegram.ext import CallbackContext

from constants import POST_HOUR
from database import db_query
from typing import Dict

logger = logging.getLogger(__name__)


def get_user_levels(job_type: int) -> Dict[str, int]:
    """
    Return the number of fully completed jobs for each user for the
    specified `job_type`.
    """
    query = db_query(f"""
        SELECT user_id,
               sum(CASE WHEN unique_days = 5 THEN 1 ELSE 0 END) AS count
        FROM
            (
                SELECT user_id,
                       job_id,
                       COUNT(DISTINCT(date_part('day', jobs_updates.created - jobs.created))) AS unique_days
                FROM jobs_updates
                LEFT JOIN jobs ON jobs_updates.job_id = jobs.id
                WHERE type = {job_type} AND date_part('day', jobs_updates.created - jobs.created) <= 4
                GROUP BY user_id, job_id
            ) t
        GROUP BY user_id;
    """)
    levels = {}
    for user_id, count in query:
        levels[user_id] = count
    return levels

def bot_message_to_chat(context: CallbackContext, chat_id: int, text: str, delete: int = 0, reply_to_message: int = None, parse_mode: str = None) -> None:
    posted_message = context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to_message,
        parse_mode = parse_mode
    )
    if delete != 0:
        context.job_queue.run_once(
            delete_message,
            delete,
            context=[posted_message.message_id, chat_id],
        )

def delete_message(context: CallbackContext) -> None:
    job = context.job.context
    context.bot.delete_message(chat_id=job[1], message_id=job[0])


def fill_template(text: str, n: int, start_date: datetime = datetime.now()) -> str:
    UTC_PLUS = 3
    text = re.sub('([#№])N', f"\g<1>{n}", text, flags=re.I)
    for day in range(5):
        date = start_date + timedelta(days=day, hours=UTC_PLUS)
        open, close = ('','') if datetime.now() - date < timedelta(hours = 24) else ('<b><s>', '</s></b>')
        date = date.strftime("%d.%m.%Y")
        text = re.sub(f"{day+1} [-–—] NN.NN.NNNN", f"{open}{day+1} — {date}{close}", text, flags=re.I)
    return text


def minutes_to_hours(minutes: int, mode = 0) -> str:
    if mode == 0:
        return f"{minutes // 60}h {(minutes % 60):02d}m"
    if mode == 1:
        return f"{round(minutes / 60, 1):g}h"


def send_job(context, cur_date, chat_id, job_type, order_number):
    if job_type != 0:
        photo_id, caption = db_query(
            f'select photo_id, caption from post_templates where job_type = {job_type}',
            True,
        )[0]
        caption = fill_template(caption, order_number)
        
        if photo_id == "None":
            posted_message = context.bot.send_message(chat_id, caption, parse_mode = ParseMode.HTML)
        else:
            posted_message = context.bot.send_photo(chat_id, photo_id, caption=caption, parse_mode = ParseMode.HTML)
        
        last_message_id = db_query(f"select coalesce(max(message_id), 0) from jobs where chat_id = {chat_id}")[0][0]

        
        db_query(f"""insert into jobs(message_id, chat_id, type, order_number, created) values 
                    ({posted_message.message_id}, {chat_id}, {job_type}, {order_number}
                    , '{cur_date.year}-{cur_date.month}-{cur_date.day} {POST_HOUR}:00')""",
            False,
        )
        logger.info(f"Job type {job_type} posted to chat_id {chat_id}")
        logger.info(f"Variables: cur_date={cur_date}, datetime.now()={datetime.now()}")
        
        try:
            context.bot.unpin_chat_message(chat_id = chat_id, message_id = last_message_id)
        except:
            logger.info(f"Unpin didn't work in chat_id {chat_id}")
        
        try:
            context.bot.pin_chat_message(chat_id, posted_message.message_id)
        except:
            logger.info(f"Pin didn't work in chat_id {chat_id}")


