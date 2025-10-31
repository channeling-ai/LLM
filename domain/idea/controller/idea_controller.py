import logging

from fastapi import APIRouter

from domain.idea.dto.idea_dto import IdeaRequest, PopularRequest
from domain.idea.service.idea_service import IdeaService
from external.rag.rag_service_impl import RagServiceImpl
from response.api_response import ApiResponse
from response.code.status.success_status import SuccessStatus

router = APIRouter(
    prefix="/ideas",
    tags=["ideas"]
)

logger = logging.getLogger(__name__)

idea_service = IdeaService()
rag_service = RagServiceImpl()

# 아이디어 생성
@router.post("")
async def create_idea(req: IdeaRequest):
    try:
        ideas = await idea_service.create_idea(req)
    except Exception as e:
        logger.error(f"아이디어 생성 프로세스 실패: {e!r}")
        raise

    return ApiResponse.on_success(SuccessStatus._OK, ideas)

# 인기 영상 호출
@router.post("/popular")
async def get_popular_ideas(req: PopularRequest):
    try:
        popular_ideas = await rag_service.get_popular_videos(req.category)
    except Exception as e:
        logger.error(f"인기 영상 호출 프로세스 실패: {e!r}")
        raise

    return ApiResponse.on_success(SuccessStatus._OK, "인기 영상 호출 성공")