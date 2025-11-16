from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from typing import Dict, Optional, List
import logging
import json

from core.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)
load_dotenv()

class VideoDetailService:
    """YouTube Video Data API 서비스"""

    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not found in environment variables")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    async def get_video_details(self, video_id: str) -> Dict:
        """
        영상 상세 정보 조회 (Redis 캐싱 적용, 5분 TTL)

        Args:
            video_id: YouTube 영상 ID

        Returns:
            영상 정보 딕셔너리 (제목, 설명, 태그, 통계 등)
        """
        cache_key = f"video_detail:{video_id}"

        # Redis 클라이언트 가져오기
        redis_client = await get_redis_client()
        if redis_client is None:
            logger.warning("Redis 캐시 없이 YouTube API 직접 호출")
            return self._fetch_video_details(video_id)

        try:
            # 캐시 확인
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ Redis 캐시 HIT: video_detail:{video_id}")
                return json.loads(cached)

            # 캐시 미스 - API 호출 후 캐싱
            logger.info(f"⚠️  Redis 캐시 MISS: video_detail:{video_id}")
            data = self._fetch_video_details(video_id)

            # 5분 TTL로 캐싱
            await redis_client.setex(cache_key, 300, json.dumps(data))
            logger.info(f"💾 Redis 캐시 저장: video_detail:{video_id} (TTL: 5분)")
            return data

        except Exception as e:
            logger.warning(f"Redis 캐시 처리 실패, API 직접 호출: {e}")
            return self._fetch_video_details(video_id)

    def _fetch_video_details(self, video_id: str) -> Dict:
        """YouTube API로 영상 상세 정보 조회 (내부 메서드)"""
        try:
            response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()

            if not response.get('items'):
                logger.error(f"Video {video_id} not found")
                return {}

            video = response['items'][0]
            # 필요한 정보 추출

            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})

            return {
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'tags': snippet.get('tags', []),
                'categoryId': snippet.get('categoryId', ''),
                'publishedAt': snippet.get('publishedAt', ''),
                'channelId': snippet.get('channelId', ''),
                'channelTitle': snippet.get('channelTitle', ''),
                'thumbnails': snippet.get('thumbnails', {}),

                'duration': content_details.get('duration', ''),

                'viewCount': int(statistics.get('viewCount', 0)),
                'likeCount': int(statistics.get('likeCount', 0)),
                'commentCount': int(statistics.get('commentCount', 0))

            }

        except HttpError as e:
            if e.resp.status == 403:
                logger.error("YouTube API quota exceeded")
            elif e.resp.status == 404:
                logger.error(f"Video {video_id} not found")
            else:
                logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_video_details: {e}")
            raise
    
    def get_channel_stats(self, channel_id: str) -> Dict:
        """
        채널 통계 정보 조회
        
        Args:
            channel_id: YouTube 채널 ID
            
        Returns:
            채널 통계 딕셔너리 (구독자수, 총 조회수, 총 영상수)
        """
        try:
            response = self.youtube.channels().list(
                part='statistics',
                id=channel_id
            ).execute()
            
            if not response.get('items'):
                logger.error(f"Channel {channel_id} not found")
                return {}
            
            statistics = response['items'][0].get('statistics', {})
            
            return {
                'subscriberCount': int(statistics.get('subscriberCount', 0)),
                'viewCount': int(statistics.get('viewCount', 0)),
                'videoCount': int(statistics.get('videoCount', 0))
            }
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error("YouTube API quota exceeded")
            elif e.resp.status == 404:
                logger.error(f"Channel {channel_id} not found")
            else:
                logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_channel_stats: {e}")
            raise
    
    def get_category_benchmarks(self, category_id: str, region_code: str = 'KR') -> Dict:
        """
        카테고리별 평균 성과 지표 계산
        
        Args:
            category_id: YouTube 카테고리 ID
            region_code: 지역 코드 (기본값: 'KR')
            
        Returns:
            카테고리 평균 지표 (평균 조회수, 좋아요, 댓글)
        """
        try:
            # 해당 카테고리의 인기 영상 조회
            response = self.youtube.videos().list(
                part='statistics',
                chart='mostPopular',
                videoCategoryId=category_id,
                regionCode=region_code,
                maxResults=50
            ).execute()
            
            if not response.get('items'):
                logger.warning(f"No videos found for category {category_id}")
                return {
                    'avgViewCount': 0,
                    'avgLikeCount': 0,
                    'avgCommentCount': 0,
                    'sampleSize': 0
                }
            
            # 통계 수집
            view_counts = []
            like_counts = []
            comment_counts = []
            
            for video in response['items']:
                stats = video.get('statistics', {})
                view_counts.append(int(stats.get('viewCount', 0)))
                like_counts.append(int(stats.get('likeCount', 0)))
                comment_counts.append(int(stats.get('commentCount', 0)))
            
            # 평균 계산
            sample_size = len(view_counts)
            avg_views = sum(view_counts) / sample_size if sample_size > 0 else 0
            avg_likes = sum(like_counts) / sample_size if sample_size > 0 else 0
            avg_comments = sum(comment_counts) / sample_size if sample_size > 0 else 0
            
            # 중앙값도 계산 (이상치 영향 최소화)
            view_counts.sort()
            like_counts.sort()
            comment_counts.sort()
            
            median_views = view_counts[sample_size // 2] if sample_size > 0 else 0
            median_likes = like_counts[sample_size // 2] if sample_size > 0 else 0
            median_comments = comment_counts[sample_size // 2] if sample_size > 0 else 0
            
            return {
                'avgViewCount': int(avg_views),
                'avgLikeCount': int(avg_likes),
                'avgCommentCount': int(avg_comments),
                'medianViewCount': median_views,
                'medianLikeCount': median_likes,
                'medianCommentCount': median_comments,
                'sampleSize': sample_size
            }
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error("YouTube API quota exceeded")
            else:
                logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_category_benchmarks: {e}")
            raise