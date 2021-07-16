from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode


def inline_stat(update, context) -> None:
    """Handle the inline query."""
    query = update.inline_query.query

    if query == "":
        update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="Получить статистику по пятидневкам",
                    input_message_content=InputTextMessageContent(
                        "<>Медитации 2/3 54h 20m", ParseMode=ParseMode.HTML
                    ),
                    thumb_url="https://i.imgur.com/o46IfVV.jpeg"
                )
            ]
        )

def get_stats():
    pass
