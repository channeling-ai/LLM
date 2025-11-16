import logging

from fastapi import FastAPI

from core.config.database_config import test_pg_connection
from core.cache.redis_client import get_redis_client, RedisClient
from core.kafka.kafka_broker import kafka_broker
from domain.idea.controller.idea_controller import router as idea_router
from domain.report.controller.report_controller import router as report_router
from domain.trend_keyword.controller.trend_keyword_controller import router as trend_router

from response.api_response import ApiResponse
from response.code.status.success_status import SuccessStatus

'''
서버 시작 명령어: fastapi dev main.py
'''

app = FastAPI(title="Channeling LLM API", version="1.0.0")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 라우터 등록
app.include_router(report_router)
app.include_router(idea_router)
app.include_router(trend_router)

@app.on_event("startup")
async def on_startup():
    print("🚀 서버 시작 중...")

    # DB 연결 테스트
    if await test_pg_connection():
        print("✅ PostgreSQL DB에 연결 완료")
    else:
        print("❌ PostgreSQL DB 연결 실패")

    # Redis 연결 테스트
    redis_client = await get_redis_client()
    if redis_client:
        print("✅ Redis 캐시 연결 완료")
    else:
        print("⚠️  Redis 캐시 없이 실행 (캐싱 비활성화)")

    # kafka 브로커 시작
    await kafka_broker.start()
    print("✅ Kafka 브로커 시작 완료")

@app.on_event("shutdown")
async def on_shutdown():

    print("🛑 서버 종료 중...")

    # Redis 연결 종료
    await RedisClient.close()
    print("✅ Redis 연결 종료 완료")

    # kafka 브로커 종료
    await kafka_broker.close()
    print("✅ Kafka 브로커 종료 완료")

@app.get("/health")
async def health_check():
    """Docker 헬스체크용 엔드포인트"""
    return ApiResponse.on_success(SuccessStatus._OK, {"status": "UP"})


