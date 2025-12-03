import json
import logging
import asyncio


from core.cache.redis_client import RedisClient
from domain.report.service.report_service import ReportService
from domain.task.model.task import Status
from domain.task.repository.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class ReportUpdateSubscriber:
    def __init__(self):
        self.report_service = ReportService()
        self.task_repository = TaskRepository()
        self.redis_channel_name = "complete"  # redis_client - redis_service 에서 publish 하는 채널명

    async def start(self):
        """Redis Subscriber 시작"""
        redis = await RedisClient.get_instance()
        pubsub = redis.pubsub()

        # 채널 구독
        await pubsub.subscribe(self.redis_channel_name)
        logger.info(f"🎧 Redis Subscriber 시작 - 채널: {self.redis_channel_name}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.handle_message(redis, message["data"])
        except Exception as e:
            logger.error(f"Subscriber 에러 발생: {e}")
        finally:
            await pubsub.unsubscribe(self.redis_channel_name)
            await pubsub.close()
            # 주의: RedisClient.close()는 싱글톤이므로 여기서 닫으면 다른데서 문제될 수 있음 -> 워커 프로세스가 종료될 때

    async def handle_message(self, redis, raw_data):
        """메시지 처리 및 상태 동기화 로직"""
        try:
            # 1. 메시지 파싱 {"userId": ..., "message": "..."}
            data_json = json.loads(raw_data)
            logging.info(f"data_json: {data_json}")
            inner_message = data_json.get("message")
            logging.info(f"inner_message: {inner_message}")


            if not inner_message:
                return

            # 내부 메시지 파싱: {"status": "success", "step": "...", "report_id": ...}
            payload = json.loads(inner_message)
            logging.info(f"payload: {payload}")

            status = payload.get("status")
            step = payload.get("step")
            report_id = payload.get("report")

            # 필요한 정보가 없거나 실패한 작업이면 무시
            if not report_id or status != "success" or step not in ["overview", "analysis"]:
                logging.info(f"⚠️ subscriber 무시된 메시지: {raw_data}")
                return

            logger.info(f"📥 작업 완료 수신: Report {report_id} - {step}")

            # 2. 두 작업이 모두 완료되었는지 확인
            task = await self.task_repository.find_by_report(report_id)

            if task.overview_status == Status.COMPLETED and task.analysis_status == Status.COMPLETED:
                logger.info(f"✅ 모든 작업 완료됨 (Report {report_id}). 업데이트 요약 생성 시작...")

                # 업데이트 요약 생성 서비스 호출
                success = await self.report_service.summarize_update_changes(report_id)

                if success:
                    logger.info(f"🎉 업데이트 요약 생성 완료 (Report {report_id})")
                else:
                    logger.error(f"❌ 업데이트 요약 생성 실패 (Report {report_id})")

        except json.JSONDecodeError:
            logger.warning(f"잘못된 JSON 형식: {raw_data}")
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")

async def main():
    subscriber = ReportUpdateSubscriber()
    await subscriber.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Redis Subscriber 중단")