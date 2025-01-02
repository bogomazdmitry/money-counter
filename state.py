import json
import logging
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# Function to get data from pinned messages
async def _get_data_from_pinned_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> float:
    logger.debug(f"Fetching pinned messages for chat_id: {chat_id}")
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    if pinned_message and "Data for money-counter" in pinned_message.text:
        logger.debug(f"Pinned message found with expected text.")
        try:
            data_json = pinned_message.text.split('\n', 1)[1]
            data = json.loads(data_json)
            logger.debug(f"Successfully parsed data from pinned message.")
            return data
        except (IndexError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing pinned message: {e}")
    else:
        logger.debug(f"No relevant pinned message found.")
    return None

# Function to update pinned message with data
async def _update_data_from_pinned_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: object):
    logger.debug(f"Updating pinned message for chat_id: {chat_id}")
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    message_text = f"Data for money-counter\n{json.dumps(data)}"

    if pinned_message and "Data for money-counter" in pinned_message.text:
        logger.debug(f"Editing existing pinned message.")
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=pinned_message.message_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Pinned message updated successfully.")
        except Exception as e:
            logger.error(f"Failed to edit pinned message: {e}")
            raise
    else:
        logger.debug(f"No existing pinned message found. Sending a new one.")
        try:
            sent_message = await context.bot.send_message(chat_id, message_text, parse_mode=ParseMode.HTML)
            await context.bot.pin_chat_message(chat_id, sent_message.message_id)
            logger.info(f"New pinned message sent and pinned successfully.")
        except Exception as e:
            logger.error(f"Failed to send or pin message: {e}")
            raise

# Function to get current balance from pinned message per type
async def get_balance_info_by_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str) -> float:
    logger.debug(f"Getting balance info for type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning(f"No data found in pinned messages.")
        return None
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return None
    balance = data[type]
    logger.info(f"Retrieved balance for type '{type}': {balance}")
    return balance

# Function to get full info about balance from pinned message
async def get_balance_info(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> object:
    logger.debug(f"Getting full balance info for chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data:
        logger.info(f"Retrieved full balance info.")
    else:
        logger.warning(f"No balance info found.")
    return data

# Function to upsert balance type info with some limit
async def upsert_balance_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: float):
    logger.debug(f"Upserting balance type '{type}' with limit {limit} in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        data = {}
        logger.debug(f"No existing data. Initializing new data dictionary.")
    if type in data and data[type]['limit'] == limit and data[type]['balance'] == limit:
        logger.info(f"Balance wasn't updated with '{type}': no changes.")
        return
    data[type] = {'limit': limit, 'balance': limit}
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Balance type '{type}' upserted with limit {limit}.")

# Function to change limit for type. Returns True if limit was changed, False otherwise
async def change_limit_for_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: float) -> bool:
    logger.debug(f"Changing limit for type '{type}' to {limit} in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning(f"No data found to change limit.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    data[type]['limit'] = limit
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Limit for type '{type}' changed to {limit}.")
    return True

# Function to change balance for type. Returns new balance if changed, None otherwise
async def spend_balance_for_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, spent_balance: float) -> float:
    logger.debug(f"Spending {spent_balance} from type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning(f"No data found to spend balance.")
        return None
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return None
    new_balance = data[type]['balance'] - spent_balance
    if new_balance < 0:
        logger.warning(f"Insufficient balance for type '{type}'. Cannot spend {spent_balance}.")
        return None
    data[type]['balance'] = new_balance
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"New balance for type '{type}': {new_balance}")
    return new_balance

# Function to delete balance type. Returns True if balance was deleted, False otherwise
async def delete_balance_type(context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str) -> bool:
    logger.debug(f"Deleting balance type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning(f"No data found to delete.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    del data[type]
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Balance type '{type}' deleted successfully.")
    return True

# Function to reset all balances. Return old and new data
async def reset_limits_for_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> object:
    logger.debug(f"Resetting all balances in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning(f"No data found to reset.")
        return None
    old_data = data.copy()
    have_changes = False
    for type in data:
        if data[type]['balance'] != data[type]['limit']:
            have_changes = True
            logger.debug(f"Resetting balance for type '{type}' from {data[type]['balance']} to {data[type]['limit']}.")
        data[type]['balance'] = data[type]['limit']
    if have_changes:
        await _update_data_from_pinned_messages(context, chat_id, data)
        logger.info(f"All balances reset successfully.")
        return {'old': old_data, 'new': data}
    else:
        logger.info(f"No balances needed resetting.")
        return {'error': 'No changes.'}
