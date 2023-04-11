import logging
from datetime import datetime, time
from telegram import ParseMode

from database import db_query
from constants import POST_HOUR, POST_MINUTE, REMINDER_DELTA, REMINDER_DAYS
from bot_functions import bot_message_to_chat


logger = logging.getLogger(__name__)

def reminder_callback(context):
    if datetime.now().weekday() == 0:
        query = """(select coalesce(child, chat_id) as chat_id, users.id, users.first_name
                    from jobs_updates join jobs on jobs.id = jobs_updates.job_id 
                            join (select id, rank() over (partition by type order by id desc) as rank from jobs where type != 0) t on t.id = jobs.id and t.rank=2
                            join users on users.id = jobs_updates.user_id 
                            join chats on chats.id = jobs.chat_id and chats.jobs_type is not null
                            left join chats_connection on parent = chat_id
                    where date_part('day', jobs_updates.created - jobs.created) = 0
                        and chats.is_enabled = true
                    group by coalesce(child, chat_id), users.id, users.first_name)

                    except 

                    (select coalesce(child, chat_id), users.id, users.first_name
                    from jobs_updates join jobs on jobs.id = jobs_updates.job_id join users on users.id = jobs_updates.user_id
                            left join chats_connection on parent = chat_id
                    where date_part('day', jobs_updates.created - jobs.created) = date_part('day', now() - jobs.created)
                    group by coalesce(child, chat_id), users.id, users.first_name)

                    order by chat_id
        """
    else:
        query = """(select coalesce(child, chat_id) as chat_id, users.id, users.first_name
                    from jobs_updates join jobs on jobs.id = jobs_updates.job_id join users on users.id = jobs_updates.user_id 
                            left join chats_connection on parent = chat_id
                    where date_part('day', jobs_updates.created - jobs.created) = date_part('day', now() - jobs.created) - 1
                    group by coalesce(child, chat_id), users.id, users.first_name 

                    except 

                    select coalesce(child, chat_id), users.id, users.first_name
                    from jobs_updates join jobs on jobs.id = jobs_updates.job_id join users on users.id = jobs_updates.user_id 
                            left join chats_connection on parent = chat_id
                    where date_part('day', jobs_updates.created - jobs.created) = date_part('day', now() - jobs.created)
                    group by coalesce(child, chat_id), users.id, users.first_name )

                    order by chat_id
        """
    last_chat_id = None
    text = str()
    
    for chat_id, user_id, user_name in db_query(query):
        if last_chat_id != chat_id and last_chat_id is not None:
            text += f"день закончится через {REMINDER_DELTA} часа. Ты не забыл(а) отметиться?"
            bot_message_to_chat(context, last_chat_id, text, parse_mode = ParseMode.HTML)
            text = str()
        text += f'{chr(8206)}<a href="tg://user?id={user_id}">{user_name}</a>, '
        last_chat_id = chat_id
    text += f"день закончится через {REMINDER_DELTA} часа. Ты не забыл отметиться?"
    bot_message_to_chat(context, last_chat_id, text, parse_mode = ParseMode.HTML)


def reminder(job):
    job.run_daily(callback = reminder_callback, time = time(POST_HOUR - REMINDER_DELTA, POST_MINUTE), days = REMINDER_DAYS, name = 'reminder_ok')
