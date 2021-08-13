from bot_functions import bot_message_to_chat
from database import db_query
from post_updater import PostUpdater


def stickers(update, context):
    upd = PostUpdater(update)

    # Writing update to table if job_id and sticker_id is correct
    if upd.job_id and upd.sticker_id:
        # Creating new users if they do not exist or updating old users
        update_users(upd)
        # Inserting new job_update
        db_query(
            f"insert into jobs_updates (user_id, job_id, sticker_id) values ({upd.user_id}, {upd.job_id}, {upd.sticker_id})",
            False,
        )

        upd.rebuild_message(context)


def update_users(data):
    db_query(
        f"""insert into users (id, username, first_name) 
                values ({data.user_id}, '{data.username}', '{data.user_firstname}')
                on conflict (id) do update 
                set username = excluded.username, 
                    first_name = excluded.first_name;""",
        False,
    )
