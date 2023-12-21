"""Commands which are publicly accessible through /command"""
import logging

from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot_functions import minutes_to_hours
from database import db_query
from telegraph_posting import TelegraphPost

logger = logging.getLogger(__name__)

def help(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id = update.effective_message.chat_id,
                            text = "Отмечайся каждый день <a href = 'https://t.me/addstickers/minimaal_zensu'>стикером</a>. За день можно отмечаться несколько раз, время суммируется. Участие в пятидневке в выходные дни по желанию, однако время тоже засчитывается.",
                            parse_mode = ParseMode.HTML,
                            disable_web_page_preview = True)

def stat(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id = update.effective_message.chat_id, 
                            text = get_stat(update),
                            parse_mode = ParseMode.HTML,
                            disable_web_page_preview = True)
    logger.info(f"Generated statistics for @{update.effective_user.username} in chat id {update.effective_message.chat_id}")

def get_stat(update: Update) -> str:
    """Function which generates aligned stat and sends it to telegra.ph. 
    We are using telegra.ph here because telegram messages are not promising to hold the alignment.
    Alignment which we are getting in telegra.ph heavily holds on EMPTY_SYMBOL.

    Returns:
        str: text of message
    """
    EMPTY_SYMBOL = ' ‎'

    user_id = update.effective_user["id"]
    user_name = update.effective_user["first_name"]

    query = db_query(f"""
        SELECT
           type,
           SUM(CASE WHEN
                   d0 > 0 AND
                   d1 > 0 AND
                   d2 > 0 AND
                   d3 > 0 AND
                   d4 > 0
               THEN 1 ELSE 0 END) AS ended,
           SUM(CASE WHEN
                   d0 > 0 OR
                   d1 > 0 OR
                   d2 > 0 OR
                   d3 > 0 OR
                   d4 > 0 OR
                   d5 > 0 OR
                   d6 > 0
               THEN 1 ELSE 0 END) AS started,
           COALESCE(SUM(summ), 0)::INTEGER
        FROM
            (
                SELECT
                    jobs_types."type",
                    MAX(jobs_types.id) AS types_id,
                    jobs.id,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 0 THEN power ELSE 0 END) d0,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 1 THEN power ELSE 0 END) d1,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 2 THEN power ELSE 0 END) d2,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 3 THEN power ELSE 0 END) d3,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 4 THEN power ELSE 0 END) d4,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 5 THEN power ELSE 0 END) d5,
                    SUM(CASE WHEN DATE_PART('day', jobs_updates.created - jobs.created) = 6 THEN power ELSE 0 END) d6,
                    SUM(COALESCE(stickers.power, 15 * power(2,(sticker_id-1)%5))) AS summ
                FROM jobs_types
                    LEFT JOIN jobs ON jobs.type = jobs_types.id
                    LEFT JOIN jobs_updates on jobs.id = jobs_updates.job_id AND user_id = {user_id}
                    LEFT JOIN stickers ON stickers.id = jobs_updates.sticker_id
                WHERE jobs_types.id != 0
                GROUP BY jobs_types."type", jobs.id
            ) t
        GROUP BY type, types_id
        ORDER BY types_id
    """)
    
    text = f'<b>Статистика пятидневок {user_name}</b><br>'
    text += f"<pre> ‎ ‎ ‎ ‎ ‎  ‎Тип ‎ ‎ ‎ ‎ ‎ ‎Закончено ‎‏‏‎ ‎Время<br>"
    for i, (type, ended, started, summ) in enumerate(query):
        if summ == 0:
            continue
        length1 = 13 - len(type)
        margin1 = length1*EMPTY_SYMBOL if length1 != 0 else ''
        if any(c in ['️', '✍'] for c in type):
            margin1 += EMPTY_SYMBOL
        length2 = 9 - len(f"{ended}/{started}")
        margin2 = length2 * EMPTY_SYMBOL
        text += f"""{type}{margin1}{2*EMPTY_SYMBOL}{ended}/{started}{margin2}{minutes_to_hours(summ, 1)}<br>"""

    text += "</pre>"
    link = TelegraphPost.post_to_telegraph(text)

    text = f'''Твоя статистика готова, <a href="tg://user?id={user_id}">{user_name}</a>\n\n{link}'''
    return text
