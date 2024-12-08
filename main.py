import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from state import change_limit_for_type, get_balance_info, reset_limits_for_chat, spend_balance_for_type, upsert_balance_type

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

# Check for necessary environment variables
def check_env_variables():
    if 'TELEGRAM_BOT_KEY' not in os.environ:
        raise ValueError("TELEGRAM_BOT_KEY not set in environment variables")

check_env_variables()

TELEGRAM_BOT_KEY = os.getenv("TELEGRAM_BOT_KEY")
WEB_HOOK_HOST = os.getenv("WEB_HOOK_HOST")
app = Application.builder().token(TELEGRAM_BOT_KEY).build()

# Define a few command handlers. These usually take the two arguments update and context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Welcome to the Balance Bot.",
        reply_markup=ForceReply(selective=True),
    )
    await update.message.reply_text(
        "I can help you keep track of your balance in this chat. "
        "Use /help to see the available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Welcome message and basic information.\n"
        "/help - Show this help message.\n"
        "/get_all_balance_info - Get full info about balance.\n"
        "/upsert_balance <limit> <type> - Set the current balance to the specified limit.\n"
        "/change_limit <limit> <type> - Change limit for balance.\n"
        "/reset_limits - Reset all balances.\n"
        "Simply send a message with a number to count that amount and update the balance."
    )
    await update.message.reply_text(help_text)

# Send all balance info to chat with formatted version, like as <Type>: <balance>/<limit>
async def get_all_balance_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get all balance info."""
    logging.info(f"Get all balance info for chat {update.message.chat_id}")
    chat_id = update.message.chat_id
    balance_info = await get_balance_info(context, chat_id)
    if balance_info:
        result_string = "Balance info:\n"
        for type, info in balance_info.items():
            result_string += f"{type}: {info['balance']}/{info['limit']}\n"
        await update.message.reply_text(result_string)
    else:
        await update.message.reply_text("No balances found.")

async def upsert_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upsert balance."""
    chat_id = update.message.chat_id
    logging.info(f"Upsert balance for chat {chat_id}")
    args = update.message.text.strip().split()[1:]
    if len(args) != 2:
        await update.message.reply_text("Please send two arguments: type and limit.")
        return
    limit, type = args
    try:
        limit = float(limit)
    except ValueError:
        await update.message.reply_text("Limit must be a number.")
        return
    await upsert_balance_type(context, chat_id, type, limit)
    await update.message.reply_text(f"Balance for {type} set to {limit}.")

async def change_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change limit."""
    logging.info(f"Change limit for chat {update.message.chat_id}")
    chat_id = update.message.chat_id
    args = update.message.text.strip().split()[1:]
    if len(args) != 2:
        await update.message.reply_text("Please send two arguments: type and limit.")
        return
    limit, type = args
    try:
        limit = float(limit)
    except ValueError:
        await update.message.reply_text("Limit must be a number.")
        return
    result = await change_limit_for_type(context, chat_id, type, limit)
    if result:
        await update.message.reply_text(f"Limit for {type} changed to {limit}.")
    else:
        await update.message.reply_text(f"No balance found for {type}.")

async def reset_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset limits."""
    logging.info(f"Reset limits for chat {update.message.chat_id}")
    chat_id = update.message.chat_id
    result = await reset_limits_for_chat(context, chat_id)
    if result:
        if 'error' in result:
            await update.message.reply_text(result['error'])
            return
        result_string = "Old balances:\n"
        for type, info in result['old'].items():
            result_string += f"{type}: {info['balance']}/{info['limit']}\n"
        result_string += "\nBalances reset."
    else:
        result_string = "No balances found."
    await update.message.reply_text(result_string)

async def spend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Spend money."""
    logging.info(f"Count money for chat {update.message.chat_id}")
    chat_id = update.message.chat_id

    try:
        parts = update.message.text.strip().split()
        amount_message_text = parts[0]
        type = parts[1]
        logging.info(f"Spend money with {amount_message_text}")
        amount = float(amount_message_text)
        new_balance = await spend_balance_for_type(context, chat_id, type, amount)
        if new_balance is None:
            await update.message.reply_text(f"No balance found for {type}.")
        else:
            await update.message.reply_text(f"Spent {amount} for type {type}. Current balance is {new_balance}.")
    except ValueError:
        await update.message.reply_text("Please send a valid number.")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("get_all_balance_info", get_all_balance_info))
app.add_handler(CommandHandler("upsert_balance", upsert_balance))
app.add_handler(CommandHandler("change_limit", change_limit))
app.add_handler(CommandHandler("reset_limits", reset_limits))

# on non command i.e message - echo the message on Telegram
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, spend))

if WEB_HOOK_HOST:
    app.bot.set_webhook(WEB_HOOK_HOST, allowed_updates=Update.ALL_TYPES)
    app.run_webhook(port=5000, listen="0.0.0.0", webhook_url=WEB_HOOK_HOST)
else:
    app.run_polling(allowed_updates=Update.ALL_TYPES)
