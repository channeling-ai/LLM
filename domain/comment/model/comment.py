from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Enum as SQLEnum
from datetime import datetime
from typing import Optional
from domain.comment.model.comment_type import CommentType
from core.utils.datetime_utils import get_kst_now_naive
from sqlalchemy import Column, Enum as SAEnum



class Comment(SQLModel, table=True):
    """댓글 모델 - SQLModel로 정의"""
    __tablename__ = "comment"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", description="리포트 ID")
    comment_type: str = Field(
        sa_column=Column(SQLEnum('ADVICE_OPINION', 'NEGATIVE', 'NEUTRAL', 'POSITIVE', name='comment_type_enum')),
        description="댓글 타입"
    )
    comment_type: str = Field(
        sa_column=Column(
            SAEnum(CommentType, name="commenttype", native_enum=False),
            nullable=False
        )
    )
    content: str = Field(description="댓글 내용")
    
    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)
    updated_at: Optional[datetime] = Field(default_factory=get_kst_now_naive)
