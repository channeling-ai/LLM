import logging
import os

from external.log.discord_handler import (
    DiscordWebhookHandler,
    DiscordFormatter,
)


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    discord_handler = DiscordWebhookHandler(webhook_url)
    discord_handler.setLevel(logging.ERROR)

    formatter = DiscordFormatter(
        "[%(asctime)s] %(levelname)s "
        "%(name)s:%(lineno)d\n%(message)s"
    )
    discord_handler.setFormatter(formatter)

    root_logger.addHandler(discord_handler)
