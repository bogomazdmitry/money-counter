# Money counter bot

Bot for storing balance for some balances to manage your money periodically and more manually.

You can add bot to any chat or send direct messages. Editing messages doesn't work for now.

Bot: [@MoneyCounterHelperBot](https://t.me/MoneyCounterHelperBot)

My workflow with money:
1. Every month reset all balances.
2. I have some balance types: budget_foods_week_1, budget_foods_week_2, ...3, ...4, cat, ...
3. When I buy something, I send message to chat.
4. Check in the end my result, manual analyzing.


Example:

```
/get_all_balance_info
Balance info:
balance1: 16.0/16.0
balance2: 14.0/19.0

Total: 35.0 / 35.0
```

```
/upsert_balance 1 balance1
Balance for balance1 set to 1.0.
```

```
/change_limit 1 balance1
Limit for balance1 changed to 1.0.
```

```
/delete_balance balance1
Balance for balance1 deleted.
```

```
/reset_limits
Old balances:
balance1: 15.0/16.0
balance2: 19.0/19.0

Total: 34.0 / 35.0

Balances reset.
```

```
/set_custom_json_balance {"balance1": {"limit": 100, "balance": 50}}
Custom JSON balance set successfully.
```

```
1 balance1 feeding cat
Spent 1.0 for type balance1. Current balance is 15.0.
```

## Install

Python 3.13.1

```
pip install -r requirements.txt
pre-commit install
```

## Deploy

1. Typical render web server
2. Setup TELEGRAM_BOT_KEY and WEB_HOOK_HOST env variables
2. GET request to `https://api.telegram.org/bot{TELEGRAM_BOT_KEY}/setWebhook?url={WEB_HOOK_HOST}` (it is automatic process now)

## Bot commands info for BotFather

/set_commands

start - Welcome message and basic information.
help - Show this help message.
get_all_balance_info - Get full info about balance.
upsert_balance - <limit> <type> Set the current balance to the specified limit.
delete_balance - <type> Delete balance with type.
change_limit - <limit> <type> Change limit for balance.
reset_limits - Reset all balances.
set_custom_json_balance - <json> Set custom json balance.
