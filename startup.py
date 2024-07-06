import logging
import os
import sys


logger = logging.getLogger("uvicorn.error")


def check_env_variables() -> None:
    required_vars = ["TELEGRAM_BOT_KEY", "TELEGRAM_CHAT_ID", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.critical(
            "Error: Missing environment variables: %s", ", ".join(missing_vars)
        )
        sys.exit(1)
