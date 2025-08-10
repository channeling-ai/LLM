from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

from core.enums.video_category import VideoCategory


class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(description="채널 ID")
    youtube_video_id: str = Field(description="YouTube 비디오 ID")
    video_category: VideoCategory = Field(description="비디오 카테고리")
    title: Optional[str] = Field(description="비디오 제목")
    view: Optional[int] = Field(description="조회수")
    like_count: Optional[int] = Field(description="좋아요 수")
    comment_count: Optional[int] = Field(description="댓글 수")
    link: Optional[str] = Field(description="비디오 링크")
    upload_date: Optional[datetime] = Field(description="업로드 날짜")
    thumbnail: Optional[str] = Field(description="썸네일 URL")
    description: Optional[str] = Field(description="비디오 설명")
    # data v3
    # duration : Optional[int] = Field(description="비디오 길이 (초 단위)")
    # analytics 항목
    # share_count: Optional[int] = Field(description="공유 수")
    # average_view_duration: Optional[int] = Field(description="평균 시청 시간 (초)")
    # subscribers_gained: Optional[int] = Field(description="구독자 증가 수")
