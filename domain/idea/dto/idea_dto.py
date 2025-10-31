from pydantic import BaseModel

from core.enums.video_category import VideoCategory


class IdeaRequest(BaseModel):
    channel_id: int| None = None
    video_type: str| None = None
    keyword: str| None = None
    detail: str| None = None

class PopularRequest(BaseModel):
    category: VideoCategory