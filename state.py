import json
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Function to get data from pinned messages
async def _get_data_from_pinned_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> float:
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    if pinned_message and "Data for money-counter" in pinned_message.text:
        try:
            return json.loads(pinned_message.text.split('\n', 1)[1])
        except (IndexError, ValueError, json.JSONDecodeError):
            pass
    return None

# Function to update pinned message with data
async def _update_data_from_pinned_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: object):
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    message_text = f"Data for money-counter\n{json.dumps(data)}"

    if pinned_message and "Data for money-counter" in pinned_message.text:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=pinned_message.message_id, text=message_text, parse_mode=ParseMode.HTML)
    else:
        sent_message = await context.bot.send_message(chat_id, message_text, parse_mode=ParseMode.HTML)
        await context.bot.pin_chat_message(chat_id, sent_message.message_id)

# Function to get current balance from pinned message per type
async def get_balance_info_by_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str) -> float:
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        return None
    if type not in data:
        return None
    return data[type]

# Function to get full info about balance from pinned message
async def get_balance_info(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> object:
    return await _get_data_from_pinned_messages(context, chat_id)

# Function to upsert balance type info with some limit
async def upsert_balance_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: float):
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        data = {}
    data[type] = {'limit': limit, 'balance': limit}
    await  _update_data_from_pinned_messages(context, chat_id, data)

# Function to change limit for type. Returns True if limit was changed, False otherwise
async def change_limit_for_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: float) -> bool:
    data = await  _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        return False
    if type not in data:
        return False
    data[type]['limit'] = limit
    await _update_data_from_pinned_messages(context, chat_id, data)
    return True

# Function to change balance for type. Returns True if balance was changed, False otherwise
async def spend_balance_for_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, spent_balance: float) -> float:
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        return None
    if type not in data:
        return None
    new_balance = data[type]['balance'] - spent_balance
    data[type]['balance'] = new_balance
    await _update_data_from_pinned_messages(context, chat_id, data)
    return new_balance


# Function to reset all balances. Return old and new data
async def reset_limits_for_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> object:
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        return None
    old_data = data.copy()
    have_changes = False
    for type in data:
        if data[type]['balance'] != data[type]['limit']:
            have_changes = True
        data[type]['balance'] = data[type]['limit']
    if have_changes:
        await _update_data_from_pinned_messages(context, chat_id, data)
        return {'old': old_data, 'new': data}
    else:
        return {'error': 'No changes.'}