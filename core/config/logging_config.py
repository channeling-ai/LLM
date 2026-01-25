import json
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


class CustomJsonFormatter(logging.Formatter):
    """로그 JSON 포매터"""
    def format(self, record):
        log_dict = {
            '@timestamp': datetime.fromtimestamp(record.created, KST).isoformat(timespec='microseconds'),
            'message': record.getMessage(),
            'logger_name': record.name,
            'thread_name': record.threadName,
            'level': record.levelname
        }
        return json.dumps(log_dict, ensure_ascii=False, separators=(',', ':'))


class ColorFormatter(logging.Formatter):
    """로컬용 색상 포매터"""
    COLORS = {
        'DEBUG': '\033[36m',    # cyan
        'INFO': '\033[32m',     # green
        'WARNING': '\033[33m',  # yellow
        'ERROR': '\033[31m',    # red
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """환경에 따른 로깅 설정 (ENV=prod → JSON, 그 외 → 색상)"""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if os.getenv("ENV") == "prod":
        formatter = CustomJsonFormatter()
    else:
        formatter = ColorFormatter(
            fmt='%(asctime)s [%(name)s] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # uvicorn 로거도 동일 포맷 적용
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.addHandler(handler)
        uvicorn_logger.propagate = False
