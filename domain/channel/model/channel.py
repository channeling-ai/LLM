from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

from core.enums.video_category import VideoCategory
from core.utils.datetime_utils import get_kst_now_naive
from sqlalchemy import Column, Enum as SAEnum


class Channel(SQLModel, table=True):
    """Channel 테이블 모델 - Spring Entity를 SQLModel로 변환"""
    __tablename__ = "channel"

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign Key - Video 테이블 참조
    member_id: int = Field(description="멤버 ID")

    youtube_channel_id: str = Field(description="YouTube 채널 ID")
    youtube_playlist_id: str = Field(description="YouTube 재생목록 ID")
    name: str = Field(description="채널 이름")
    view: int = Field(description="채널 조회수")
    like_count: int = Field(description="채널 좋아요 수")
    subscribe: int = Field(description="채널 구독자 수")
    share: int = Field(description="채널 공유 수")
    video_count: int = Field(description="채널 비디오 수")
    comment: int = Field(description="채널 댓글 수")
    link: str = Field(description="채널 링크")
    join_date: datetime = Field(description="채널 가입 날짜")
    target: str = Field(description="시청자 타겟")
    concept: str = Field(description="채널 컨셉")
    image: str = Field(description="채널 프로필 이미지")
    channel_hash_tag: VideoCategory  = Field(
        sa_column=Column(
            SAEnum(VideoCategory, name="status", native_enum=False),
            nullable=False
        )
    )
    channel_update_at: datetime = Field(description="채널 업데이트 날짜")

    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)
    updated_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)

