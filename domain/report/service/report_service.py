import asyncio
import json
import logging
import time
from typing import DefaultDict, List

from core.enums.source_type import SourceTypeEnum
from domain.channel.repository.channel_repository import ChannelRepository
from domain.comment.model.comment import Comment
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.log.repository.report_log_repository import ReportLogRepository
from domain.report.repository.report_repository import ReportRepository
from domain.trend_keyword.model.trend_keyword_type import TrendKeywordType
from domain.trend_keyword.repository.trend_keyword_repository import TrendKeywordRepository
from domain.video.model.video import Video
from external.rag import leave_analyize
from external.rag.rag_service_impl import RagServiceImpl

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        self.report_repository = ReportRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.trend_keyword_repository = TrendKeywordRepository()
        self.channel_repository = ChannelRepository()
        self.rag_service = RagServiceImpl()
        self.report_log_repository = ReportLogRepository()

    async def create_summary(self, video: Video, report_id: int, skip_vector_save: bool = False) -> bool:
        """
        영상 요약을 생성하고 Vector DB와 PostgreSQL에 저장
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            skip_vector_save: Vector DB 저장 스킵 여부 (기본값: False)
            
        Returns:
            성공 시 True, 실패 시 False
        """
        start_time = time.time()
        logger.info(f"📄 요약 생성 시작 - Report ID: {report_id}")
        
        try:
            # 유튜브 영상 아이디 조회
            youtube_video_id = getattr(video, "youtube_video_id", None)
            if not youtube_video_id:
                logger.error("YouTube 영상 ID가 없습니다.")
                return False
            
            # 요약 생성 (LLM API 호출, Redis 캐싱 적용)
            summary_start = time.time()
            summary = await self.rag_service.summarize_video(youtube_video_id)
            summary_time = time.time() - summary_start
            logger.info(f"🤖 LLM API 요약 생성 완료 ({summary_time:.2f}초)")
            logger.info("요약 결과:\n%s", summary[:100])
            
            # 벡터 DB에 저장 (skip_vector_save가 False인 경우만)
            if not skip_vector_save:
                await self.content_chunk_repository.save_context(
                    source_type=SourceTypeEnum.VIDEO_SUMMARY,
                    source_id=report_id,
                    context=summary
                )
                logger.info("요약 결과를 벡터 DB에 저장했습니다.")
            else:
                logger.info("[V2] 벡터 DB 저장을 스킵했습니다.")
            
            # PostgreSQL에 저장
            pg_start = time.time()
            await self.report_repository.save({
                "id": report_id,
                "summary": summary,
                "title": video.title
            })
            pg_time = time.time() - pg_start
            logger.info(f"🗄️ PostgreSQL DB 저장 완료 ({pg_time:.2f}초)")
            
            total_time = time.time() - start_time
            logger.info(f"📄 요약 생성 전체 완료 ({total_time:.2f}초)")
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"📄 요약 생성 실패 ({total_time:.2f}초): {e}")
            raise

    async def analyze_viewer_retention(self, video: Video, report_id: int, token: str, skip_vector_save: bool = False) -> bool:
        """
        시청자 이탈 분석 (재시도 로직 포함)
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            token: Google 액세스 토큰
            skip_vector_save: Vector DB 저장 스킵 여부 (기본값: False)
            
        Returns:
            성공 시 True, 실패 시 False
        """
        start_time = time.time()
        logger.info(f"📊 시청자 이탈 분석 시작 - Report ID: {report_id}")
        
        try:
            leave_result = None
            max_retries = 3
            retry_count = 0
            
            # 재시도 로직 (이탈 분석 API 호출)
            api_start = time.time()
            while retry_count < max_retries:
                try:
                    leave_result = await leave_analyize.analyze_leave(video, token)
                    api_time = time.time() - api_start
                    logger.info(f"📈 이탈 분석 API 호출 완료 ({api_time:.2f}초)")
                    break  # 성공하면 루프 종료
                    
                except (AttributeError, TypeError, KeyError):
                    # 즉시 실패해야 하는 에러들
                    raise
                    
                except Exception as e:
                    error_type = e.__class__.__name__
                    
                    # 네트워크 관련 에러인 경우 재시도
                    if error_type in ['ConnectTimeout', 'ReadTimeout', 'ConnectionError', 'TimeoutError']:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = retry_count * 5  # 지수 백오프
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # 최대 재시도 초과시 기본값 설정
                            leave_result = "시청자 이탈 분석 실패 (네트워크 타임아웃)"
                            break
                    else:
                        # 네트워크 에러가 아닌 경우 즉시 종료
                        raise
            
            # Vector DB에 저장 (skip_vector_save가 False인 경우만)
            if not skip_vector_save:
                await self.content_chunk_repository.save_context(
                    source_type=SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS,
                    source_id=report_id,
                    context=leave_result
                )
            else:
                logger.info("[V2] 벡터 DB 저장을 스킵했습니다.")
            
            # PostgreSQL에 저장
            await self.report_repository.save({
                "id": report_id,
                "leave_analyze": leave_result
            })
            
            return True
            
        except Exception as e:
            raise

    async def analyze_optimization(self, video: Video, report_id: int, skip_vector_save: bool = False) -> bool:
        """
        알고리즘 최적화 분석
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            skip_vector_save: Vector DB 저장 스킵 여부 (기본값: False)
            
        Returns:
            성공 시 True, 실패 시 False
        """
        start_time = time.time()
        logger.info(f"⚙️ 알고리즘 최적화 분석 시작 - Report ID: {report_id}")
        
        try:
            # 알고리즘 최적화 분석 (LLM API 호출)
            opt_start = time.time()
            analyze_opt = await self.rag_service.analyze_algorithm_optimization(video_id=video.youtube_video_id, skip_vector_save=skip_vector_save)
            opt_time = time.time() - opt_start
            logger.info(f"⚙️ 알고리즘 최적화 LLM 분석 완료 ({opt_time:.2f}초)")
            
            # Vector DB에 저장 (skip_vector_save가 False인 경우만)
            if not skip_vector_save:
                await self.content_chunk_repository.save_context(
                    source_type=SourceTypeEnum.ALGORITHM_OPTIMIZATION,
                    source_id=report_id,
                    context=analyze_opt
                )
            else:
                logger.info("[V2] 벡터 DB 저장을 스킵했습니다.")
            
            # PostgreSQL에 저장
            pg_start = time.time()
            await self.report_repository.save({
                "id": report_id,
                "optimization": analyze_opt
            })
            pg_time = time.time() - pg_start
            logger.info(f"🗄️ 알고리즘 최적화 분석 PostgreSQL DB 저장 완료 ({pg_time:.2f}초)")
            
            total_time = time.time() - start_time
            logger.info(f"⚙️ 알고리즘 최적화 분석 전체 완료 ({total_time:.2f}초)")
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"⚙️ 알고리즘 최적화 분석 실패 ({total_time:.2f}초): {e}")
            raise

    async def analyze_trends_and_save(self, video: Video, report_id: int, skip_vector_save: bool = False) -> bool:
        """
        트렌드 분석 및 키워드 저장
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            skip_vector_save: Vector DB 저장 스킵 여부 (기본값: False)
            
        Returns:
            성공 시 True, 실패 시 False
        """
        start_time = time.time()
        logger.info(f"📊 트렌드 분석 시작 - Report ID: {report_id}")
        
        try:
            # 1. 실시간 트렌드 분석
            realtime_keyword = self.rag_service.analyze_realtime_trends()
            
            # 2. 채널 정보 조회
            channel_id = getattr(video, "channel_id", None)
            if not channel_id:
                raise ValueError("video에 channel_id가 없습니다.")
                
            channel = await self.channel_repository.find_by_id(channel_id)
            if not channel:
                raise ValueError(f"channel_id={channel_id}에 해당하는 채널이 없습니다.")
            
            # 3. 채널 맞춤형 트렌드 분석
            channel_concept = getattr(channel, "concept", "")
            target_audience = getattr(channel, "target", "")
            
            channel_keyword = self.rag_service.analyze_channel_trends(
                channel_concept=channel_concept,
                target_audience=target_audience
            )
            
            # 4. Vector DB에 채널 맞춤형 키워드 저장 (skip_vector_save가 False인 경우만)
            if not skip_vector_save:
                await self.content_chunk_repository.save_context(
                    source_type=SourceTypeEnum.PERSONALIZED_KEYWORDS,
                    source_id=report_id,
                    context=json.dumps(channel_keyword, ensure_ascii=False)
                )
                logger.info("채널 맞춤형 키워드를 Vector DB에 저장했습니다.")
            else:
                logger.info("[V2] 벡터 DB 저장을 스킵했습니다.")
            
            # 5. PostgreSQL에 키워드 저장
            # 실시간 트렌드 키워드 저장
            if realtime_keyword and "trends" in realtime_keyword:
                realtime_keywords_to_save = []
                for keyword_data in realtime_keyword["trends"]:
                    trend_keyword = {
                        "report_id": report_id,
                        "keyword_type": TrendKeywordType.REAL_TIME,
                        "keyword": keyword_data.get("keyword", ""),
                        "score": keyword_data.get("score", 0)
                    }
                    realtime_keywords_to_save.append(trend_keyword)
                
                await self.trend_keyword_repository.save_bulk(realtime_keywords_to_save)
                logger.info("실시간 트렌드 키워드를 PostgreSQL DB에 저장했습니다.")

            # 채널 맞춤형 키워드 저장
            if channel_keyword and "customized_trends" in channel_keyword:
                channel_keywords_to_save = []
                for keyword_data in channel_keyword["customized_trends"]:
                    trend_keyword = {
                        "report_id": report_id,
                        "keyword_type": TrendKeywordType.CHANNEL,
                        "keyword": keyword_data.get("keyword", ""),
                        "score": keyword_data.get("score", 0)
                    }
                    channel_keywords_to_save.append(trend_keyword)
                
                await self.trend_keyword_repository.save_bulk(channel_keywords_to_save)
                logger.info("채널 맞춤형 키워드를 PostgreSQL DB에 저장했습니다.")
            
            total_time = time.time() - start_time
            logger.info(f"📊 트렌드 분석 전체 완료 ({total_time:.2f}초)")
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"📊 트렌드 분석 실패 ({total_time:.2f}초): {e}")
            raise

    async def update_report_emotion_counts(self, report_id: int, comment_dict:DefaultDict[str,List[Comment]]) -> bool:
        """
        성공 시 True, 실패 시 False를 반환합니다.
        """
        count_dict = {comment_type: len(comments) for comment_type, comments in comment_dict.items()}
        logger.info("댓글 개수를 PostgreSQL DB에 저장합니다.")
        return await self.report_repository.update_count(report_id, count_dict)

    async def summarize_update_changes(self, report_id: int) -> bool:
        """
        리포트 업데이트 시 변경점 요약 생성
        """
        logger.info(f"🔄 업데이트 요약 생성 시작 - Report ID: {report_id}")

        try:
            # 1. 현재 리포트 조회
            current_report = await self.report_repository.find_by_id(report_id)
            if not current_report:
                logger.error(f"Report {report_id} not found.")
                return False

            # 2. 이전 리포트 로그 조회 (가장 최근 것)
            prev_log = await self.report_log_repository.find_by_video(current_report.video_id)

            if not prev_log:
                logger.info("이전 리포트 로그가 없어 업데이트 요약을 생략합니다.")
                return True

            # 3. 변경점 요약 생성 요청 (Service -> RAG Service)
            update_summary_text = await self.rag_service.create_update_summary(prev_log, current_report)

            # 4. 결과 저장
            current_report.update_summary = update_summary_text
            await self.report_repository.save({"id": current_report.id, "update_summary": update_summary_text})

            return True

        except Exception as e:
            logger.error(f"❌ 업데이트 요약 생성 실패: {e}")
            return False