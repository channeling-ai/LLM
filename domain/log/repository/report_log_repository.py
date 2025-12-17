from sqlmodel import select, desc, and_

from core.config.database_config import PGSessionLocal
from core.database.repository.crud_repository import CRUDRepository
from domain.log.model.report_log import ReportLog
from domain.task.model.task import Status


class ReportLogRepository(CRUDRepository[ReportLog]):
    def model_class(self) -> type[ReportLog]:
        return ReportLog


    async def find_by_video(self, video_id):
        async with PGSessionLocal() as session:
            statement = (
                select(ReportLog)
                .where(
                    and_(
                        ReportLog.video_id == video_id,
                        ReportLog.overview_status == Status.COMPLETED,
                        ReportLog.analyze_status == Status.COMPLETED,
                    )
                )
                .order_by(desc(ReportLog.created_at))
                .limit(1)
            )

            result = await session.execute(statement)
            return result.scalar_one_or_none()



