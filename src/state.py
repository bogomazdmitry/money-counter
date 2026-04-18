import json
import logging
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from decimal import Decimal

logger = logging.getLogger(__name__)

DATA_KEY = "balances"
MSG_ID_KEY = "data_message_id"


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    return value


def _normalize_data_to_decimals(data: object) -> object:
    if not isinstance(data, dict):
        return data
    for type_key, info in list(data.items()):
        if isinstance(info, dict):
            if "limit" in info:
                info["limit"] = _to_decimal(info["limit"])
            if "balance" in info:
                info["balance"] = _to_decimal(info["balance"])
    return data


def _get_chat_data(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict:
    """Get balances from chat_data (PicklePersistence)."""
    chat_data = context.application.chat_data.get(chat_id, {})
    data = chat_data.get(DATA_KEY)
    if data is not None:
        return _normalize_data_to_decimals(data)
    return None


def _set_chat_data(context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: dict):
    """Save balances to chat_data (PicklePersistence)."""
    if chat_id not in context.application.chat_data:
        context.application.chat_data[chat_id] = {}
    context.application.chat_data[chat_id][DATA_KEY] = data


def _get_message_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Get stored message_id for the data message."""
    chat_data = context.application.chat_data.get(chat_id, {})
    return chat_data.get(MSG_ID_KEY)


def _set_message_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Save message_id for the data message."""
    if chat_id not in context.application.chat_data:
        context.application.chat_data[chat_id] = {}
    context.application.chat_data[chat_id][MSG_ID_KEY] = message_id


async def _migrate_from_pinned(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> dict:
    """One-time migration: read data from pinned message into chat_data."""
    logger.info(f"Attempting migration from pinned message for chat_id: {chat_id}")
    try:
        chat = await context.bot.get_chat(chat_id)
        pinned_message = chat.pinned_message
        if pinned_message and pinned_message.text and "Data for money-counter" in pinned_message.text:
            data_json = pinned_message.text.split("\n", 1)[1]
            data = json.loads(data_json, parse_float=Decimal, parse_int=Decimal)
            data = _normalize_data_to_decimals(data)
            _set_chat_data(context, chat_id, data)
            _set_message_id(context, chat_id, pinned_message.message_id)
            logger.info(f"Migrated data from pinned message in chat {chat_id}")
            return data
    except Exception as e:
        logger.error(f"Migration from pinned message failed: {e}")
    return None


async def _get_data(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict:
    """Get data: chat_data first, fallback to pinned message migration."""
    data = _get_chat_data(context, chat_id)
    if data is not None:
        return data
    return await _migrate_from_pinned(context, chat_id)


async def _update_data(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: dict
):
    """Save data to chat_data and update mirror message (best-effort)."""
    _set_chat_data(context, chat_id, data)

    message_text = f"Data for money-counter\n{json.dumps(data, default=str)}"
    message_id = _get_message_id(context, chat_id)

    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message_text,
                parse_mode=ParseMode.HTML,
            )
            logger.debug("Mirror message updated.")
            return
        except Exception as e:
            logger.warning(f"Failed to edit mirror message {message_id}: {e}")

    try:
        sent_message = await context.bot.send_message(
            chat_id, message_text, parse_mode=ParseMode.HTML
        )
        _set_message_id(context, chat_id, sent_message.message_id)
        try:
            await context.bot.pin_chat_message(chat_id, sent_message.message_id)
        except Exception as e:
            logger.warning(f"Failed to pin message: {e}")
        logger.info("New mirror message sent.")
    except Exception as e:
        logger.warning(f"Failed to send mirror message: {e}")


# Function to get current balance from pinned message per type
async def get_balance_info_by_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str
) -> object:
    logger.debug(f"Getting balance info for type '{type}' in chat_id: {chat_id}")
    data = await _get_data(context, chat_id)
    if data is None:
        logger.warning("No data found.")
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
    data = await _get_data(context, chat_id)
    if data:
        logger.info("Retrieved full balance info.")
    else:
        logger.warning("No balance info found.")
    return data


# Function to upsert balance type info with some limit
async def upsert_balance_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: Decimal
):
    logger.debug(
        f"Upserting balance type '{type}' with limit {limit} in chat_id: {chat_id}"
    )
    data = await _get_data(context, chat_id)
    if data is None:
        data = {}
        logger.debug("No existing data. Initializing new data dictionary.")
    if type in data and data[type]["limit"] == limit and data[type]["balance"] == limit:
        logger.info(f"Balance wasn't updated with '{type}': no changes.")
        return
    data[type] = {"limit": limit, "balance": limit}
    await _update_data(context, chat_id, data)
    logger.info(f"Balance type '{type}' upserted with limit {limit}.")


# Function to change limit for type. Returns True if limit was changed, False otherwise
async def change_limit_for_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: Decimal
) -> bool:
    logger.debug(f"Changing limit for type '{type}' to {limit} in chat_id: {chat_id}")
    data = await _get_data(context, chat_id)
    if data is None:
        logger.warning("No data found to change limit.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    data[type]["balance"] = data[type]["balance"] - (limit - data[type]["limit"])
    data[type]["limit"] = limit
    await _update_data(context, chat_id, data)
    logger.info(f"Limit for type '{type}' changed to {limit}.")
    return True


# Function to change balance for type. Returns new balance if changed, None otherwise
async def spend_balance_for_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, spent_balance: Decimal
) -> object:
    logger.debug(f"Spending {spent_balance} from type '{type}' in chat_id: {chat_id}")
    data = await _get_data(context, chat_id)
    if data is None:
        logger.warning("No data found to spend balance.")
        return None
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return None
    if spent_balance == 0:
        logger.info(f"Balance '{type}' didn't change")
        return data[type]["balance"] - spent_balance

    new_balance = data[type]["balance"] - spent_balance
    data[type]["balance"] = new_balance
    await _update_data(context, chat_id, data)
    logger.info(f"New balance for type '{type}': {new_balance}")
    return new_balance


# Function to delete balance type. Returns True if balance was deleted, False otherwise
async def delete_balance_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str
) -> bool:
    logger.debug(f"Deleting balance type '{type}' in chat_id: {chat_id}")
    data = await _get_data(context, chat_id)
    if data is None:
        logger.warning("No data found to delete.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    del data[type]
    await _update_data(context, chat_id, data)
    logger.info(f"Balance type '{type}' deleted successfully.")
    return True


# Function to reset all balances. Return old and new data
async def reset_limits_for_chat(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> object:
    logger.debug(f"Resetting all balances in chat_id: {chat_id}")
    data = await _get_data(context, chat_id)
    if data is None:
        logger.warning("No data found to reset.")
        return None
    old_data = data.copy()
    have_changes = False
    for type in data:
        if "balance" not in data[type] or "limit" not in data[type]:
            continue
        if data[type]["balance"] != data[type]["limit"]:
            have_changes = True
            logger.debug(
                f"Resetting balance for type '{type}' from {data[type]['balance']} to {data[type]['limit']}."
            )
        data[type]["balance"] = data[type]["limit"]
    if have_changes:
        await _update_data(context, chat_id, data)
        logger.info("All balances reset successfully.")
        return {"old": old_data, "new": data}
    else:
        logger.info("No balances needed resetting.")
        return {"error": "No changes."}


# Function for custom setting json as balances
async def set_custom_json_balance(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: object
):
    logger.debug(f"Setting custom json balance in chat_id: {chat_id}")
    data = _normalize_data_to_decimals(data)
    await _update_data(context, chat_id, data)
    logger.info("Custom json balance set successfully.")
