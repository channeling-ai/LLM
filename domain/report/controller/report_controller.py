
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from core.config.kafka_config import KafkaConfig
from core.kafka.kafka_broker import kafka_broker
from core.kafka.message import Message
from core.kafka.message import Step
from domain.channel.repository.channel_repository import ChannelRepository
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.repository.report_repository import ReportRepository
from domain.report.service.report_producer import ReportProducer
from domain.report.service.report_service import ReportService
from domain.task.model.task import Status
from domain.task.repository.task_repository import TaskRepository
from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service_impl import RagServiceImpl
from response.api_response import ApiResponse
from response.code.status.error_status import ErrorStatus
from response.code.status.success_status import SuccessStatus


# Request Body Model
class CreateReportRequest(BaseModel):
    googleAccessToken: str

router = APIRouter(prefix="/reports", tags=["reports"])


report_repository = ReportRepository()
task_repository = TaskRepository()
kafka_config = KafkaConfig()
report_producer = ReportProducer(kafka_broker, kafka_config)

rag_service = RagServiceImpl()
logger = logging.getLogger(__name__)
video_repository = VideoRepository()
channel_repository = ChannelRepository()
idea_repository = IdeaRepository()

@router.post("/v1")
async def create_report(video_id: int, request: CreateReportRequest):
    """
    리포트 생성을 시작합니다.
    parameters:
        video_id: int - 리포트에 대한 영상 ID
        request: CreateReportRequest - Google Access Token을 포함한 요청 body
    returns:
        task_id: int
    """
    # Google Access Token 로깅 (디버깅용)
    logger.info(f"Received Google Access Token: {request.googleAccessToken[:20]}...")  # 토큰의 일부만 로깅
    
    # report 생성
    report_data = {"video_id": video_id}
    report = await report_repository.save(data=report_data)
    print(f"Report created with ID: {report.id}")
    
    # task 생성
    task_data = {
        "report_id": report.id,
        "overview_status": Status.PENDING,
        "analysis_status": Status.PENDING,
        "idea_status": Status.COMPLETED
        }
    task = await task_repository.save(data=task_data)
    print(f"Task created with ID: {task.id}")

    # 메시지 생성
    overview_message= Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.overview,
        google_access_token=request.googleAccessToken
    )

    analysis_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.analysis,
        google_access_token=request.googleAccessToken
    )

    # 메시지 발행
    await report_producer.send_message("overview-topic", overview_message)
    await report_producer.send_message("analysis-topic", analysis_message)

    return ApiResponse.on_success(SuccessStatus._OK, {"task_id": task.id})


@router.post("/v2")
async def create_report_v2(video_id: int, request: CreateReportRequest):
    """
    리포트 생성을 시작합니다. (V2 - 벡터 저장 없이)
    parameters:
        video_id: int - 리포트에 대한 영상 ID
        request: CreateReportRequest - Google Access Token을 포함한 요청 body
    returns:
        task_id: int
    """
    # Google Access Token 로깅 (디버깅용)
    logger.info(f"[V2] Received Google Access Token: {request.googleAccessToken[:20]}...")
    
    # report 생성
    report_data = {"video_id": video_id}
    report = await report_repository.save(data=report_data)
    logger.info(f"[V2] Report created with ID: {report.id}")
    
    # task 생성
    task_data = {
        "report_id": report.id,
        "overview_status": Status.PENDING,
        "analysis_status": Status.PENDING,
        "idea_status": Status.COMPLETED
        }
    task = await task_repository.save(data=task_data)
    logger.info(f"[V2] Task created with ID: {task.id}")

    # 메시지 생성 (skip_vector_save=True 추가)
    overview_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.overview,
        google_access_token=request.googleAccessToken,
        skip_vector_save=True
    )

    analysis_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.analysis,
        google_access_token=request.googleAccessToken,
        skip_vector_save=True
    )

    # 메시지 발행 (V2 토픽 사용)
    await report_producer.send_message("overview-topic-v2", overview_message)
    await report_producer.send_message("analysis-topic-v2", analysis_message)

    return ApiResponse.on_success(SuccessStatus._OK, {"task_id": task.id, "version": "v2"})