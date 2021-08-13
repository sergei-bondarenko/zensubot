"""Sample finite-state machine"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from database import db_query
from refresh_posts import refresh_posts
from responses import Responses

#These constants provided to zensu_bot conv_handler
(
    PARSE_START,
    PARSE_WHERE_TO_POST,
    PARSE_TYPE,
    EDIT_TEMPLATE,
    SAVE_TEMPLATE,
    EDIT_RESPONSE_TYPE,
    PARSE_RESPONSE_TYPE,
    WRITE_RESPONSES
) = range(8)

logger = logging.getLogger(__name__)


def get_reply_keyboard(query: str) -> list:
    """Generate reply keyboard from query

    Args:
        query (str): Sql query in form (id, text)

    Returns:
        list: List of buttons
    """
    data = db_query(query)

    reply_keyboard = list()
    for item in data:
        reply_keyboard.append([InlineKeyboardButton(item[1], callback_data=item[0])])

    return reply_keyboard


def start(update: Update, context: CallbackContext) -> int:
    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} started bot"
    )

    admins = db_query(f"select id from users where is_admin = True")
    admins = {x[0] for x in admins}

    if update.effective_user.id in admins:
        reply_keyboard = [
            [InlineKeyboardButton("Добавить пятидневку в новый чат", callback_data="add_job")],
            [InlineKeyboardButton("Добавить тип пятидневки", callback_data="job_type")],
            [InlineKeyboardButton("Изменить шаблон", callback_data="edit_template")],
            [InlineKeyboardButton("Добавить реплики бота", callback_data="responses")],
            [InlineKeyboardButton("Обновить посты", callback_data="rebuild")],
            [InlineKeyboardButton("Пойти нахуй", callback_data="end")]
        ]
    else:
        reply_keyboard = [
            [InlineKeyboardButton("Я не дзендзи. Пойти нахуй", callback_data="end")]
        ]

    reply_markup = InlineKeyboardMarkup(reply_keyboard)

    update.message.reply_text("Что сделать?", reply_markup=reply_markup)

    return PARSE_START


def parse_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query.data == "add_job":

        keyboard = get_reply_keyboard(f"select id, title from chats")
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_text(
            text="Куда запостить?",
            reply_markup=reply_markup,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        return PARSE_WHERE_TO_POST
    if query.data in ("edit_template", "responses"):
        keyboard = get_reply_keyboard(f"select id, type from jobs_types")
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.edit_message_text(
            text="Выбери тип пятидневки",
            reply_markup=reply_markup,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        return EDIT_TEMPLATE if query.data == "edit_template" else EDIT_RESPONSE_TYPE
    if query.data == "rebuild":
        refresh_posts(context)

        context.bot.edit_message_text(
            text = f"Готово!",
            chat_id=query.message.chat_id, 
            message_id=query.message.message_id)

        return ConversationHandler.END
    if query.data == "end":
        context.bot.delete_message(
            chat_id=query.message.chat_id, message_id=query.message.message_id
        )
        return ConversationHandler.END


def parse_where_to_post(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.user_data["chosen_group"] = query.data

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} chosen to post at {query.data}"
    )

    keyboard = get_reply_keyboard(f"select id, type from jobs_types")
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text="Выбери тип пятидневки",
        reply_markup=reply_markup,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return PARSE_TYPE


def parse_type(update: Update, context: CallbackContext) -> int:
    query = update.callback_query

    logger.info(
        f"@{update.effective_user.username}, {update.effective_user.first_name} chosen type {query.data}"
    )

    db_query(f'update chats set jobs_type = {query.data} where id = {context.user_data["chosen_group"]}')

    context.bot.edit_message_text(
        text="Готово!",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    return ConversationHandler.END


def edit_template(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.user_data["chosen_type"] = query.data
    photo_id, caption = db_query(
        f'select photo_id, caption from post_templates where job_type = {query.data}',
        True,
    )[0]
    if photo_id == "None":
        context.bot.send_message(update.effective_chat.id, caption)
    else:
        context.bot.send_photo(update.effective_chat.id, photo_id, caption=caption)
    context.bot.send_message(update.effective_chat.id, "Отправь новый темплейт. Если отправишь только картинку, то текст останется без изменений.")
    return SAVE_TEMPLATE


def save_template(update: Update, context: CallbackContext) -> int:
    photo_id, caption = db_query(
        f'select photo_id, caption from post_templates where job_type = {context.user_data["chosen_type"]}',
        True,
    )[0]
    # TODO: Check for videos/multiple photos.
    if len(update["message"]["photo"]):
        photo_id = update["message"]["photo"][-1]["file_id"]
        if update["message"]["caption"]:
            caption = update["message"]["caption"]
        context.bot.send_photo(update.effective_chat.id, photo_id, caption=caption)
    else:
        photo_id = "None"
        caption = update["message"]["text"]
        context.bot.send_message(update.effective_chat.id, caption)
    db_query(
        f"update post_templates set photo_id = '{photo_id}', caption = '{caption}' where job_type = {context.user_data['chosen_type']};",
        False,
    )
    logger.info(f"@{update.effective_user.username} saved template for job_type = {context.user_data['chosen_type']}")
    return ConversationHandler.END


def edit_response_type(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.user_data["chosen_job_type"] = query.data

    keyboard = get_reply_keyboard(f"select id, type from response_types")
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text="Выбери тип ответа бота. Ответы идут друг за другом в формате \nResponse 1\n\nResponse 2",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup,
    )
    return PARSE_RESPONSE_TYPE

def parse_response_type(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.user_data["chosen_response_type"] = query.data

    context.bot.edit_message_text(
        text="Отправь файл в формате .txt с одной фразой в каждой строчке. Можно использовать html теги телеграм\n\nДля удаления фраз отправь .txt файл состоящий из одного пробела",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return WRITE_RESPONSES

def write_response(update: Update, context: CallbackContext) -> int:
    job_type = int(context.user_data['chosen_job_type'])
    response_type = int(context.user_data['chosen_response_type'])

    b_array = context.bot.get_file(update.message.document).download_as_bytearray()
    text = b_array.decode(encoding = 'utf-8')

    db_query(f"""insert into responses (job_type, response_type, phrase) values 
                ({job_type}, {response_type}, '{text}')
                on conflict (job_type, response_type) do update 
                set phrase = excluded.phrase;""", False)

    Responses.update(job_type, response_type, text)

    context.bot.send_message(chat_id=update.effective_chat.id, text="Готово!")
    logger.info(f"@{update.effective_user.username} written responses for job_type = {job_type} and response_type = {response_type}")
    return ConversationHandler.END
