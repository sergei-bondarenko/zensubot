from html import escape
from datetime import datetime
from bot_functions import bot_message_to_chat
from database import db_query
from post_updater import PostUpdater
from telegram import ParseMode


def stickers(update, context):
    upd = PostUpdater(update)
    # Writing update to table if job_id and sticker_id is correct
    if upd.job_id and upd.sticker_id:
        if update.effective_user["username"] == "Channel_Bot":
            bot_message_to_chat(
                context,
                update["message"]["chat"]["id"],
                "Стикер от паблика НЕ засчитан. Пожалуйста, используй личный аккаунт.",
                0,
                update.message.message_id,
                ParseMode.HTML
            )
            return

        if upd.sticker_id in [56, 57, 58, 59, 60]:
            bot_message_to_chat(
                context,
                update["message"]["chat"]["id"],
                "Пятидневка больше не принимает в себя эти жуткие огромные пальцы. Слишком уж это, простите, грязное зрелище. Возможно, когда-нибудь дизайнер откопает исходники и сделает пальцы поменьше, но а пока воспользуйтесь уже <a href = 'https://t.me/addstickers/minimaal_zensu'>уменьшенными стикерами</a>.",
                0,
                update.message.message_id,
                ParseMode.HTML
            )
            return

        # Creating new users if they do not exist or updating old users
        update_users(upd)
        # Inserting new job_update
        db_query(
            f"insert into jobs_updates (user_id, job_id, sticker_id) values ({upd.user_id}, {upd.job_id}, {upd.sticker_id})",
            False,
        )

        upd.rebuild_message(context)


def update_users(data):
    user_firstname = escape(data.user_firstname)
    db_query(
        f"""insert into users (id, username, first_name) 
                values ({data.user_id}, '{data.username}', '{user_firstname}')
                on conflict (id) do update 
                set username = excluded.username, 
                    first_name = excluded.first_name;""",
        False,
    )
