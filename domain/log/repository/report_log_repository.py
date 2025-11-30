from sqlmodel import select, desc

from core.config.database_config import PGSessionLocal
from core.database.repository.crud_repository import CRUDRepository
from domain.log.model.report_log import ReportLog


class ReportLogRepository(CRUDRepository[ReportLog]):
    def model_class(self) -> type[ReportLog]:
        return ReportLog

    async def find_by_video(self, video_id):
        async with PGSessionLocal() as session:
            statement = select(ReportLog).where(ReportLog.video_id == video_id).order_by(
                desc(ReportLog.created_at)).limit(1)

            result = await session.execute(statement)
            return result.scalar_one_or_none()




