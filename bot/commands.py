"""Commands which are publicly accessible through /command"""
import logging

from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from bot_functions import minutes_to_hours
from database import db_query
from telegraph_posting import TelegraphPost

logger = logging.getLogger(__name__)

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

    query = db_query(f"""select type, sum(case when max >= 4 then 1 else 0 end) as ended, count(max) as started, coalesce(sum(summ), 0)::integer
                            from
                                (select jobs_types."type", max(jobs_types.id) as types_id, jobs.id, max(date_part('day', jobs_updates.created - jobs.created)), sum(coalesce(stickers.power, 15 * power(2,(sticker_id-1)%5))) as summ
                                    from jobs_types left join jobs on jobs.type = jobs_types.id left join jobs_updates on jobs.id = jobs_updates.job_id and user_id = {user_id} left join stickers on stickers.id = jobs_updates.sticker_id 
                                    where  jobs_types.id != 0
                                    group by jobs_types."type", jobs.id) t
                            group by type, types_id
                            order by types_id""")
    
    text = f'<b>Статистика пятидневок {user_name}</b><br>'
    text += f"<pre> ‎ ‎ ‎ ‎ ‎  ‎Тип ‎ ‎ ‎ ‎ ‎ ‎Закончено ‎‏‏‎ ‎Время<br>"
    for i, (type, ended, started, summ) in enumerate(query):
        length1 = 13 - len(type)
        margin1 = length1*EMPTY_SYMBOL if length1 != 0 else ''
        if any(c in ['⌨', '✍', '⚙️'] for c in type):
            margin1 += EMPTY_SYMBOL
        length2 = 9 - len(f"{ended}/{started}")
        margin2 = length2 * EMPTY_SYMBOL
        text += f"""{type}{margin1}{2*EMPTY_SYMBOL}{ended}/{started}{margin2}{minutes_to_hours(summ, 1)}<br>"""

    text += "</pre>"
    link = TelegraphPost.post_to_telegraph(text)

    text = f'''Твоя статистика готова, <a href="tg://user?id={user_id}">{user_name}</a>\n\n{link}'''
    return text
