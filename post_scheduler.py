from datetime import datetime, timedelta

def callback_minute(context):
    # context.bot.send_message(chat_id='@guhccssa', text='Тестирую отправку сообщения каждые 10 секунд.')
    posted_message = context.bot.copy_message(chat_id='-1001211284566', from_chat_id = '-1001575457049', message_id = 3)

def create_post(job):
    # interval = timedelta(days = 5)
    interval = timedelta(minutes = 5)
    # job_minute = job.run_repeating(callback = callback_minute, interval = interval, first = datetime(2021, 7, 5, 18, 50))
    job_minute = job.run_repeating(callback = callback_minute, interval = interval)

