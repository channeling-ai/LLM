import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from core.cache.redis_client import get_redis_client

# .env 파일 로드
load_dotenv()

logger = logging.getLogger(__name__)

class TranscriptService:
    """YouTube 자막 처리 서비스"""

    def __init__(self):
        # Webshare 프록시 설정
        self.proxy_username = os.getenv("PROXY_USERNAME")
        self.proxy_password = os.getenv("PROXY_PASSWORD")

        # 프록시 설정된 API 인스턴스 생성
        self.ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=self.proxy_username,
                proxy_password=self.proxy_password,
                filter_ip_locations=["kr", "jp"]  # 한국, 일본 지역으로 제한

            )
        )

    def fetch_transcript(self, video_id: str, languages=['ko', 'en']) -> list:
        """
        공통: YouTubeTranscriptApi를 사용해 자막 리스트 반환
        각 요소: FetchedTranscriptSnippet 객체 (text, start, duration 속성 포함)
        """
        try:
            transcript_list = self.ytt_api.list(video_id) # -> 가능한 자막의 언어 리스트
            transcript = transcript_list.find_transcript(languages) # -> 기본으로 ko, en 
            return transcript.fetch() #-> 가져오기
        except Exception as e:
            print(f"자막 불러오기 실패: {e}")
            return []

    @staticmethod
    def format_time(seconds: float) -> str:
        """초 단위를 '분:초' 문자열로 변환"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    async def get_formatted_transcript(self, video_id: str, languages=['ko', 'en']) -> str:
        """
        fetch_transcript로 자막 가져와서 사람이 읽기 좋은 문자열 포맷으로 변환
        예: "안녕하세요. (0:08 - 0:13)"

        Note: Redis 캐싱을 사용하는 get_structured_transcript()를 호출합니다.
        """
        structured = await self.get_structured_transcript(video_id, languages)
        if not structured:
            return ""

        formatted_lines = []
        for entry in structured:
            start = entry["start_time"]
            end = entry["end_time"]
            start_fmt = self.format_time(start)
            end_fmt = self.format_time(end)
            line = f"{entry['text']} ({start_fmt} - {end_fmt})"
            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    async def get_structured_transcript(self, video_id: str, languages=['ko', 'en']) -> list[dict]:
        """
        fetch_transcript로 자막 가져와서
        [{'text': ..., 'start_time': ..., 'end_time': ...}, ...] 형식 리스트로 반환

        Redis 캐싱 적용:
        - 캐시 hit: Redis에서 반환 (< 1ms)
        - 캐시 miss: YouTube API 호출 후 캐싱 (5-10초)
        - 병렬 처리 경쟁 조건: Lock을 사용하여 중복 API 호출 방지
        - TTL: 30일 (자막은 불변 데이터)
        """
        cache_key = f"transcript:{video_id}"
        lock_key = f"transcript:lock:{video_id}"

        # Redis 클라이언트 가져오기
        redis_client = await get_redis_client()

        # Redis 사용 불가 시 직접 조회
        if redis_client is None:
            logger.warning(f"⚠️  Redis 없이 Transcript 조회: {video_id}")
            return await self._fetch_and_structure_async(video_id, languages)

        # 1. Redis 캐시 확인
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ Transcript cache hit: {video_id}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"❌ Redis 조회 실패: {e}")
            # Redis 오류 시 직접 조회
            return await self._fetch_and_structure_async(video_id, languages)

        # 2. Lock 획득 시도 (다른 consumer가 조회 중인지 확인)
        try:
            acquired = await redis_client.set(lock_key, "1", nx=True, ex=30)

            if acquired:
                # 이 consumer가 조회 담당
                logger.info(f"🔒 Transcript lock 획득, YouTube API 호출: {video_id}")

                try:
                    # YouTube API 호출
                    structured = await self._fetch_and_structure_async(video_id, languages)

                    # Redis에 캐싱 (30일)
                    ttl = 30 * 24 * 3600  # 30일
                    await redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(structured, ensure_ascii=False)
                    )
                    logger.info(f"💾 Transcript cached (30d TTL): {video_id}")

                    return structured

                finally:
                    # Lock 해제
                    await redis_client.delete(lock_key)

            else:
                # 다른 consumer가 조회 중 → 대기 후 캐시 확인
                logger.info(f"⏳ 다른 consumer가 Transcript 조회 중, 대기: {video_id}")

                for attempt in range(30):  # 최대 30초 대기
                    await asyncio.sleep(1)

                    cached = await redis_client.get(cache_key)
                    if cached:
                        logger.info(f"✅ Transcript cache hit (대기 후): {video_id}")
                        return json.loads(cached)

                # 타임아웃 → 직접 조회
                logger.warning(f"⏰ Transcript cache 대기 타임아웃, 직접 조회: {video_id}")
                return await self._fetch_and_structure_async(video_id, languages)

        except Exception as e:
            logger.error(f"❌ Redis lock 처리 실패: {e}")
            # Lock 오류 시 직접 조회
            return await self._fetch_and_structure_async(video_id, languages)

    def _fetch_and_structure(self, video_id: str, languages=['ko', 'en']) -> list[dict]:
        """
        YouTube API로 자막을 조회하고 구조화된 형식으로 반환
        (내부 헬퍼 메서드)
        """
        transcription = self.fetch_transcript(video_id, languages)
        if not transcription:
            return []

        structured = []
        for entry in transcription:
            structured.append({
                "text": entry.text,
                "start_time": entry.start,
                "end_time": entry.start + entry.duration
            })

        return structured

    async def _fetch_and_structure_async(self, video_id: str, languages=['ko', 'en']) -> list[dict]:
        """_fetch_and_structure의 비동기 래퍼"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._fetch_and_structure, video_id, languages
        )
