import json
import logging
import os
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from decimal import Decimal

logger = logging.getLogger(__name__)

CACHE_DIR = os.environ.get("BOT_CACHE_DIR", "/app/data")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(chat_id: int) -> str:
    return os.path.join(CACHE_DIR, f"{chat_id}.json")


def _load_cache(chat_id: int) -> dict | None:
    path = _cache_path(chat_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            raw = json.load(f)
        return {
            "message_id": raw.get("message_id"),
            "data": _normalize_data_to_decimals(raw.get("data", {})),
        }
    except Exception as e:
        logger.error(f"Failed to load cache for {chat_id}: {e}")
        return None


def _save_cache(chat_id: int, message_id: int, data: dict):
    path = _cache_path(chat_id)
    try:
        with open(path, "w") as f:
            json.dump({"message_id": message_id, "data": data}, f, default=str)
    except Exception as e:
        logger.error(f"Failed to save cache for {chat_id}: {e}")


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


# Function to get data from the bot's data message
async def _get_data_from_pinned_messages(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> object:
    logger.debug(f"Fetching data message for chat_id: {chat_id}")

    # Try file cache first (survives restarts and pinned message changes)
    cached = _load_cache(chat_id)
    if cached and cached["data"]:
        logger.debug("Returning data from file cache.")
        return cached["data"]

    # Fallback: try pinned message
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    if pinned_message and pinned_message.text and "Data for money-counter" in pinned_message.text:
        logger.debug("Pinned message found with expected text.")
        try:
            data_json = pinned_message.text.split("\n", 1)[1]
            data = json.loads(data_json, parse_float=Decimal, parse_int=Decimal)
            data = _normalize_data_to_decimals(data)
            _save_cache(chat_id, pinned_message.message_id, data)
            logger.debug("Successfully parsed and cached data from pinned message.")
            return data
        except (IndexError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing pinned message: {e}")
    else:
        logger.debug("No relevant pinned message found.")
    return None


# Function to update data message (uses cached message_id, no get_chat needed)
async def _update_data_from_pinned_messages(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, data: object
):
    logger.debug(f"Updating data message for chat_id: {chat_id}")
    message_text = f"Data for money-counter\n{json.dumps(data, default=str)}"

    # Use cached message_id to edit directly (works even if another msg is pinned)
    cached = _load_cache(chat_id)
    if cached and cached.get("message_id"):
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=cached["message_id"],
                text=message_text,
                parse_mode=ParseMode.HTML,
            )
            _save_cache(chat_id, cached["message_id"], data)
            logger.info("Data message updated via cached message_id.")
            return
        except Exception as e:
            logger.warning(f"Failed to edit via cached message_id: {e}")

    # Fallback: check pinned message
    chat = await context.bot.get_chat(chat_id)
    pinned_message = chat.pinned_message
    if pinned_message and pinned_message.text and "Data for money-counter" in pinned_message.text:
        logger.debug("Editing existing pinned message.")
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=pinned_message.message_id,
                text=message_text,
                parse_mode=ParseMode.HTML,
            )
            _save_cache(chat_id, pinned_message.message_id, data)
            logger.info("Pinned message updated successfully.")
        except Exception as e:
            logger.error(f"Failed to edit pinned message: {e}")
            raise
    else:
        logger.debug("No existing data message found. Sending a new one.")
        try:
            sent_message = await context.bot.send_message(
                chat_id, message_text, parse_mode=ParseMode.HTML
            )
            _save_cache(chat_id, sent_message.message_id, data)
            await context.bot.pin_chat_message(chat_id, sent_message.message_id)
            logger.info("New data message sent and pinned successfully.")
        except Exception as e:
            logger.error(f"Failed to send or pin message: {e}")
            raise


# Function to get current balance from pinned message per type
async def get_balance_info_by_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str
) -> object:
    logger.debug(f"Getting balance info for type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning("No data found in pinned messages.")
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
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        data = {}
        logger.debug("No existing data. Initializing new data dictionary.")
    if type in data and data[type]["limit"] == limit and data[type]["balance"] == limit:
        logger.info(f"Balance wasn't updated with '{type}': no changes.")
        return
    data[type] = {"limit": limit, "balance": limit}
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Balance type '{type}' upserted with limit {limit}.")


# Function to change limit for type. Returns True if limit was changed, False otherwise
async def change_limit_for_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, limit: Decimal
) -> bool:
    logger.debug(f"Changing limit for type '{type}' to {limit} in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning("No data found to change limit.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    data[type]["balance"] = data[type]["balance"] - (limit - data[type]["limit"])
    data[type]["limit"] = limit
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Limit for type '{type}' changed to {limit}.")
    return True


# Function to change balance for type. Returns new balance if changed, None otherwise
async def spend_balance_for_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str, spent_balance: Decimal
) -> object:
    logger.debug(f"Spending {spent_balance} from type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
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
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"New balance for type '{type}': {new_balance}")
    return new_balance


# Function to delete balance type. Returns True if balance was deleted, False otherwise
async def delete_balance_type(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, type: str
) -> bool:
    logger.debug(f"Deleting balance type '{type}' in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
    if data is None:
        logger.warning("No data found to delete.")
        return False
    if type not in data:
        logger.warning(f"Type '{type}' not found in data.")
        return False
    del data[type]
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info(f"Balance type '{type}' deleted successfully.")
    return True


# Function to reset all balances. Return old and new data
async def reset_limits_for_chat(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> object:
    logger.debug(f"Resetting all balances in chat_id: {chat_id}")
    data = await _get_data_from_pinned_messages(context, chat_id)
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
        await _update_data_from_pinned_messages(context, chat_id, data)
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
    await _update_data_from_pinned_messages(context, chat_id, data)
    logger.info("Custom json balance set successfully.")
