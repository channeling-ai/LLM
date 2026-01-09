from domain.content_chunk.model.content_chunk import ContentChunk
from core.database.repository.vector_repository import VectorRepository
from core.config.database_config import PGSessionLocal
from sqlalchemy import text
from core.enums.source_type import SourceTypeEnum
from typing import List, Dict, Any

class ContentChunkRepository(VectorRepository[ContentChunk]):
    def model_class(self) -> type[ContentChunk]:
        """ContentChunk 모델 클래스를 반환합니다."""
        return ContentChunk

    async def exists_by_chunk_type_and_id(self, chunk_type: str, source_id: int) -> bool:
        async with PGSessionLocal() as session:
            query = text("""
                SELECT 1 FROM content_chunk
                WHERE source_id = :source_id
                AND meta ->> 'chunk_type' = :chunk_type
                LIMIT 1
            """)
            result = await session.execute(query, {"chunk_type": chunk_type, "source_id": source_id})
            row = result.fetchone()
            return row is not None
    
    async def search_similar_optimization(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        현재 영상과 유사한 알고리즘 최적화 청크 검색
        
        Args:
            query_text: 검색 쿼리 텍스트 (현재 영상 정보)
            limit: 검색할 최대 결과 수
            
        Returns:
            유사도 순으로 정렬된 알고리즘 최적화 청크 목록
        """
        # 쿼리 텍스트의 임베딩 생성
        query_embedding = await self.generate_embedding(query_text)
        meta_data = {"query_embedding": str(query_embedding)}
        
        # 알고리즘 최적화 타입의 유사 청크 검색
        return await self.search_similar_by_embedding(
            SourceTypeEnum.ALGORITHM_OPTIMIZATION,
            metadata=meta_data,
            limit=limit
        )
    