import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI

from core.enums.source_type import SourceTypeEnum
from core.enums.video_category import VideoCategory
from core.llm.prompt_template_manager import PromptTemplateManager
from domain.channel.model.channel import Channel
from domain.comment.model.comment_type import CommentType
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.idea.dto.idea_dto import IdeaRequest
from domain.log.model.report_log import ReportLog
from domain.report.model.report import Report
from domain.trend_keyword.model.trend_keyword import TrendKeyword
from external.rag.rag_service import RagService
from external.youtube.transcript_service import TranscriptService
from external.youtube.trend_service import TrendService
from external.youtube.video_detail_service import VideoDetailService
from external.youtube.youtube_comment_service import YoutubeCommentService
from external.youtube.youtube_video_service import VideoService

logger = logging.getLogger(__name__)


class RagServiceImpl(RagService):
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.video_detail_service = VideoDetailService()
        self.youtube_comment_service = YoutubeCommentService()
        self.content_chunk_repository = ContentChunkRepository()
        self.trend_service = TrendService()
        self.youtube_video_service = VideoService()
        self.llm = ChatOpenAI(model="gpt-4o-mini")
    
    async def summarize_video(self, video_id: str) -> str:
        context = await self.transcript_service.get_formatted_transcript(video_id)
        print("정리된 자막 = ", context[:100])
        print()


        # 자막이 없는 경우 바로 메시지 반환
        if not context or context.strip() == "":
            return "자막을 불러올 수 없는 영상입니다."

        query = "유튜브 영상 자막을 기반으로 10초 단위 개요를 위의 형식에 따라 작성해주세요."
        return self.execute_llm_chain(context, query, PromptTemplateManager.get_video_summary_prompt())
    
    def classify_comment(self, comment: str) -> Dict[str, Any]:
        query = "유튜브 댓글을 분석하여 감정을 분류하고 백틱(```)이나 설명 없이 순수 JSON으로 출력해주세요."
        result = self.execute_llm_chain(comment, query, PromptTemplateManager.get_comment_reaction_prompt())
        print("LLM 응답 = ", result)

        try:
            clean_json_str = result.strip().replace("```json", "").replace("```", "")
            result_json = json.loads(clean_json_str)
            
            # 리스트로 반환된 경우 첫 번째 요소 사용
            if isinstance(result_json, list):
                if result_json and isinstance(result_json[0], dict):
                    emotion_value = result_json[0].get("emotion")
                    logger.warning(f"LLM이 리스트로 반환됨. 첫 번째 요소 사용: {emotion_value}")
                else:
                    emotion_value = None
            else:
                emotion_value = result_json.get("emotion")
            
            return {
                "comment_type": CommentType.from_emotion_code(emotion_value)
            }
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}, 원본 응답: {result}")
            return {
                "comment_type": CommentType.NEUTRAL
            }
        except Exception as e:
            logger.error(f"댓글 분류 중 예상치 못한 오류: {e}, 응답: {result}")
            return {
                "comment_type": CommentType.NEUTRAL
            }

    def summarize_comments(self, comments: str) -> List[str]:
        query = (
            "유튜브 댓글을 분석하여 요약하고 "
            "백틱(```)이나 설명 없이 순수 JSON으로 출력해주세요."
        )

        result = self.execute_llm_chain(
            comments, query, PromptTemplateManager.get_sumarlize_comment_prompt()
        )
        print("LLM 응답 = ", result)

        try:
            clean_json_str = result.strip().replace("```json", "").replace("```", "")
            result_list = json.loads(clean_json_str)
            contents = [item["content"] for item in result_list if isinstance(item, dict) and "content" in item]
            return contents
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}, 원본 응답: {result}")
            return ["댓글 요약을 생성할 수 없습니다."]

    async def get_popular_videos(self, category: VideoCategory):
        api_start = time.time()
        logger.info(f"{category.name} YouTube 인기 동영상 API 호출 중...")

        # 2. 인기 동영상 목록 유튜브 호출 (YouTube API)
        category_id = category.value
        popular_videos = self.youtube_video_service.get_category_popular(category_id)

        api_time = time.time() - api_start
        logger.info(f"📱 YouTube 인기 동영상 API 호출 완료 ({api_time:.2f}초) - {len(popular_videos)}개 영상")

        # 3. 텍스트로 변환하여 Vector DB에 저장
        for popular in popular_videos:
            pop_video_text = (
                f"제목(가중치 높음): {popular['video_title']}.\n"
                f"주요 태그: {popular['video_hash_tag']}.\n"
                f"영상 설명: {popular['video_description'][:500]}"  # 너무 길면 일부만
            )
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.IDEA_RECOMMENDATION,
                source_id=int(category.value),
                context=pop_video_text)


    async def analyze_idea(self, idea_req: IdeaRequest, channel: Channel, summary: str) -> List[Dict[str, Any]]:
        try:
            # 1. 내 채널 정보 + 요청 내용
            origin_context = f"""
- 채널명: {channel.name}
- 채널 컨셉: {channel.concept}
- 타겟 시청자: {channel.target}
- 카테고리 : {channel.channel_hash_tag.name}
- 최근 영상의 핵심 내용: {summary}
            """
            logging.info("아이디어 내 채널 확인 : %s", origin_context)

            request_context = []

            if idea_req.keyword:
                request_context.append(f"- 아이디어 키워드 : {idea_req.keyword}")
            if idea_req.detail:
                request_context.append(f"- 아이디어 설명 : {idea_req.detail}")
            if idea_req.video_type:
                request_context.append(f"- 아이디어 영상 유형 : {idea_req.video_type}")

            request_context = "\n".join(request_context) if request_context else ""


            # 2. 영상과 의미적으로 가장 유사한 '인기 영상' 청크를 검색 (Vector DB)
            search_start = time.time()
            logger.info("🔍 유사 인기 영상 벡터 검색 중...")
            query_text = f"컨셉: {channel.concept}, 카테고리: {channel.channel_hash_tag}, 최근 영상 요약: {summary}"

            video_embedding = await self.content_chunk_repository.generate_embedding(query_text)
            meta_data = {"query_embedding": str(video_embedding), "source_id": int(channel.channel_hash_tag.value)}
            similar_chunks = await self.content_chunk_repository.search_similar_by_embedding(
                SourceTypeEnum.IDEA_RECOMMENDATION, metadata=meta_data, limit=5
            )

            search_time = time.time() - search_start
            logger.info(f"🔍 유사 인기 영상 벡터 검색 완료 ({search_time:.2f}초) - {len(similar_chunks)}개 청크")

            # 3. 검색된 청크(내용)를 텍스트로 (토큰 효율성을 위해 '제목'만 추출하거나, 저장된 content를 그대로 사용)
            popularity_context = "\n".join([chunk.get("content", "") for chunk in similar_chunks])

            input_data = {
                "request": request_context,
                "origin": origin_context,
                "popularity": popularity_context
            }
            full_prompt = PromptTemplateManager.get_idea_prompt(input_data)
            logger.info("🤖 아이디어 생성 - LLM 호출 전 전체 프롬프트:\n%s", full_prompt)

            # 4. LLM 실행
            llm_start = time.time()
            logger.info("🤖 아이디어 생성 LLM 실행 중...")

            result_str = await self.llm.ainvoke(full_prompt)

            llm_time = time.time() - llm_start
            logger.info(f"🤖 아이디어 생성 LLM 실행 완료 ({llm_time:.2f}초)")

            # LLM의 응답 문자열을 JSON 파싱
            clean_json_str = result_str.content.strip().replace("```json", "").replace("```", "")
            return json.loads(clean_json_str)
        except Exception as e:
            logger.error(f"아이디어 생성 중 오류 발생: {e!r}")
            raise e

    
    async def analyze_algorithm_optimization(self, video_id: str, skip_vector_save: bool = False) -> str:
        """
        유튜브 알고리즘 최적화 분석
        
        Args:
            video_id: YouTube 영상 ID
            
        Returns:
            알고리즘 최적화 분석 결과
        """
        try:
            # 영상 상세 정보 조회 (YouTube API + Redis 캐싱)
            video_start = time.time()
            logger.info("📹 YouTube 영상 상세 정보 API 호출 중...")
            video_details = await self.video_detail_service.get_video_details(video_id)
            video_time = time.time() - video_start
            logger.info(f"📹 YouTube 영상 상세 정보 API 호출 완료 ({video_time:.2f}초)")

            # 채널 정보 조회 (YouTube API)
            channel_id = video_details.get('channelId')

            channel_stats = {}
            if channel_id:
                channel_start = time.time()
                logger.info("📺 YouTube 채널 통계 API 호출 중...")
                channel_stats = self.video_detail_service.get_channel_stats(channel_id)
                channel_time = time.time() - channel_start
                logger.info(f"📺 YouTube 채널 통계 API 호출 완료 ({channel_time:.2f}초)")
            
            # 분석에 필요한 데이터 구조화
            optimization_data = {
                "video": {
                    "title": video_details.get('title', ''),
                    "description": video_details.get('description', ''),
                    "tags": video_details.get('tags', []),
                    "publishedAt": video_details.get('publishedAt', ''),
                    "duration": video_details.get('duration', ''),
                    "viewCount": video_details.get('viewCount', 0),
                    "likeCount": video_details.get('likeCount', 0),
                    "commentCount": video_details.get('commentCount', 0),
                    "thumbnails": video_details.get('thumbnails', {})
                },
                "channel": {
                    "name": video_details.get('channelTitle', ''),
                    "subscriberCount": channel_stats.get('subscriberCount', 0),
                    "totalViewCount": channel_stats.get('viewCount', 0),
                    "totalVideoCount": channel_stats.get('videoCount', 0)
                }
            }
            
            # JSON 형식으로 context 생성
            context = json.dumps(optimization_data, ensure_ascii=False, indent=2)
            
            # 유사한 이전 알고리즘 최적화 분석 사례 검색 (skip_vector_save가 False인 경우만)
            if not skip_vector_save:
                query_text = f"제목: {video_details.get('title', '')}, 설명: {video_details.get('description', '')[:200]}"
                similar_chunks = await self.content_chunk_repository.search_similar_optimization(
                    query_text=query_text,
                    limit=3
                )
                
                # 이전 분석 사례가 있으면 context에 추가
                if similar_chunks:
                    previous_cases = "\n\n---\n\n".join([chunk.get("content", "") for chunk in similar_chunks])
                    context += f"\n\n## 유사 영상의 이전 최적화 분석 사례:\n{previous_cases}"
            
            query = "이 유튜브 영상의 알고리즘 최적화 상태를 분석하고 구체적인 개선 방안을 제시해주세요."
            
            # 프롬프트 템플릿 가져오기 및 LLM 실행
            llm_start = time.time()
            prompt_template = PromptTemplateManager.get_algorithm_optimization_prompt()
            result = self.execute_llm_chain(context, query, prompt_template)
            llm_time = time.time() - llm_start
            logger.info(f"🤖 알고리즘 최적화 LLM 실행 완료 ({llm_time:.2f}초)")
            
            return result
        
        except Exception as e:
            logger.error(f"알고리즘 최적화 분석 중 오류 발생: {e}")
            raise e
            

    def analyze_realtime_trends(self, limit: int = 5, geo: str = "KR") -> Dict:
        """
        실시간 트렌드를 분석하여 YouTube 콘텐츠에 적합한 형태로 반환
        
        Args:
            limit: 분석할 트렌드 개수 (최대 5개)
            geo: 지역 코드 (기본값: KR)
            
        Returns:
            분석된 트렌드 정보
        """
        # 1. Google Trends에서 실시간 트렌드 가져오기 (Google Trends API)
        trends_start = time.time()
        logger.info("📈 Google Trends 실시간 트렌드 API 호출 중...")
        raw_trends = self.trend_service.get_realtime_trends(limit=limit*2, geo=geo)  # 여유있게 가져오기
        trends_time = time.time() - trends_start
        logger.info(f"📈 Google Trends 실시간 트렌드 API 호출 완료 ({trends_time:.2f}초) - {len(raw_trends) if raw_trends else 0}개 트렌드")
        
        if not raw_trends:
            return {"error": "트렌드 데이터를 가져올 수 없습니다."}
        
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        # 3. Context 구성
        context = {
            "trends_data": raw_trends,
            "current_date": current_date,
            "region": geo
        }
        
        # 4. LLM에게 분석 요청
        query = f"실시간 트렌드 중 YouTube 콘텐츠로 적합한 상위 {limit}개를 선정하고 분석해주세요."
        prompt_template = PromptTemplateManager.get_trend_analysis_prompt()
        
        # 5. LLM 실행 및 결과 파싱
        llm_start = time.time()
        logger.info("🤖 실시간 트렌드 분석 LLM 실행 중...")
        result_str = self.execute_llm_chain(
            context=json.dumps(context, ensure_ascii=False),
            query=query,
            prompt_template_str=prompt_template
        )
        llm_time = time.time() - llm_start
        logger.info(f"🤖 실시간 트렌드 분석 LLM 실행 완료 ({llm_time:.2f}초)")
        
        try:
            clean_json_str = result_str.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_json_str)
            return result
        except json.JSONDecodeError:
            return {"error": "결과 파싱 오류", "raw_result": result_str}
    
    

    def analyze_channel_trends(
        self,
        channel_concept: str,
        target_audience: str,
        latest_trend_keywords : List[TrendKeyword]

    ) -> Dict:
        """
        채널 맞춤형 트렌드를 생성하고 분석
        
        Args:
            channel_concept: 채널 컨셉
            target_audience: 타겟 시청자
            
        Returns:
            채널 맞춤형 트렌드 분석 결과
        """
        # 1. Context 구성 (채널 정보)
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        # TrendKeyword 리스트 → dict로 변환
        real_time_keywords_data = [
            {
                "keyword": kw.keyword,
                "score": kw.score,
                "created_at": kw.created_at.strftime("%Y-%m-%d %H:%M:%S")  # datetime → str
            }
            for kw in latest_trend_keywords
]
        context = {
            "channel_concept": channel_concept,
            "target_audience": target_audience,
            "current_date": current_date,
            "latest_5_trend_keywords": real_time_keywords_data

        }
        
        # 2. LLM에게 분석 요청
        query = "채널에 최적화된 트렌드 키워드 5개를 생성하고 분석해주세요."
        prompt_template = PromptTemplateManager.get_channel_customized_trend_prompt()
        
        # 3. 채널 맞춤형 트렌드를 위한 특별 처리
        documents = [Document(page_content=json.dumps(context, ensure_ascii=False))]
        
        # 필요한 모든 변수를 포함한 프롬프트 템플릿 생성
        prompt = PromptTemplate(
            input_variables=["input", "context", "channel_concept", "target_audience", "current_date"],
            template=prompt_template
        )
        
        chat_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate(prompt=prompt)
        ])
        
        # 체인 실행
        llm_start = time.time()
        logger.info("🤖 채널 맞춤형 트렌드 분석 LLM 실행 중...")
        combine_chain = create_stuff_documents_chain(self.llm, chat_prompt)
        result_str = combine_chain.invoke({
            "input": query,
            "context": documents,
            "channel_concept": channel_concept,
            "target_audience": target_audience,
            "current_date": current_date,
            "latest_5_trend_keywords": real_time_keywords_data

        })
        llm_time = time.time() - llm_start
        logger.info(f"🤖 채널 맞춤형 트렌드 분석 LLM 실행 완료 ({llm_time:.2f}초)")
        
        
        try:
            clean_json_str = result_str.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_json_str)
            return result
        except json.JSONDecodeError:
            return {"error": "결과 파싱 오류", "raw_result": result_str}



    def execute_llm_chain(self, context: str, query: str, prompt_template_str: str) -> str:
        """
        LLM 체인을 실행하는 공통 메서드
        :param context: LLM에 제공할 정보(youtube api를 통해 가져온 자막 등)
        :param query: 사용자 질문
        :return: LLM의 응답
        """
        documents = [Document(page_content=context)]
        
        # 프롬프트 템플릿 생성
        prompt_template = PromptTemplate(
            input_variables=["input", "context"],
            template=prompt_template_str
        )

        chat_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate(prompt=prompt_template)
        ])

        # 체인 조합 및 실행
        combine_chain = create_stuff_documents_chain(self.llm, chat_prompt)
        result = combine_chain.invoke({"input": query, "context": documents})
        return result
    
    def execute_llm_direct(self, prompt: str) -> str:
        """
        이미 완성된 프롬프트 문자열을 바로 LLM에 넣어 실행하는 함수

        :param prompt: 완성된 프롬프트 문자열
        :return: LLM의 응답
        """
        # self.llm이 직접 프롬프트 문자열을 받아 실행하는 함수라고 가정
        result = self.llm.invoke(prompt)
        return result.content

    async def create_update_summary(self, prev_report: ReportLog, curr_report: Report):
        """
        리포트 업데이트 시 변경점 요약 생성
        """

        try:
            # 1. 데이터 가공 헬퍼 함수 (내부 정의)
            def safe_get(val, default=0):
                return val if val is not None else default

            def summarize_text(text):
                return text[:100] + "..." if text and len(text) > 100 else (text or "내용 없음")

            def calc_diff_msg(val, avg):
                if val is None or avg is None or avg == 0:
                    return "정보 없음"
                diff = val - avg
                return f"{'+' if diff > 0 else ''}{int(diff)}"

            # 2. 템플릿에 전달할 데이터 준비 (dict 변환)
            template_data = {
                "title": curr_report.title,

                # 이전 데이터
                "prev_view": safe_get(prev_report.view),
                "prev_view_diff": calc_diff_msg(prev_report.view, prev_report.view_channel_avg),
                "prev_like": safe_get(prev_report.like_count),
                "prev_comment": safe_get(prev_report.comment),
                "prev_pos": safe_get(prev_report.positive_comment),
                "prev_neg": safe_get(prev_report.negative_comment),
                "prev_concept": safe_get(prev_report.concept),
                "prev_seo": safe_get(prev_report.seo),
                "prev_revisit": safe_get(prev_report.revisit),
                "prev_leave": summarize_text(prev_report.leave_analyze),

                # 현재 데이터
                "curr_view": safe_get(curr_report.view),
                "curr_view_diff": calc_diff_msg(curr_report.view, curr_report.view_channel_avg),
                "curr_like": safe_get(curr_report.like_count),
                "curr_comment": safe_get(curr_report.comment),
                "curr_pos": safe_get(curr_report.positive_comment),
                "curr_neg": safe_get(curr_report.negative_comment),
                "curr_concept": safe_get(curr_report.concept),
                "curr_seo": safe_get(curr_report.seo),
                "curr_revisit": safe_get(curr_report.revisit),
                "curr_leave": summarize_text(curr_report.leave_analyze),
            }

            # 탬플릿 생성
            update_summary_prompt = PromptTemplateManager.summarize_update_changes(template_data)

            # 4. LLM 실행
            llm_start = time.time()
            logger.info("🤖 업데이트 요약 LLM 실행 중...")

            response = await self.llm.ainvoke(update_summary_prompt)
            update_summary_text = response.content # 객체에서 문자열 추출

            llm_time = time.time() - llm_start
            logger.info(f"🤖 업데이트 요약 LLM 실행 완료 ({llm_time:.2f}초)")

            return update_summary_text

        except Exception as e:
            logger.error(f"❌ 업데이트 요약 생성 실패: {e}")
            raise e