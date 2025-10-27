from datetime import datetime
from zoneinfo import ZoneInfo

def get_kst_now() -> datetime:
    """현재 한국 시간(KST)을 반환합니다."""
    return datetime.now(ZoneInfo("Asia/Seoul"))

def get_kst_now_naive() -> datetime:
    """현재 한국 시간(KST)을 timezone 정보 없이 반환합니다.
    PostgreSQL TIMESTAMP 필드에 저장할 때 사용합니다."""
    kst = datetime.now(ZoneInfo("Asia/Seoul"))
    # timezone 정보를 제거하고 KST 시간 값만 유지
    return kst.replace(tzinfo=None)