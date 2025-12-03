from sqlmodel import select

from core.config.database_config import PGSessionLocal
from core.database.repository.crud_repository import CRUDRepository
from domain.task.model.task import Task


class TaskRepository(CRUDRepository[Task]):
    def model_class(self) -> type[Task]:
        """Task 모델 클래스를 반환합니다."""
        return Task


    async def find_by_report(self, report_id):
        async with PGSessionLocal() as session:
            statement = select(Task).where(Task.report_id == report_id)

            result = await session.execute(statement)
            return result.scalar_one_or_none()