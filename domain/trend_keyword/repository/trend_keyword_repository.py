from core.database.repository.crud_repository import CRUDRepository
from domain.trend_keyword.model.trend_keyword import TrendKeyword
from typing import List
from sqlalchemy import desc
from sqlmodel import select
from sqlalchemy import delete

from core.config.database_config import PGSessionLocal

class TrendKeywordRepository(CRUDRepository):
    def model_class(self) -> type["TrendKeyword"]:
        return TrendKeyword
    

    async def get_latest_real_time_keywords(self, limit: int = 5) -> List[TrendKeyword]:
        async with PGSessionLocal() as session:  # type: AsyncSession
            query = select(self.model_class()).where(
                self.model_class().keyword_type == "REAL_TIME"  # Enum 값 확인
            ).order_by(
                desc(self.model_class().created_at)
            ).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()
        
    async def get_latest_channel_keywords(self, channe_id: int) -> List[TrendKeyword]:
        async with PGSessionLocal() as session:  # type: AsyncSession
            query = select(self.model_class()).where(
                self.model_class().keyword_type == "CHANNEL",
                self.model_class().channel_id == channe_id #  Enum 값 확인
            )

            result = await session.execute(query)
            return result.scalars().all()
        

    async def delete_trend_keywords_bulk(self, trend_keyword_list: list[TrendKeyword]):
        ids = [tk.id for tk in trend_keyword_list]
        async with PGSessionLocal() as session:
            query = delete(self.model_class()).where(self.model_class().id.in_(ids))
            await session.execute(query)
            await session.commit()

        



