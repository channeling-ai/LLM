from typing import Optional
from datetime import datetime
from pydantic import Field, ConfigDict
from pydantic.alias_generators import to_camel

from sqlmodel import SQLModel

from domain.log.model.delete_type import DeleteType
from domain.log.model.task_status import TaskStatus


class ReportLog(SQLModel, table=True):
    # 기본 설정: snake_case <-> camelCase 자동 변환
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True  # ORM 객체에서 데이터 읽기 허용
    )

    # ID는 생성 전에는 없을 수 있으므로 Optional
    id: Optional[int] = None
    logged_at: Optional[datetime] = None

    report_id: Optional[int] = None
    video_id: Optional[int] = None

    title: Optional[str] = None  # 영상 제목

    view: Optional[int] = None  # 조회수 (Long -> int)
    view_topic_avg: Optional[float] = None  # 동일 주제 평균 조회수 (Double -> float)
    view_channel_avg: Optional[float] = None  # 채널 평균 조회수

    like_count: Optional[int] = None  # 좋아요 수
    like_topic_avg: Optional[float] = None  # 동일 주제 평균 좋아요 수
    like_channel_avg: Optional[float] = None  # 채널 평균 좋아요 수

    comment: Optional[int] = None  # 댓글 수
    comment_topic_avg: Optional[float] = None  # 동일 주제 평균 댓글 수
    comment_channel_avg: Optional[float] = None  # 채널 평균 댓글 수 (Java 주석엔 좋아요 수로 되어있으나 변수명상 댓글 수로 추정)

    concept: Optional[int] = None  # 컨셉 일관성
    seo: Optional[int] = None  # seo 구성
    revisit: Optional[int] = None  # 재방문률

    summary: Optional[str] = None  # 요약본 (TEXT)

    neutral_comment: Optional[int] = None  # 중립 댓글 수
    advice_comment: Optional[int] = None  # 조언 댓글 수
    positive_comment: Optional[int] = None  # 긍정 댓글 수
    negative_comment: Optional[int] = None  # 부정 댓글 수

    leave_analyze: Optional[str] = None  # 시청자 이탈 분석 (TEXT)
    optimization: Optional[str] = None  # 알고리즘 최적화 (TEXT)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # [로그에서만 추가]
    overview_status: Optional[TaskStatus] = None  # 개요 생성 상태
    analyze_status: Optional[TaskStatus] = None  # 분석 생성 상태

    delete_type: Optional[DeleteType] = None  # 삭제 타입 확인

    # [로그에서만 추가] 댓글 내용 (length=400)
    positive_comment_content: Optional[str] = Field(None, max_length=400)
    negative_comment_content: Optional[str] = Field(None, max_length=400)
    neutral_comment_content: Optional[str] = Field(None, max_length=400)
    advice_comment_content: Optional[str] = Field(None, max_length=400)



