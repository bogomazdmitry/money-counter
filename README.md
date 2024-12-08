# Money counter bot

Bot for storing balance and count current balance

Bot: @MoneyCounterHelperBot

Example:

```
/get_all_balance_info
Balance info:
balance1: 16.0/16.0
balance2: 14.0/19.0
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
balance1: 16.0/16.0
balance2: 19.0/19.0

Balances reset.
```

```
1 balance1 feeding cat
Spent 1.0 for type balance1. Current balance is 15.0.
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
