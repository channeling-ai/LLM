from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import async_session

from core.config.database_config import PGSessionLocal
from core.database.repository.crud_repository import CRUDRepository, T
from domain.comment.model.comment import Comment


class CommentRepository(CRUDRepository[Comment]):
    def __init__(self):
        self.async_session = async_session

    def model_class(self) -> type[Comment]:
        return Comment