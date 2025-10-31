from abc import ABC, abstractmethod
from typing import Dict, TypeVar, Generic, Any, Optional, List
import os
from sqlalchemy.sql import text
from openai import AsyncOpenAI
from dotenv import load_dotenv
from core.config.database_config import PGSessionLocal
from sqlmodel import SQLModel
from sqlalchemy import text
from domain.content_chunk.model.content_chunk import ContentChunk
from core.enums.source_type import SourceTypeEnum
load_dotenv()

T = TypeVar("T", bound=SQLModel)
"""
예상 사용 예시:
---데이터 저장할 때---
1. 추후에 context로 제공할 텍스트 정보를 받아옴
(ex. 채널 정보, 이전 추천 아이디어, 영상 요약, 시청 최적화 전략, 이탈 분석)
* 단순히 이전 리포트의 정보만 쓸거면, 리포트 하나 생성 후에 각 요소마다 source_type만 다르게 해서 저장하는 것도 괜찮아 보임!
2. content_chunk_repository.save_context(source_type: idea, source_id: 1,  context: 후쿠오카에서 꼭 가야할 맛집) 호출
3. 알아서 텍스트 청크로 나누고, 임베딩 생성 후 벡터 저장소에 저장

---검색할 때---
1. content_chunk_repository.search_similar(source_type: idea, limit=5) 호출
2. 유사한 청크들을 반환받음
3. 청크들을 context로 추가해서 llm에 전달
* 예시로는 채널에 대한 아이디어를 생성할 때, 이전에 저장된 아이디어들을 참고할 수 있음
* source_type만으로는 필터링하기 힘들 경우, metadata를 활용해서 추가 필터링 가능
"""
class VectorRepository(Generic[T], ABC):
    """벡터 저장소를 위한 추상 클래스입니다."""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"

    @abstractmethod
    def model_class(self) -> type[T]:
        """서브클래스에서 구체적인 모델 클래스를 반환해야 함"""
        pass
    
    async def generate_embedding(self, text: str) -> List[float]:
        """OpenAI API를 사용해서 텍스트(청크)의 임베딩 생성"""
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def chunk_text(self, text: str, chunk_size: int = 150, overlap: int = 15) -> List[str]:
        """텍스트를 청크로 분할"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            # 의미 없는 공백은 저장 skip
            if chunk.strip():
                chunks.append(chunk)
            
            start = end - overlap
            
        return chunks

    async def save(self, data: Dict[str, Any]) -> T:
        
        async with PGSessionLocal() as session:
            
            # 모델 인스턴스 생성
            instance = self.model_class()(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def save_context(self, source_type: SourceTypeEnum, source_id: int, context: str, meta: Dict[str, any] = None):
        """
        컨텍스트를 벡터 저장소에 저장
        parameters:
            source_type: str - 'video_info', 'channel_data', 'report' 등(이걸 뭐로 할 지 잘 모르겠음..)
            source_id: int - 해당 소스의 ID (예: video_id, channel_id, report_id 등)
            context: str - 저장할 텍스트 컨텍스트
            metadata: Dict[str, Any] - 추가 메타데이터 (선택적)
        """
        chunks = self.chunk_text(context)
        for i, chunk in enumerate(chunks):
            embedding = await self.generate_embedding(chunk)
            await self.save({
                "source_type": source_type,
                "source_id": source_id,
                "content": chunk,
                "chunk_index": i,
                "embedding": embedding,
                "meta": meta
            })

    

    

    # 특정 유사도 조회
    async def search_similar_by_embedding(self, source_type: SourceTypeEnum, metadata: Dict[str, Any] = None, limit: int = 10) -> List[
        Dict[str, Any]]:

        async with PGSessionLocal() as session:

            template_embedding = metadata.get("query_embedding")

            # 2. 해당 source_type의 content_chunks 중 가장 유사한 것들 검색
            base_query = """
                         SELECT c.id,
                                c.source_type,
                                c.source_id,
                                c.content,
                                c.chunk_index,
                                c.meta,
                                c.created_at,
                                1 - (c.embedding <=> :template_embedding) as similarity
                         FROM content_chunk c
                         WHERE c.source_type = :source_type \
                         """

            params = {
                "template_embedding": template_embedding,
                "source_type": source_type.name,
                "limit": limit
            }

            # 메타데이터 조건 추가(있을 경우)
            if metadata and "source_id" in metadata:
                base_query += " AND c.source_id = :source_id"
                params["source_id"] = metadata["source_id"]

            # 정렬 조건 및 쿼리 실행
            final_query_string = base_query + """
                ORDER BY c.embedding <=> :template_embedding
                LIMIT :limit
            """
            search_query = text(final_query_string)
            result = await session.execute(search_query, params)

            chunks = []
            for row in result:
                chunks.append({
                    "id": row.id,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "content": row.content,
                    "chunk_index": row.chunk_index,
                    "meta": row.meta,
                    "created_at": row.created_at,
                    "similarity": row.similarity
                })

            return chunks

    
    async def search_similar_K(self,query :str, source_type: str, source_id : str,metadata: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        query_embedding = await self.generate_embedding(query)  # OpenAI or other model로 임베딩
        query_embedding = str(query_embedding)
        async with PGSessionLocal() as session:
            # 메타 조건 SQL 동적 생성
            meta_filter_sql = ""
            meta_params = {}
            if metadata:
                for i, (k, v) in enumerate(metadata.items()):
                    meta_filter_sql += f" AND c.meta ->> :meta_key_{i} = :meta_val_{i}"
                    meta_params[f"meta_key_{i}"] = k
                    meta_params[f"meta_val_{i}"] = v

            # 유사한 청크 검색
            search_query = text(f"""
                SELECT 
                    c.id,
                    c.source_type,
                    c.source_id,
                    c.content,
                    c.chunk_index,
                    c.meta,
                    c.created_at,
                    1 - (c.embedding <=> :query_embedding) AS similarity
                FROM content_chunk c
                WHERE c.source_type = :source_type
                AND c.source_id = :source_id
                {meta_filter_sql}
                ORDER BY c.embedding <=> :query_embedding
                LIMIT :limit
            """)

            result = await session.execute(
                search_query,
                {
                    "query_embedding": query_embedding,
                    "source_type": source_type,
                    "source_id": source_id,
                    "limit": limit,
                    **meta_params
                }
            )
            rows = result.fetchall()  # 또는 fetchall()이 async면 await 붙이기
            return [
                {
                    "id": row.id,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "content": row.content,
                    "chunk_index": row.chunk_index,
                    "meta": row.meta,
                    "created_at": row.created_at.isoformat(),
                    "similarity": row.similarity,
                }
                for row in rows
            ]

        

   

    
