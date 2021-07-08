from sticker_tracking import delete_message


def plus(update, context):
    posted_message = context.bot.send_message(
        chat_id=update.effective_message.chat.id,
        reply_to_message_id=update.message.message_id,
        text="+ добавлен!",
    )

    context.job_queue.run_once(
        delete_message,
        10,
        context=[posted_message.message_id, update.effective_message.chat.id],
    )
