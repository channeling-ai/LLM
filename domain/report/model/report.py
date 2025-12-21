from datetime import datetime
from core.utils.datetime_utils import get_kst_now_naive
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text


class Report(SQLModel, table=True):
    """Report 테이블 모델 - Spring Entity를 SQLModel로 변환"""
    __tablename__ = "report"
    
    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key - Video 테이블 참조
    video_id: int = Field(description="영상 ID")
    
    # 영상 정보
    title: str = Field(description="영상 제목")
    view: int = Field(description="조회수")
    view_topic_avg: int = Field(description="동일 주제 평균 조회수")
    view_channel_avg: int = Field(description="채널 평균 조회수")
    
    # 좋아요 정보
    like_count: int = Field(description="좋아요 수")
    like_topic_avg: int = Field(description="동일 주제 평균 좋아요 수")
    like_channel_avg: int = Field(description="채널 평균 좋아요 수")
    
    # 댓글 정보
    comment: int = Field(description="댓글 수")
    comment_topic_avg: int = Field(description="동일 주제 평균 댓글 수")
    comment_channel_avg: int = Field(description="채널 평균 댓글 수")
    
    # 분석 지표
    concept: int = Field(description="컨셉 일관성")
    seo: int = Field(description="SEO 구성")
    revisit: int = Field(description="재방문률")
    
    # 텍스트 분석
    summary: str = Field(sa_column=Column(Text), description="요약본")
    
    # 댓글 감정 분석
    neutral_comment: int = Field(description="중립 댓글 수")
    advice_comment: int = Field(description="조언 댓글 수") 
    positive_comment: int = Field(description="긍정 댓글 수")
    negative_comment: int = Field(description="부정 댓글 수")
    
    # 분석 결과
    leave_analyze: str = Field(sa_column=Column(Text), description="시청자 이탈 분석")
    optimization: str = Field(sa_column=Column(Text), description="알고리즘 최적화")

    # 업데이트 요약본
    update_summary: Optional[str] = Field(default=None, sa_column=Column(Text), description="업데이트 요약본")
    
    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)
    updated_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)