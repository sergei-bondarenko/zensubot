import logging

from telegram import ParseMode
from telegram.error import BadRequest

from bot_functions import bot_message_to_chat, fill_template
from database import db_query
from post_scheduler import JOB_DAYS_DURATION

logger = logging.getLogger(__name__)

EM_TRUE = "✅"
EM_FALSE = "⚫️"
EM_FAIL = "❌"


def stickers(update, context):
    data = CollectData(update)

    # Writing update to table if job_id and sticker_id is correct
    if data.job_id and data.sticker_id:

        # Creating new users if they do not exist or updating old users
        update_users(data)

        # Check if user is banned
        is_banned = get_is_banned(context, data) if data.cur_day > 0 else False

        if not is_banned:
            # Inserting new job_update
            db_query(
                f"insert into jobs_updates (user_id, job_id, sticker_id) values ({data.user_id}, {data.job_id}, {data.sticker_id})",
                False,
            )

            rebuild_message(context, data)


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
        self.job_id, self.start_date, self.cur_day, self.job_type, self.order_number = db_query(
            f"""select id, created, DATE_PART('day', now()-created), type, order_number 
                from jobs 
                where message_id = {self.job_message_id} 
                and chat_id = {self.job_chat_id} 
                and DATE_PART('day', now()-created) < {JOB_DAYS_DURATION}"""
        )[0]

        # Getting sticker id if it exist
        self.sticker_id, self.sticker_power = db_query(
            f"select id, power from stickers where text_id='{message['sticker']['file_unique_id']}'"
        )[0]


def rebuild_message(context, data):
    # Collecting data about current job progress
    query = db_query(
        f"""select user_id, first_name, total, d1, d2, d3, d4, d5 
                from
                    (select user_id , sum(case when sday = 1 then power else 0 end) d1, sum(case when sday = 2 then power else 0 end) d2
                                        , sum(case when sday = 3 then power else 0 end) d3, sum(case when sday = 4 then power else 0 end) d4
                                        , sum(case when sday = 5 then power else 0 end) d5, sum(power) total
                    from
                        (select user_id, date_part('day', jobs_updates.created - jobs.created)+1 as sday, sticker_id
                        from jobs_updates join jobs on jobs.id = jobs_updates.job_id
                        where job_id = {data.job_id}) t join stickers on stickers.id = t.sticker_id
                    group by user_id) t 
                    join users on users.id=t.user_id 
                    order by total desc
                ;"""
    )

    text = db_query(f"select caption from post_templates where job_type = {data.job_type}")[
        0
    ][0]
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
            text = f"Молодец! День {int(data.cur_day+1)} выполнен!"
        else:
            text = f"Время добавлено!\nЗа сегодня всрато {work_today // 60}h {work_today % 60:02d}m!"

        bot_message_to_chat(
            context, data.chat_id_user_reply, text, 60, data.message_id_user_reply
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


def get_is_banned(context, data):
    is_banned = False
    yesterday = data.cur_day - 1
    data = db_query(
        f"""select count(*)
            from jobs_updates join jobs on jobs.id = jobs_updates.job_id
            where job_id={data.job_id} and 
                    user_id = {data.user_id} and 
                    date_part('day', jobs_updates.created - jobs.created) = {yesterday};"""
    )[0][0]
    if data == 0:
        is_banned = True

        context.bot.send_message(
            chat_id=data.chat_id_user_reply,
            reply_to_message_id=data.message_id_user_reply,
            text=f"Мда, долбаеб. Вчера день проебал, а сегодня хочешь отметиться?",
        )

    return is_banned
