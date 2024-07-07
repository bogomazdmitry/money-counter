import json
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Function to get current balance from pinned message
async def get_balance(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> float:
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    if pinned_message and "Data for money-counter" in pinned_message.text:
        try:
            data = json.loads(pinned_message.text.split('\n', 1)[1])
            return data.get('balance', 0.0)
        except (IndexError, ValueError, json.JSONDecodeError):
            pass
    return 0.0

# Function to update pinned message with current balance
async def update_balance(context: ContextTypes.DEFAULT_TYPE, chat_id: int, balance: float):
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    data = {'balance': balance}
    message_text = f"Data for money-counter\n{json.dumps(data)}"

    if pinned_message and "Data for money-counter" in pinned_message.text:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=pinned_message.message_id, text=message_text, parse_mode=ParseMode.HTML)
    else:
        sent_message = await context.bot.send_message(chat_id, message_text, parse_mode=ParseMode.HTML)
        await context.bot.pin_chat_message(chat_id, sent_message.message_id)
