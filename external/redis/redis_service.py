import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self, host="localhost", port=6379, db=0, channel="complete"):
        self.redis = aioredis.Redis(host=host, port=port, db=db)
        self.channel = channel

    async def publish(self, user_id: str, message: str):
        try:
            payload = json.dumps({"userId": user_id, "message": message})
            await self.redis.publish(self.channel, payload)
            logger.info(f"📤 Redis Publish: {payload}")
        except Exception as e:
            logger.error(f"Redis Publish 실패: {e!r}")
