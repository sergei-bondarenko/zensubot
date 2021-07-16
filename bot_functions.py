import re
from datetime import datetime, timedelta

def bot_message_to_chat(context, chat_id, text, delete = 0, reply_to_message = None, parse_mode = None):
    posted_message = context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to_message,
        parse_mode = parse_mode
    )
    if delete != 0:
        context.job_queue.run_once(
            delete_message,
            delete,
            context=[posted_message.message_id, chat_id],
        )

def delete_message(context) -> None:
    job = context.job.context
    context.bot.delete_message(chat_id=job[1], message_id=job[0])


def fill_template(text, n, start_date = datetime.now()) -> str:
    UTC_PLUS = 3
    text = re.sub('([#№])N', f"\g<1>{n}", text, flags=re.I)
    for day in range(5):
        date = start_date + timedelta(days=day, hours=UTC_PLUS)
        open, close = ('','') if datetime.now() - date < timedelta(hours = 24 - UTC_PLUS) else ('<b><s>', '</s></b>')
        date = date.strftime("%d.%m.%Y")
        text = re.sub(f"{day+1} [-–—] NN.NN.NNNN", f"{open}{day+1} — {date}{close}", text, flags=re.I)
    return text


def minutes_to_hours(minutes):
    return f"{minutes // 60}h {(minutes % 60):02d}m"