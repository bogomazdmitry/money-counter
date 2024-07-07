# Money counter bot

Bot for storing balance and count current balance

Example:

```
/set_current_balance 1
Current balance set to 1.0.
```

```
/get_current_balance
Current balance is 1.0.
```

```
1 feeding cat
Counted 1.0. Current balance is 0.0.
```

## Deploy

1. Typical render web server
2. Setup TELEGRAM_BOT_KEY and WEB_HOOK_HOST env variables
2. GET request to `https://api.telegram.org/bot{TELEGRAM_BOT_KEY}/setWebhook?url={WEB_HOOK_HOST}` (it is automatic process now)