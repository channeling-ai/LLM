import logging
import requests
import traceback


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url: str):
        super().__init__(level=logging.ERROR)
        self.webhook_url = webhook_url

    def emit(self, record: logging.LogRecord):
        try:
            message = self.format(record)

            payload = {
                "content": f"🚨 **FastAPI ERROR** 🚨\n```{message}```"
            }

            requests.post(
                self.webhook_url,
                json=payload,
                timeout=3
            )
        except Exception:
            # 로깅 실패로 서버 죽으면 안 됨
            pass


class DiscordFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base_message = super().format(record)

        if record.exc_info:
            base_message += "\n" + "".join(
                traceback.format_exception(*record.exc_info)
            )

        return base_message
