import logging

from telegram import Chat, ChatMember

from database import db_query

logger = logging.getLogger(__name__)


def extract_status_change(
    chat_member_update,
):
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = (
        old_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    )
    is_member = (
        new_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    )

    return was_member, is_member


def track_chats(update, context) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.title is None:
        logger.info(f"Can't track chat: {chat.id}.")
        return
    else:
        title = chat.title.replace("'", "''")
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            logger.info("%s started the bot", cause_name)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info(
                "%s added the bot to the group %s with id %s",
                cause_name,
                chat.title,
                chat.id,
            )
            db_query(f"insert into chats values ({chat.id}, '{title} чат')", False)
        elif was_member and not is_member:
            logger.info(
                "%s removed the bot from the group %s with id %s",
                cause_name,
                chat.title,
                chat.id,
            )
            db_query(f"delete from chats where id = {chat.id}", False)
    else:
        if not was_member and is_member:
            logger.info(
                "%s added the bot to the channel %s with id %s",
                cause_name,
                chat.title,
                chat.id,
            )
            db_query(
                f"insert into chats values ({chat.id}, '{title} канал')", False
            )
        elif was_member and not is_member:
            logger.info(
                "%s removed the bot from the channel %s with id %s",
                cause_name,
                chat.title,
                chat.id,
            )
            db_query(f"delete from chats where id = {chat.id}", False)
