import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from database import db_query

(
    PARSE_START,
    PARSE_WHERE_TO_POST,
    PARSE_TYPE,
    CREATE_POST,
    EDIT_TEMPLATE
) = range(5)

logger = logging.getLogger(__name__)


def get_reply_keyboard(query):
    data = db_query(query)

    reply_keyboard = list()
    for item in data:
        reply_keyboard.append([InlineKeyboardButton(item[1], callback_data=item[0])])

    return reply_keyboard


def start(update, context) -> int:

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} started bot"
    )

    admins = db_query(f"select id from users where is_admin = True")
    admins = {x[0] for x in admins}

    if update.effective_user.id in admins:
        reply_keyboard = [
            [InlineKeyboardButton("Добавить пост", callback_data="add_post")],
            [InlineKeyboardButton("Изменить шаблон", callback_data="edit_template")],
            [InlineKeyboardButton("Пойти нахуй", callback_data="end")]
        ]
    else:
        reply_keyboard = [
            [InlineKeyboardButton("Я не дзендзи. Пойти нахуй", callback_data="end")]
        ]

    reply_markup = InlineKeyboardMarkup(reply_keyboard)

    update.message.reply_text("Что сделать?", reply_markup=reply_markup)

    return PARSE_START


def parse_start(update, context) -> int:
    query = update.callback_query
    if query.data == "add_post":

        keyboard = get_reply_keyboard(f"select id, title from chats")
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_text(
            text="Куда запостить?",
            reply_markup=reply_markup,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        return PARSE_WHERE_TO_POST
    if query.data == "edit_template":
        data = db_query(
            f'select photo_id, caption from post_templates where job_type = 1',
            True,
        )
        context.bot.send_message(update.effective_chat.id, str(data))
 #       if photo_id:
 #           context.bot.send_photo(update.effective_chat.id, photo_id, caption=caption)
 #       else:
 #           context.bot.send_message(update.effective_chat.id, caption)
 #       context.bot.send_message(update.effective_chat.id, "Отправь новый темплейт.")
        return EDIT_TEMPLATE
    if query.data == "end":
        context.bot.delete_message(
            chat_id=query.message.chat_id, message_id=query.message.message_id
        )
        return ConversationHandler.END


def parse_where_to_post(update, context) -> int:
    query = update.callback_query
    context.user_data["chosen_group"] = query.data

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} chosen to post at {query.data}"
    )

    keyboard = get_reply_keyboard(f"select id, type from jobs_types")
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text="Choose type of pyatidnevka",
        reply_markup=reply_markup,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return PARSE_TYPE


def parse_type(update, context) -> int:
    query = update.callback_query
    context.user_data["chosen_type"] = query.data

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} chosen type {query.data}"
    )

    context.bot.edit_message_text(
        text="Write here your post",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )

    return CREATE_POST


def create_post(update, context) -> int:
    # context.bot.send_message(chat_id=update.effective_chat.id, text=context.user_data["chosen_group"] + '\n\n' + update.message.text)
    posted_message = context.bot.copy_message(
        chat_id=context.user_data["chosen_group"],
        from_chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
    )

    db_query(
        f'insert into jobs(message_id, chat_id, type) values ({posted_message.message_id}, {context.user_data["chosen_group"]}, {context.user_data["chosen_type"]});',
        False,
    )

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} posted message to {context.user_data['chosen_group']}"
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text="Done!")
    return ConversationHandler.END


def cancel(update, context) -> int:
    return ConversationHandler.END


def edit_template(update, context) -> int:
    # TODO: Selection of chats must be here.
    # context.bot.send_message(update.effective_chat.id, str(update))
    photo_id = None
    caption = None
    # TODO: Check for videos/multiple photos.
    if len(update["message"]["photo"]):
        context.bot.send_photo(update.effective_chat.id, update["message"]["photo"][-1]["file_id"], caption=update["message"]["caption"])
        photo_id = update["message"]["photo"][-1]["file_id"]
        caption = update["message"]["caption"]
    else:
        context.bot.send_message(update.effective_chat.id, update["message"]["text"])
        caption = update["message"]["text"]
    db_query(
        f"update post_templates set photo_id = '{photo_id}', caption = '{caption}' where job_type = 1;",
        False,
    )
    # TODO: Proceed to save_template.
    return ConversationHandler.END
