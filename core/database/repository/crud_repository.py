from typing import Dict, TypeVar, Generic, Any, Optional, List
from abc import ABC, abstractmethod
from sqlmodel import SQLModel, select
from sqlalchemy import update
from core.config.database_config import PGSessionLocal


T = TypeVar("T", bound=SQLModel)

class CRUDRepository(Generic[T], ABC):
    
    
    @abstractmethod
    def model_class(self) -> type[T]:
        """서브클래스에서 구체적인 모델 클래스를 반환해야 함"""
        pass
    
    async def save(self, data: Dict[str, Any]) -> T:
        """
        데이터를 저장하거나 업데이트합니다. (부분 저장 지원)
        
        parameters:
            data: Dict[str, Any] - 저장할 데이터
        returns:
            T - 저장된 모델 인스턴스
        """
        if "id" in data and data["id"] is not None:
            # UPDATE - 기존 레코드 부분 업데이트
            return await self._update_partial(data)
        else:
            # INSERT - 새 레코드 생성
            return await self._create_new(data)

    async def save_bulk(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """여러 엔티티를 한 번에 저장"""
        async with PGSessionLocal() as session:
            # 딕셔너리를 모델 인스턴스로 변환
            instances = []
            for data in data_list:
                data_copy = data.copy()
                data_copy.pop("id", None)  # id가 있으면 제거 (자동 생성)
                instance = self.model_class()(**data_copy)
                instances.append(instance)
            
            session.add_all(instances)
            await session.commit()
            
            # refresh all instances
            for instance in instances:
                await session.refresh(instance)
            
        return instances


    async def _create_new(self, data: Dict[str, Any]) -> T:
        """새 레코드 생성"""
        async with PGSessionLocal() as session:
            # id 제거 (자동 생성되므로)
            data_copy = data.copy()
            data_copy.pop("id", None)
            
            # 모델 인스턴스 생성
            instance = self.model_class()(**data_copy)
            
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def _update_partial(self, data: Dict[str, Any]) -> T:
        """기존 레코드 부분 업데이트"""
        async with PGSessionLocal() as session:
            record_id = data.pop("id")
            
            # 빈 데이터가 아닌 경우에만 업데이트
            if data:
                # 부분 업데이트 실행
                stmt = update(self.model_class()).where(
                    self.model_class().id == record_id
                ).values(**data)
                await session.execute(stmt)
                await session.commit()
            
            # 업데이트된 레코드 조회 후 반환
            result = await session.execute(
                select(self.model_class()).where(self.model_class().id == record_id)
            )
            return result.scalar_one()
    
    async def find_by_id(self, id: int) -> Optional[T]:
        """ID로 레코드 조회"""
        async with PGSessionLocal() as session:
            result = await session.execute(
                select(self.model_class()).where(self.model_class().id == id)
            )
            return result.scalar_one_or_none()
    
    async def delete(self, id: int) -> None:
        """ID로 레코드 삭제"""
        async with PGSessionLocal() as session:
            instance = await self.find_by_id(id)
            if instance:
                await session.delete(instance)
                await session.commit()
            