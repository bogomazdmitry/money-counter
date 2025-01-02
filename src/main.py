import json
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import state
import tg_helper

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

load_dotenv()


# Check for necessary environment variables
def check_env_variables():
    if "TELEGRAM_BOT_KEY" not in os.environ:
        raise ValueError("TELEGRAM_BOT_KEY is not set in environment variables")


check_env_variables()

TELEGRAM_BOT_KEY = os.getenv("TELEGRAM_BOT_KEY")
WEB_HOOK_HOST = os.getenv("WEB_HOOK_HOST")
app = Application.builder().token(TELEGRAM_BOT_KEY).build()


# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    logger.info(f"/start command received from user {update.effective_user.id}")
    user = update.effective_user
    try:
        await tg_helper.reply_html(
            update, app, rf"Hi {user.mention_html()}! Welcome to the Balance Bot."
        )
        logger.debug(f"Sent welcome message to user {user.id}")
        await tg_helper.reply_text(
            update,
            app,
            "I can help you keep track of your balance in this chat. "
            "Use /help to see the available commands.",
        )
        logger.debug(f"Sent help prompt to user {user.id}")
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    logger.info(f"/help command received from user {update.effective_user.id}")
    help_text = (
        "Available commands:\n"
        "/start - Welcome message and basic information.\n"
        "/help - Show this help message.\n"
        "/get_all_balance_info - Get full info about balance.\n"
        "/upsert_balance <limit> <type> - Set the current balance to the specified limit.\n"
        "/change_limit <limit> <type> - Change limit for balance.\n"
        "/delete_balance <type> - Delete balance with type.\n"
        "/reset_limits - Reset all balances.\n"
        "/set_custom_json_balance <json> - Set custom json balance.\n"
        "Simply send a message with a number and type to count that amount and update the balance."
    )
    try:
        await tg_helper.reply_text(update, app, help_text)
        logger.debug(f"Sent help text to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in /help handler: {e}")


def print_to_string_balance_info(balance_info):
    all_limit = 0
    all_balance = 0
    result_string = ""
    for type, info in balance_info.items():
        if isinstance(info, dict) and "balance" in info and "limit" in info:
            result_string += f"{type}: {info['balance']} / {info['limit']}\n"
            all_limit += info["limit"]
            all_balance += info["balance"]
    result_string += f"\nTotal: {all_balance} / {all_limit}"
    return result_string


# Handler for /get_all_balance_info command
async def get_all_balance_info(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Get all balance info."""
    if update.message is None:
        logger.info(
            f"/get_all_balance_info command received in chat {update.effective_chat.id}, but update.message is None"
        )
        return
    logger.info(
        f"/get_all_balance_info command received from chat {update.effective_chat.id}"
    )
    chat_id = update.effective_chat.id
    try:
        balance_info = await state.get_balance_info(context, chat_id)
        if balance_info:
            result_string = (
                f"Balance info:\n{print_to_string_balance_info(balance_info)}"
            )
            await tg_helper.reply_text(update, app, result_string)
            logger.debug(f"Sent balance info to chat {chat_id}")
        else:
            await tg_helper.reply_text(update, app, "No balances found.")
            logger.debug(f"No balances found for chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in /get_all_balance_info handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while fetching balance information."
        )


# Handler for /upsert_balance command
async def upsert_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upsert balance."""
    if update.message is None:
        logger.info(
            f"/upsert_balance command received in chat {update.effective_chat.id}, but update.message is None"
        )
        return
    logger.info(f"/upsert_balance command received in chat {update.effective_chat.id}")
    chat_id = update.effective_chat.id
    args = update.message.text.strip().split()[1:]
    if len(args) != 2:
        await tg_helper.reply_text(
            update, app, "Please provide two arguments: <limit> <type>."
        )
        logger.warning(f"Invalid arguments for /upsert_balance: {args}")
        return
    limit, type = args
    try:
        limit = float(limit)
    except ValueError:
        await tg_helper.reply_text(update, app, "Limit must be a number.")
        logger.warning(f"Invalid limit value: {limit}")
        return
    try:
        await state.upsert_balance_type(context, chat_id, type, limit)
        await tg_helper.reply_text(update, app, f"Balance for '{type}' set to {limit}.")
        logger.info(f"Balance for '{type}' upserted to {limit} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in /upsert_balance handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while setting the balance."
        )


# Handler for /change_limit command
async def change_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change limit."""
    if update.message is None:
        logger.info(
            f"/change_limit command received in chat {update.effective_chat.id}, but update.message is None"
        )
        return
    logger.info(f"/change_limit command received in chat {update.effective_chat.id}")
    chat_id = update.effective_chat.id
    args = update.message.text.strip().split()[1:]
    if len(args) != 2:
        await tg_helper.reply_text(
            update, app, "Please provide two arguments: <new_limit> <type>."
        )
        logger.warning(f"Invalid arguments for /change_limit: {args}")
        return
    limit, type = args
    try:
        limit = float(limit)
    except ValueError:
        await tg_helper.reply_text(update, app, "Limit must be a number.")
        logger.warning(f"Invalid limit value: {limit}")
        return
    try:
        result = await state.change_limit_for_type(context, chat_id, type, limit)
        if result:
            await tg_helper.reply_text(
                update, app, f"Limit for '{type}' changed to {limit}."
            )
            logger.info(f"Limit for '{type}' changed to {limit} in chat {chat_id}")
        else:
            await tg_helper.reply_text(update, app, f"No balance found for '{type}'.")
            logger.warning(f"No balance found for type '{type}' in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in /change_limit handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while changing the limit."
        )


# Handler for /delete_balance command
async def delete_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete balance."""
    if update.message is None:
        logger.info(
            f"/delete_balance command received in chat {update.effective_chat.id}, but update.message is None"
        )
        return
    chat_id = update.effective_chat.id
    logger.info(f"/delete_balance command received in chat {update.effective_chat.id}")

    args = update.message.text.strip().split()[1:]
    if len(args) != 1:
        await tg_helper.reply_text(update, app, "Please provide one argument: <type>.")
        logger.warning(f"Invalid arguments for /delete_balance: {args}")
        return
    type = args[0]
    try:
        result = await state.delete_balance_type(context, chat_id, type)
        if result:
            await tg_helper.reply_text(update, app, f"Balance for '{type}' deleted.")
            logger.info(f"Balance for '{type}' deleted in chat {chat_id}")
        else:
            await tg_helper.reply_text(update, app, f"No balance found for '{type}'.")
            logger.warning(f"No balance found for type '{type}' in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in /delete_balance handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while deleting the balance."
        )


# Handler for /reset_limits command
async def reset_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset limits."""
    if update.message is None:
        logger.info(
            f"/reset_limits command received in chat {update.effective_chat.id}, but update.message is None"
        )
        return
    chat_id = update.effective_chat.id
    try:
        result = await state.reset_limits_for_chat(context, chat_id)
        if result:
            if "error" in result:
                result_string = result["error"]
                logger.info(f"Reset limits result: {result_string}")
            else:
                old_info = print_to_string_balance_info(result["old"])
                result_string = f"Old balances:\n{old_info}\nBalances have been reset to their limits."
                logger.info(f"Balances reset successfully in chat {chat_id}")
        else:
            result_string = "No balances found."
            logger.info(f"No balances to reset in chat {chat_id}")
        await tg_helper.reply_text(update, app, result_string)
    except Exception as e:
        logger.error(f"Error in /reset_limits handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while resetting the limits."
        )


# Handler for spending money via messages
async def spend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Spend money."""
    if update.message is None:
        logger.info(
            f"Spend command received in chat {update.effective_chat.id} with message: '{update.message.text.strip()}, but update.message is empty'"
        )
        return
    logger.info(
        f"Spend command received in chat {update.effective_chat.id} with message: '{update.message.text.strip()}'"
    )

    chat_id = update.effective_chat.id

    message_text = update.message.text.strip()
    try:
        parts = message_text.split()
        if len(parts) != 2:
            await tg_helper.reply_text(
                update,
                app,
                "Please send a message with a number and type, e.g., '50 groceries'.",
            )
            logger.warning(f"Invalid message format: '{message_text}'")
            return
        amount_str, type = parts
        amount = float(amount_str)
        logger.debug(f"Parsed amount: {amount}, type: '{type}'")
        new_balance = await state.spend_balance_for_type(context, chat_id, type, amount)
        if new_balance is None:
            await tg_helper.reply_text(
                update, app, f"No balance found for '{type}', or insufficient funds."
            )
            logger.warning(
                f"Failed to spend {amount} from type '{type}' in chat {chat_id}"
            )
        else:
            await tg_helper.reply_text(
                update,
                app,
                f"Spent {amount} for '{type}'. Current balance is {new_balance}.",
            )
            logger.info(
                f"Spent {amount} from type '{type}'. New balance: {new_balance}"
            )
    except ValueError:
        await tg_helper.reply_text(
            update,
            app,
            "Please send a valid number followed by the type, e.g., '50 groceries'.",
        )
        logger.warning(f"Invalid amount value in message: '{message_text}'")
    except Exception as e:
        logger.error(f"Error in spend handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while processing your request."
        )


async def set_custom_json_balance(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Set custom JSON balance."""
    if update.message is None:
        logger.info(
            f"/set_custom_json_balance command received in chat {update.effective_chat.id}, but update.message is empty"
        )
        return
    chat_id = update.effective_chat.id
    try:
        json_str = update.message.text
        json_str = json_str.replace("/set_custom_json_balance", "").strip()
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError:
            await tg_helper.reply_text(
                update,
                app,
                'Please send a valid JSON string followed by the type, e.g., \'{"groceries": {"limit": 100, "balance": 50}}\'.',
            )
            logger.warning(f"Invalid JSON string: '{json_str}'")
            return
        await state.set_custom_json_balance(context, chat_id, json_data)
        await tg_helper.reply_text(update, app, "Custom JSON balance set successfully.")
        logger.info(f"Custom JSON balance set in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in /set_custom_json_balance handler: {e}")
        await tg_helper.reply_text(
            update, app, "An error occurred while processing your request."
        )


# Register command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("get_all_balance_info", get_all_balance_info))
app.add_handler(CommandHandler("upsert_balance", upsert_balance))
app.add_handler(CommandHandler("change_limit", change_limit))
app.add_handler(CommandHandler("reset_limits", reset_limits))
app.add_handler(CommandHandler("delete_balance", delete_balance))
app.add_handler(CommandHandler("set_custom_json_balance", set_custom_json_balance))

# on non command i.e message - handle spending
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, spend))

# Run the bot
if WEB_HOOK_HOST:
    logger.info("Starting bot with webhook.")
    try:
        app.bot.set_webhook(WEB_HOOK_HOST, allowed_updates=Update.ALL_TYPES)
        app.run_webhook(port=5000, listen="0.0.0.0", webhook_url=WEB_HOOK_HOST)
        logger.info("Webhook is set and bot is running.")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
else:
    logger.info("Starting bot with long polling.")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is polling for updates.")
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")
