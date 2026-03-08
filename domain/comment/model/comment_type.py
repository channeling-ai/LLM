from enum import Enum


class CommentType(str, Enum):
    ADVICE_OPINION = 'ADVICE_OPINION'
    NEGATIVE = 'NEGATIVE'
    NEUTRAL = 'NEUTRAL'
    POSITIVE = 'POSITIVE'

    @property
    def label(self) -> str:
        labels = {
            CommentType.POSITIVE: "긍정",
            CommentType.NEGATIVE: "부정",
            CommentType.NEUTRAL: "중립",
            CommentType.ADVICE_OPINION: "조언 및 의견",
        }
        return labels[self]

    @staticmethod
    def from_emotion_code(code: int) -> "CommentType":
        mapping = {
            1: CommentType.POSITIVE,
            2: CommentType.NEGATIVE,
            3: CommentType.NEUTRAL,
            4: CommentType.ADVICE_OPINION
        }
        return mapping.get(code, CommentType.NEUTRAL)  # 기본값 NEUTRAL
