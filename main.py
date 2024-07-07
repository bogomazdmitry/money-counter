import os
import logging
from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
        "/set_current_balance <amount> - Set the current balance to the specified amount.\n"
        "/get_current_balance - Get the current balance.\n"
        "Simply send a message with a number to count that amount and update the balance."
    )
    await update.message.reply_text(help_text)

async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Count money."""
    chat_data = context.chat_data

    try:
        message_text = update.message.text.strip().split()[0]
        logging.info(f"Count money with {message_text}")
        amount = float(message_text)
        if 'balance' in chat_data:
            chat_data['balance'] -= amount
        else:
            chat_data['balance'] = -amount
        await update.message.reply_text(f"Counted {amount}. Current balance is {chat_data['balance']}.")
    except ValueError:
        await update.message.reply_text("Please send a valid number.")

async def set_current_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set current balance."""
    chat_data = context.chat_data

    message_text = update.message.text.split(' ', 1)
    if len(message_text) == 2:
        try:
            balance = float(message_text[1])
            chat_data['balance'] = balance
            await update.message.reply_text(f"Current balance set to {balance}.")
        except ValueError:
            await update.message.reply_text("Please send a valid number.")
    else:
        await update.message.reply_text("Usage: /set_current_balance <amount>")

async def get_current_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current balance."""
    chat_data = context.chat_data

    balance = chat_data.get('balance', 0.0)
    await update.message.reply_text(f"Current balance is {balance}.")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("set_current_balance", set_current_balance))
app.add_handler(CommandHandler("get_current_balance", get_current_balance))

# on non command i.e message - echo the message on Telegram
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count))

if WEB_HOOK_HOST == '':
    app.run_polling(allowed_updates=Update.ALL_TYPES)
else:
    WEB_HOOK_PATH = f'{WEB_HOOK_HOST}/{TELEGRAM_BOT_KEY}'
    app.run_webhook(port=5000, listen="0.0.0.0", webhook_url=WEB_HOOK_PATH)
