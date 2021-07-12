import logging

from telegram import ParseMode
from telegram.error import BadRequest

from database import db_query
from bot_functions import bot_message_to_chat, fill_template

logger = logging.getLogger(__name__)

EM_TRUE = "✅"
EM_FALSE = "⚫️"
EM_FAIL = "❌"


def stickers(update, context):
    message = update.effective_message
    user = update.effective_user
    is_caption = False
    is_banned = False

    try:
        message_id = message.reply_to_message.forward_from_message_id
        group_id = message.reply_to_message.forward_from_chat.id
        text = message.reply_to_message.text
    except:
        message_id = message.reply_to_message.message_id
        group_id = message.reply_to_message.chat.id
        text = message.reply_to_message.text

    if text is None:
        try:
            text = message["reply_to_message"]["caption"]
            is_caption = True
        except:
            pass

    user_id = user.id
    username = user.username
    user_firstname = user.first_name

    job_id, sticker_id = None, None

    # Getting active jobs if they exist
    data = db_query(
        f"select id from jobs where message_id = {message_id} and chat_id = {group_id} and DATE_PART('day', now()-created)<=4"
    )
    if len(data) != 0:
        job_id = data[0][0]

    # Getting sticker id if it exist
    data = db_query(
        f"select id, power from stickers where text_id='{message.sticker.file_unique_id}'"
    )
    if len(data) != 0:
        sticker_id, sticker_power = data[0]

    # Writing update to table if job_id and sticker_id is correct
    if job_id and sticker_id:

        # Creating new users if they do not exist
        data = db_query(f"select id from users where id = {user_id}")
        if len(data) == 0:
            db_query(
                f"insert into users values ({user_id}, '{username}', '{user_firstname}')",
                False,
            )
            logger.info(
                f"User with id {user_id}, username {username}, firstname {user_firstname} added to database"
            )

        # Getting current day since start of the job
        cur_day, job_type, order_number = db_query(
            f"select DATE_PART('day', now()-created)+1, type, order_number from jobs where id = {job_id}"
        )[0]

        # updating users if today is start of the job
        if cur_day == 1:
            db_query(
                f"update users set username = '{username}', first_name = '{user_firstname}' where id = {user_id}",
                False,
            )

        # Check if user is banned
        if cur_day > 2:
            is_banned = get_is_banned(
                context,
                job_id,
                user_id,
                cur_day,
                message.chat.id,
                update.message.message_id,
            )

        # New logic
        if sticker_id > 50 and not is_banned:

            # Inserting new job_update
            db_query(
                f"insert into jobs_updates (user_id, job_id, sticker_id) values ({user_id}, {job_id}, {sticker_id})",
                False,
            )

            # Collecting data about current job progress
            data = db_query(
                f"""select user_id ,first_name as name, d1, d2, d3, d4, d5, total
                        from
                            (select user_id , sum(case when sday = 1 then power else 0 end) d1, sum(case when sday = 2 then power else 0 end) d2
                            				  , sum(case when sday = 3 then power else 0 end) d3, sum(case when sday = 4 then power else 0 end) d4
                            				  , sum(case when sday = 5 then power else 0 end) d5, sum(power) total
                            from
                                (select user_id, date_part('day', jobs_updates.created - jobs.created)+1 as sday, sticker_id
                                from jobs_updates join jobs on jobs.id = jobs_updates.job_id
                                where job_id = {job_id}) t join stickers on stickers.id = t.sticker_id
                            group by user_id) t 
                            join users on users.id=t.user_id 
                            order by total desc
                        ;"""
            )

            text = db_query(
                f"select caption from post_templates where job_type = {job_type}"
            )[0][0]
            text = fill_template(text, order_number)

            text, work_today = get_posted_message(text, data, cur_day, user_id)

            try:
                if is_caption:
                    context.bot.edit_message_caption(
                        chat_id=group_id,
                        message_id=message_id,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    context.bot.edit_message_text(
                        text=text,
                        chat_id=group_id,
                        message_id=message_id,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )

                logger.info(
                    f"Edited job with id {job_id} after posted sticker id {sticker_id} by @{username} with firstname {user_firstname}"
                )

                if work_today == sticker_power:
                    text = f"Молодец! День {int(cur_day)} выполнен!"
                else:
                    text = f"Время добавлено!\nЗа сегодня всрато {work_today // 60}h {work_today % 60:02d}m!"

                bot_message_to_chat(
                    context, message.chat.id, text, 60, update.message.message_id
                )

            except BadRequest:
                pass


def get_posted_message(text, data, cur_day, cur_user_id):
    USERS = "<b>Участники</b>"
    QUERY_OFFSET = 2

    text = text.split(f"\n\n{USERS}:")[0]

    passed = list()
    loosers = list()

    for item in data:
        is_first = True

        user_id = item[0]
        user_firstname = item[1]
        total = item[-1]

        name_phrase = f'<a href="tg://user?id={user_id}">{user_firstname}</a>'
        phrase = chr(8206)

        for i, day in enumerate(item[QUERY_OFFSET : QUERY_OFFSET + 5]):
            day = int(day)

            # Checking if today is the first activity of user
            if user_id == cur_user_id and i + 1 == cur_day:
                work_today = day

            if day == 0 and is_first and i + 1 < cur_day:
                phrase += EM_FAIL
                is_first = False
            elif day > 0:
                phrase += EM_TRUE
            else:
                phrase += EM_FALSE

        phrase += f" {str(total // 60)}h {(total % 60):02d}m"

        if is_first:
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


def get_is_banned(context, job_id, user_id, cur_day, chat_id, message_id):
    is_banned = False

    data = int(
        db_query(
            f"""select count(1)
                        from jobs_updates join jobs on jobs.id = jobs_updates.job_id
                        where job_id={job_id} and 
                                user_id = {user_id} and 
                                date_part('day', jobs_updates.created - jobs.created) + 2 = {cur_day};"""
        )[0][0]
    )
    if data == 0:
        is_banned = True

        context.bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            text=f"Мда, долбаеб. Вчера день проебал, а сегодня хочешь отметиться?",
        )

    return is_banned
