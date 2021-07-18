from database import db_query
from bot_functions import bot_message_to_chat


def plus(update, context):
    THRESHOLD = 3
    AUTODESTRUCTION = 0
    STATUS = ["administrator", "creator"]

    chat_id = update.effective_message.chat.id
    replied_message = update.message.reply_to_message.message_id
    plus_message = update.message.message_id

    user_id = update.effective_user.id

    user_status = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id).status

    if user_id == update.message.reply_to_message.from_user.id:
        text = "Твой голос не учтен! Самолайк не считается."
        bot_message_to_chat(
            context,
            chat_id,
            text,
            60,
            plus_message,
        )
        return None

    # Filter only accepted users
    if user_status not in STATUS:
        text = "Твой голос не учтен! Для голосования нужно получить прописку в чате."
        bot_message_to_chat(
            context,
            chat_id,
            text,
            60,
            plus_message,
        )
        return None

    try:
        forward_from_chat_id = update.message.reply_to_message.forward_from_chat.id
    except AttributeError:
        forward_from_chat_id = 0

    # Getting chats to post
    to_chat_ids = db_query(
        f"select parent from chats_connection where child = {chat_id}"
    )
    to_chat_ids = {x[0] for x in to_chat_ids}

    # Filter if chat is not enabled to pass plus
    if len(to_chat_ids) == 0:
        return None
    # Filter if user tries to plus message from parent chat
    elif forward_from_chat_id in to_chat_ids:
        text = "Зачем ты голосуешь за пост, который уже есть в паблике?"
        bot_message_to_chat(context, chat_id, text, 60, plus_message)
        return None

    # Getting info about post state and current user votes
    cur_amount, has_voted = db_query(
        f"""select count(1) + 1, coalesce(sum(case when user_id = {user_id} then 1 else 0 end), 0) 
            from plus_data 
            where chat_id = {chat_id} and message_id = {replied_message}"""
    )[0]

    if has_voted != 0:
        text = "Ты уже голосовал, грязный и мерзкий!"
        bot_message_to_chat(
            context,
            chat_id,
            text,
            AUTODESTRUCTION,
            plus_message,
        )
        return None

    if cur_amount == THRESHOLD:

        db_query(
            f"insert into plus_data (chat_id, message_id, user_id) values ({chat_id}, {replied_message}, {user_id})",
            False
        )

        for chat in to_chat_ids:
            context.bot.copy_message(
                chat_id=chat, from_chat_id=chat_id, message_id=replied_message
            )

    elif cur_amount < THRESHOLD:
        post_to = db_query(f"select title from chats where id in ({','.join(map(str, to_chat_ids))})")
        post_to = {x[0] for x in post_to}
        text = f"{cur_amount} из {THRESHOLD} + до поста в {chr(10).join(post_to)}"
        bot_message_to_chat(context, chat_id, text, AUTODESTRUCTION, replied_message)

        db_query(
            f"insert into plus_data (chat_id, message_id, user_id) values ({chat_id}, {replied_message}, {user_id})",
            False
        )

    else:
        text = "Пост уже отправлен!"
        bot_message_to_chat(context, chat_id, text, AUTODESTRUCTION, plus_message)

    return None
