import logging
from typing import List

from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from bot_functions import bot_message_to_chat, fill_template, minutes_to_hours
from constants import EM_TRUE, EM_FAIL, EM_FALSE, EM_WEEKEND, JOB_DAYS_DURATION, USERS
from database import db_query
from responses import Responses
from telegram import InputMediaPhoto

logger = logging.getLogger(__name__)

class PostUpdater:
    """Class which applies updates to posts on demand or after sticker replies"""
    def __init__(self, update):
        """If update is given as tuple from query then handling update as on_demand
           If update is given as Update then parsing wrapper Update class for entities
        """

        if isinstance(update, tuple):
            self.on_demand = True
            (self.job_id, self.job_type, self.start_date, self.job_message_id,
            self.job_chat_id, self.order_number, 
            self.cur_day, self.user_id, self.is_caption) = update

        elif isinstance(update, Update):
            self.on_demand = False
            message = update["message"]
            reply = message["reply_to_message"]
            user = update.effective_user
            try:
                # Job posted to channel
                self.job_chat_id = reply["forward_from_chat"]["id"]
                self.job_message_id = reply["forward_from_message_id"]
            except TypeError:
                # Job posted to chat
                self.job_chat_id = message["chat"]["id"]
                self.job_message_id = reply["message_id"]

            self.user_id = user["id"]
            self.username = user["username"]
            self.user_firstname = user["first_name"]

            self.chat_id_user_reply = message["chat"]["id"]
            self.message_id_user_reply = message["message_id"]

            self.is_caption = bool(reply.caption)

            # Getting active jobs if they exist
            try:
                (
                    self.job_id, self.start_date, self.cur_day, self.job_type, self.order_number,
                    self.sticker_id, self.sticker_power, self.yesterday_work,
                ) = db_query(
                    f"""select jobs.id, jobs.created, DATE_PART('day', now()-jobs.created), type, order_number , stickers.id, power, count(jobs_updates.created)
                            from jobs left join jobs_updates 
                            on jobs.id=jobs_updates.job_id and user_id={self.user_id} and date_part('day', jobs_updates.created - jobs.created) = least(4, DATE_PART('day', now()-jobs.created) - 1)
                            left join stickers on stickers.text_id = '{message['sticker']['file_unique_id']}'
                            where message_id = {self.job_message_id} and chat_id = {self.job_chat_id} and DATE_PART('day', now()-jobs.created) < {JOB_DAYS_DURATION}
                        group by jobs.id, jobs.created, DATE_PART('day', now()-jobs.created), type, order_number , stickers.id, power
                """
                )[0]
            except IndexError:
                # Job not exists
                self.job_id = self.sticker_id = None


    def rebuild_message(self, context: CallbackContext) -> None:
        """Generates message trough call of fill_template and get_posted_message and tries to edit already posted message. If message stays the same BadRequest exception is passed
        """
        photo_id, text = db_query(
            f"select photo_id, caption from post_templates where job_type = {self.job_type}"
        )[0]
        text = fill_template(text, self.order_number, self.start_date)
        text, work_today = self.get_posted_message(text)

        try:
            if self.is_caption:
                context.bot.edit_message_media(
                    chat_id=self.job_chat_id,
                    message_id=self.job_message_id,
                    media=InputMediaPhoto(
                        media=photo_id,
                        caption=text,
                        parse_mode=ParseMode.HTML),
                )
            else:
                context.bot.edit_message_text(
                    text=text,
                    chat_id=self.job_chat_id,
                    message_id=self.job_message_id,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )

            if not self.on_demand:
                logger.info(
                    f"Edited job with id {self.job_id} after posted sticker id {self.sticker_id} by @{self.username} with firstname {self.user_firstname}"
                )

                if work_today == self.sticker_power:
                    r_1 = Responses.get(self.job_type, 1)
                    r_2 = Responses.get(self.job_type, 2)
                    line = '' if r_1 == '' else '\n\n'
                    if self.cur_day == 5:
                        text = f"День 6/5 выполнен! Держи ⭐️"
                    elif self.cur_day == 6:
                        text = f"День 7/5 выполнен! Держи 🌟"
                    else:
                        text = f"День {int(self.cur_day+1)}/5 выполнен!"
                    text += f"\n\n{r_1 + line + r_2}"
                else:
                    text = f"За сегодня добавлено {minutes_to_hours(work_today)}!"

                bot_message_to_chat(
                    context, self.chat_id_user_reply, text, 60, self.message_id_user_reply, ParseMode.HTML
                )
            else:
                logger.info(f"Edited job with id {self.job_id} after ON DEMAND update")

        except BadRequest:
            pass


    def get_posted_message(self, text: str) -> None:
        # Collecting data about current job progress
        query = db_query(
            f"""select user_id, first_name, total, d0, d1, d2, d3, d4, d5, d6
                    from
                        (select user_id , sum(case when sday = 0 then power else 0 end) d0, sum(case when sday = 1 then power else 0 end) d1
                                            , sum(case when sday = 2 then power else 0 end) d2, sum(case when sday = 3 then power else 0 end) d3
                                            , sum(case when sday = 4 then power else 0 end) d4, sum(case when sday = 5 then power else 0 end) d5
                                            , sum(case when sday = 6 then power else 0 end) d6, sum(power) total
                        from
                            (select user_id, date_part('day', jobs_updates.created - jobs.created) as sday, sticker_id
                            from jobs_updates join jobs on jobs.id = jobs_updates.job_id
                            where job_id = {self.job_id}) t join stickers on stickers.id = t.sticker_id
                        group by user_id) t 
                        join users on users.id=t.user_id 
                        order by total desc
                    ;"""
        )

        text = text.split(f"\n\n{USERS}:")[0]

        passed = list()
        loosers = list() 
        work_today = 0

        for user_id, user_firstname, total, *days in query:
            is_first_fail = True
            weekends = list()
            # chr(8206) is a mark to keep text format left to right
            name_phrase = (
                f'{chr(8206)}<a href="tg://user?id={user_id}">{user_firstname}</a>'
            )
            phrase = str()

            for i, work in enumerate(days):
                work = int(work)

                if not self.on_demand:
                    # Checking if today is the first activity of user
                    if user_id == self.user_id and i == self.cur_day:
                        work_today = work
                elif i == self.cur_day:
                    work_today = work
                
                # Weekends
                if i >= 5:
                    if i == 5 and work > 0:
                        weekends.append('⭐')
                    if i == 6 and work > 0:
                        weekends.append('🌟')
                # Workdays
                elif work == 0 and i < self.cur_day:
                    #phrase += EM_FAIL
                    phrase += '❌'
                    is_first_fail = False
                elif work > 0:
                    #phrase += EM_TRUE
                    if work >= 240:
                        phrase += '💎'
                    elif work >= 120:
                        phrase += '🔴'
                    elif work >= 60:
                        phrase += '🟠'
                    elif work >= 30:
                        phrase += '🟡'
                    else:
                        phrase += '🟢'
                else:
                    #phrase += EM_FALSE
                    phrase += '⚫'

            phrase += f"\n🕗<code>{minutes_to_hours(total)}</code>"
            if work_today > 0:
                phrase += f"<code>[+{minutes_to_hours(work_today)}]</code>"
            weekends = ''.join(weekends)

            if is_first_fail:
                passed.append((name_phrase, phrase, weekends))
            else:
                loosers.append((name_phrase, phrase, weekends))

        added_text = str()
        i, j = 0, 0

        for i, (name_phrase, phrase, weekends) in enumerate(passed):
            added_text += f"{i+1}. {name_phrase} {weekends}\n{phrase}\n\n"

        for j, (name_phrase, phrase, weekends) in enumerate(loosers):
            added_text += f"{i + j + 2 + (-1 if i==0 else 0)}. <s>{name_phrase}</s> {weekends}\n{phrase}\n\n"
        text += "\n\n" + added_text

        return text, work_today
