from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, DateTime, JSON, text
from pgvector.sqlalchemy import Vector
from core.enums.source_type import SourceTypeEnum


class ContentChunk(SQLModel, table=True):
    __tablename__ = "content_chunk"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_type: SourceTypeEnum = Field(nullable=False)
    source_id: int = Field(nullable=False)   # video_id, channel_id, report_id 등
    content: str = Field(nullable=False)                      # 텍스트 데이터(청크)
    chunk_index: int = Field(nullable=False)                  # 원본에서의 청크 순서
    embedding: List[float] = Field(sa_column=Column(Vector(3072)))  # 벡터 데이터
    meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # 메타데이터
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, server_default=text("NOW()"))
    )
