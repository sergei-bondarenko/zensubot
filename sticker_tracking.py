import logging
from responses import Responses

from telegram import ParseMode
from telegram.error import BadRequest

from bot_functions import bot_message_to_chat, fill_template
from database import db_query
from post_scheduler import JOB_DAYS_DURATION

logger = logging.getLogger(__name__)


def stickers(update, context):
    data = CollectData(update)

    # Writing update to table if job_id and sticker_id is correct
    if data.job_id and data.sticker_id:

        # Creating new users if they do not exist or updating old users
        update_users(data)

        # Check if user is not allowed to post
        if data.yesterday_work != 0 or data.cur_day == 0:
            # Inserting new job_update
            db_query(
                f"insert into jobs_updates (user_id, job_id, sticker_id) values ({data.user_id}, {data.job_id}, {data.sticker_id})",
                False,
            )

            rebuild_message(context, data)
        else:
            bot_message_to_chat(
                context,
                data.chat_id_user_reply,
                f"Мда, долбаеб. Вчера день проебал, а сегодня хочешь отметиться?",
                reply_to_message=data.message_id_user_reply,
            )


class CollectData:
    def __init__(self, update):
        message = update["message"]
        reply = message["reply_to_message"]
        user = update.effective_user
        try:
            # Job posted to channel
            self.job_chat_id = reply["forward_from_chat"]["id"]
            self.job_message_id = reply["forward_from_message_id"]
        except TypeError:
            # Job posted to chat
            self.job_chat_id = message["chat"]["id"]
            self.job_message_id = reply["message_id"]

        self.user_id = user["id"]
        self.username = user["username"]
        self.user_firstname = user["first_name"]

        self.chat_id_user_reply = message["chat"]["id"]
        self.message_id_user_reply = message["message_id"]

        self.is_caption = bool(reply.caption)

        # Getting active jobs if they exist
        try:
            (
                self.job_id, self.start_date, self.cur_day, self.job_type, self.order_number,
                self.sticker_id, self.sticker_power, self.yesterday_work,
            ) = db_query(
                f"""select jobs.id, jobs.created, DATE_PART('day', now()-jobs.created), type, order_number , stickers.id, power, count(jobs_updates.created)
                    from jobs left join jobs_updates 
                    on jobs.id=jobs_updates.job_id and user_id={self.user_id} and date_part('day', jobs_updates.created - jobs.created) = DATE_PART('day', now()-jobs.created) - 1
                    left join stickers on stickers.text_id = '{message['sticker']['file_unique_id']}'
                    where message_id = {self.job_message_id} 
                    and chat_id = {self.job_chat_id} 
                    and DATE_PART('day', now()-jobs.created) < {JOB_DAYS_DURATION}
                    group by jobs.id, jobs.created, DATE_PART('day', now()-jobs.created), type, order_number , stickers.id, power
            """
            )[0]
        except IndexError:
            # Job not exists
            self.job_id = self.sticker_id = None


def rebuild_message(context, data):
    # Collecting data about current job progress
    query = db_query(
        f"""select user_id, first_name, total, d0, d1, d2, d3, d4
                from
                    (select user_id , sum(case when sday = 0 then power else 0 end) d0, sum(case when sday = 1 then power else 0 end) d1
                                        , sum(case when sday = 2 then power else 0 end) d2, sum(case when sday = 3 then power else 0 end) d3
                                        , sum(case when sday = 4 then power else 0 end) d4, sum(power) total
                    from
                        (select user_id, date_part('day', jobs_updates.created - jobs.created) as sday, sticker_id
                        from jobs_updates join jobs on jobs.id = jobs_updates.job_id
                        where job_id = {data.job_id}) t join stickers on stickers.id = t.sticker_id
                    group by user_id) t 
                    join users on users.id=t.user_id 
                    order by total desc
                ;"""
    )

    text = db_query(
        f"select caption from post_templates where job_type = {data.job_type}"
    )[0][0]
    text = fill_template(text, data.order_number, data.start_date)

    text, work_today = get_posted_message(text, query, data.cur_day, data.user_id)

    try:
        if data.is_caption:
            context.bot.edit_message_caption(
                chat_id=data.job_chat_id,
                message_id=data.job_message_id,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
        else:
            context.bot.edit_message_text(
                text=text,
                chat_id=data.job_chat_id,
                message_id=data.job_message_id,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        logger.info(
            f"Edited job with id {data.job_id} after posted sticker id {data.sticker_id} by @{data.username} with firstname {data.user_firstname}"
        )

        if work_today == data.sticker_power:
            first_day = True
            question = Responses.get(data.job_type, 1)
            greet = Responses.get(data.job_type, 2)
            line = '' if question == '' else '\n'
            text = f"Молодец! День {int(data.cur_day+1)} выполнен!\n\n{question+line+greet}"
        else:
            first_day = False
            text = f"Время добавлено!\nЗа сегодня ты потрудился {work_today // 60}h {work_today % 60:02d}m!"

        bot_message_to_chat(
            context, data.chat_id_user_reply, text, 0 if first_day else 60, data.message_id_user_reply, ParseMode.HTML
        )

    except BadRequest:
        pass


def update_users(data):
    db_query(
        f"""insert into users (id, username, first_name) 
                values ({data.user_id}, '{data.username}', '{data.user_firstname}')
                on conflict (id) do update 
                set username = excluded.username, 
                    first_name = excluded.first_name;""",
        False,
    )


def get_posted_message(text, query, cur_day, cur_user_id):
    EM_TRUE = "✅"
    EM_FALSE = "⚫️"
    EM_FAIL = "❌"
    USERS = "<b>Участники</b>"

    text = text.split(f"\n\n{USERS}:")[0]

    passed = list()
    loosers = list()

    for user_id, user_firstname, total, *days in query:
        is_first_fail = True

        # chr(8206) is a mark to keep text format left to right
        name_phrase = (
            f'{chr(8206)}<a href="tg://user?id={user_id}">{user_firstname}</a>'
        )
        phrase = str()

        for i, day in enumerate(days):
            day = int(day)

            # Checking if today is the first activity of user
            if user_id == cur_user_id and i == cur_day:
                work_today = day

            if day == 0 and is_first_fail and i < cur_day:
                phrase += EM_FAIL
                is_first_fail = False
            elif day > 0:
                phrase += EM_TRUE
            else:
                phrase += EM_FALSE

        phrase += f" {str(total // 60)}h {(total % 60):02d}m"

        if is_first_fail:
            passed.append((name_phrase, phrase))
        else:
            loosers.append((name_phrase, phrase))

    added_text = str()

    for i, (name_phrase, phrase) in enumerate(passed):
        added_text += f"{i+1}. {name_phrase}\n{phrase}\n\n"

    for j, (name_phrase, phrase) in enumerate(loosers):
        added_text += f"{i + j + 2}. <s>{name_phrase}</s>\n{phrase}\n\n"
    text += "\n\n" + added_text

    return text, work_today
