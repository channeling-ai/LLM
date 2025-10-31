from sqlmodel import select, func

from core.config.database_config import PGSessionLocal
from core.database.repository.crud_repository import CRUDRepository
from domain.video.model.video import Video


class VideoRepository(CRUDRepository[Video]):
    def model_class(self) -> type[Video]:
        return Video

    # 채널별 비디오 조회
    async def find_by_channel_id(self, channel_id: int, limit: int = None) -> list[Video]:
        """
        채널 ID로 비디오를 조회합니다.
        limit가 지정되면 최신 영상을 limit 개수만큼만 반환합니다.
        """
        async with PGSessionLocal() as session:
            statement = select(self.model_class()).where(
                self.model_class().channel_id == channel_id
            ).order_by(self.model_class().upload_date.desc())  # 최신순 정렬

            if limit:
                statement = statement.limit(limit)

            result = await session.execute(statement)
            return result.scalars().all()