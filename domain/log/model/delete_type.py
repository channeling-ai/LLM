from enum import Enum


class DeleteType(str, Enum):
    USER_REQUEST = "USER_REQUEST"
    REPLACED = "REPLACED"