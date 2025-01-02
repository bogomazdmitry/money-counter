from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application


async def reply_text(update: Update, app, message: str):
    if update.message is not None:
        await update.message.reply_text(message)
        return
    if update.edited_message is not None:
        await update.edited_message.reply_text(message)
        return
    await app.bot.send_message(update.effective_chat.id, message)


async def reply_html(update: Update, app: Application, message: str):
    if update.message is not None:
        await reply_html(update, app, message)
        return
    if update.edited_message is not None:
        await update.edited_message.reply_html(message)
        return
    await app.bot.send_message(
        update.effective_chat.id, message, parse_mode=ParseMode.HTML
    )
