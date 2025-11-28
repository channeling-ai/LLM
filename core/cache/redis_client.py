import os
import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class RedisClient:
    """Redis 클라이언트 싱글톤"""

    _instance: Optional[redis.Redis] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        """Redis 클라이언트 인스턴스 반환 (싱글톤)"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    redis_host = os.getenv("REDIS_HOST", "localhost")
                    redis_port = int(os.getenv("REDIS_PORT", "6379"))
                    redis_password = os.getenv("REDIS_PASSWORD", None)
                    redis_db = int(os.getenv("REDIS_DB", "0"))

                    try:
                        cls._instance = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            password=redis_password,
                            db=redis_db,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5,
                            retry_on_timeout=True,
                        )

                        # 연결 테스트
                        await cls._instance.ping()

                    except Exception as e:
                        cls._instance = None

        return cls._instance

    @classmethod
    async def close(cls):
        """Redis 연결 종료"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Redis 연결 종료")


# 전역 redis_client 헬퍼 함수
async def get_redis_client() -> Optional[redis.Redis]:
    """
    Redis 클라이언트를 반환합니다.
    Redis 연결 실패 시 None을 반환합니다 (캐싱 비활성화).
    """
    return await RedisClient.get_instance()

class RedisService:
    """Redis publish 전용 서비스"""

    def __init__(self, channel: str = "complete"):
        self.channel = channel
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> Optional[redis.Redis]:
        if not self._client:
            self._client = await RedisClient.get_instance()
        return self._client

    async def publish(self, user_id: str, message: str):
        """Redis 채널에 메시지 발행"""
        client = await self._get_client()
        if not client:
            logger.warning("Redis 연결 실패: 메시지를 발행할 수 없습니다.")
            return
        try:
            payload = json.dumps({"userId": user_id, "message": message})
            await client.publish(self.channel, payload)
            logger.info(f"📤 Redis Publish: {payload}")
        except Exception as e:
            logger.error(f"Redis Publish 실패: {e!r}")