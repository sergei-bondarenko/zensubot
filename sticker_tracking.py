from bot_functions import CollectData, bot_message_to_chat, rebuild_message
from database import db_query


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


def update_users(data):
    db_query(
        f"""insert into users (id, username, first_name) 
                values ({data.user_id}, '{data.username}', '{data.user_firstname}')
                on conflict (id) do update 
                set username = excluded.username, 
                    first_name = excluded.first_name;""",
        False,
    )
