import asyncio
import json
import logging
import time

from domain.channel.repository.channel_repository import ChannelRepository
from domain.idea.dto.idea_dto import IdeaRequest
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.repository.report_repository import ReportRepository
from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service_impl import RagServiceImpl
from external.youtube.transcript_service import TranscriptService

logger = logging.getLogger(__name__)

class IdeaService:
    def __init__(self):
        self.idea_repository = IdeaRepository()
        self.rag_service = RagServiceImpl()
        self.report_repository = ReportRepository()
        self.video_repository = VideoRepository()
        self.transcript_service = TranscriptService()
        self.channel_repository = ChannelRepository()


    """
    아이디어 생성 요청 : 최근 3개 비디오 요약본 및 채널 정보 활용
    """
    async def create_idea(self, req: IdeaRequest):
        start_time = time.time()
        logger.info(f"💡 아이디어 생성 시작 - Channel ID: {req.channel_id}")
        
        try:
            channel = await self.channel_repository.find_by_id(req.channel_id)
            videos = await self.video_repository.find_by_channel_id(req.channel_id, 3)
            summary = ", ".join([video.title if video.title else "" for video in videos])

            # 아이디어 분석 요청
            idea_results = await self.rag_service.analyze_idea(req, channel, summary)

            # 아이디어 분석 결과를 Report에 저장
            db_start = time.time()
            ideas = []
            for idea_result in idea_results:
                idea = {
                    "channel_id": channel.id,
                    "title": idea_result.get("title"),
                    "content": idea_result.get("description"),
                    "hash_tag": json.dumps(idea_result.get("tags"), ensure_ascii=False),
                    "is_book_marked": False,
                }
                ideas.append(idea)

            ideas = await self.idea_repository.save_bulk(ideas)
            db_time = time.time() - db_start
            logger.info(f"🗄️ 아이디어 DB 저장 완료 ({db_time:.2f}초) - {len(ideas)}개 아이디어")
            
            total_time = time.time() - start_time
            logger.info(f"💡 아이디어 생성 전체 완료 ({total_time:.2f}초)")

            return ideas
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"💡 아이디어 생성 실패 ({total_time:.2f}초): {e!r}")
            raise e

    async def wait_for_summary(self, report_id: int, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            report = await report_repository.find_by_id(report_id)
            if report.summary:
                return report.summary

            logger.info(f"아이디어 요약본 확인 시도 {attempt + 1}: {report.summary}")
            await asyncio.sleep(1)

        return None