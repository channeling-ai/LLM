import logging
import requests
import traceback
from datetime import datetime


_FIELD_LIMIT = 1000   # Discord embed field value 최대 1024자에서 여유 두기
_TRACEBACK_LIMIT = 3000  # Discord embed description 최대 4096자에서 여유 두기


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...(생략됨)"


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url: str):
        super().__init__(level=logging.ERROR)
        self.webhook_url = webhook_url

    def emit(self, record: logging.LogRecord):
        try:
            tb_text = ""
            if record.exc_info:
                tb_text = "".join(traceback.format_exception(*record.exc_info))

            # 엔드포인트 정보 (exception handler에서 extra로 전달)
            endpoint = getattr(record, "endpoint", None)
            fields = [
                {"name": "Logger", "value": f"`{record.name}:{record.lineno}`", "inline": True},
                {"name": "Level",  "value": f"`{record.levelname}`",            "inline": True},
            ]
            if endpoint:
                fields.append({"name": "Endpoint", "value": f"`{endpoint}`", "inline": False})

            fields.append({
                "name": "Message",
                "value": _truncate(record.getMessage(), _FIELD_LIMIT),
                "inline": False,
            })

            if tb_text:
                fields.append({
                    "name": "Traceback",
                    "value": f"```python\n{_truncate(tb_text, _TRACEBACK_LIMIT)}\n```",
                    "inline": False,
                })

            payload = {
                "embeds": [{
                    "title": "🚨 FastAPI ERROR",
                    "color": 0xE74C3C,
                    "fields": fields,
                    "timestamp": datetime.utcnow().isoformat(),
                }]
            }

            requests.post(self.webhook_url, json=payload, timeout=3)
        except Exception:
            traceback.print_exc()


class DiscordFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record)
