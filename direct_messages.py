import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler

from database import db_query
from responses import Responses

(
    PARSE_START,
    PARSE_WHERE_TO_POST,
    PARSE_TYPE,
    CREATE_POST,
    EDIT_TEMPLATE,
    SAVE_TEMPLATE,
    EDIT_RESPONSE_TYPE,
    PARSE_RESPONSE_TYPE,
    WRITE_RESPONSES
) = range(9)

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
            [InlineKeyboardButton("Добавить реплики бота", callback_data="responses")],
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
        text="Выбери тип пятидневки",
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
        text="Напиши здесь свой пост",
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

    context.bot.send_message(chat_id=update.effective_chat.id, text="Готово!")
    return ConversationHandler.END


def cancel(update, context) -> int:
    return ConversationHandler.END


def edit_template(update, context) -> int:
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


def save_template(update, context) -> int:
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
    return ConversationHandler.END


def edit_response_type(update, context):
    query = update.callback_query
    context.user_data["chosen_job_type"] = query.data

    keyboard = get_reply_keyboard(f"select id, type from response_types")
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text="Выбери тип ответа бота",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup,
    )
    return PARSE_RESPONSE_TYPE

def parse_response_type(update, context):
    query = update.callback_query
    context.user_data["chosen_response_type"] = query.data

    context.bot.edit_message_text(
        text="Отправь файл в формате .txt с одной фразой в каждой строчке. Можно использовать html теги телеграм",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return WRITE_RESPONSES

def write_response(update, context):
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
    return ConversationHandler.END


def stat(update, context):
    message = update.message
    context.bot.send_message(chat_id = update.effective_message.chat_id, 
                             text = get_stat(update),
                             parse_mode = ParseMode.HTML)

def get_stat(update):
    user_id = update.effective_user["id"]
    user_name = update.effective_user["first_name"]
    query = db_query(f"""select type, sum(case when max = 4 then 1 else 0 end) as ended, count(max) as started, coalesce(sum(summ), 0)
                            from
                                (select jobs_types."type", max(jobs_types.id) as types_id, jobs.id, max(date_part('day', jobs_updates.created - jobs.created)), sum(coalesce(stickers.power, 15 * power(2,sticker_id%5-1))) as summ
                                    from jobs_types left join jobs on jobs.type = jobs_types.id left join jobs_updates on jobs.id = jobs_updates.job_id and user_id = 919075076 left join stickers on stickers.id = jobs_updates.sticker_id 
                                    where  jobs_types.id != 0
                                    group by jobs_types."type", jobs.id) t
                            group by type, types_id
                            order by types_id""")

    text = f'<b>Статистика пятидневок <a href="tg://user?id={user_id}">{user_name}</a></b>\n\n'
    text += f"<pre>Тип\tЗакончено/Начато\tВремя</pre>\n"

    for type, ended, started, sum in query:
        text += f"<pre>{type}\t{ended}/{started}\t{sum}</pre>\n"

    return text

