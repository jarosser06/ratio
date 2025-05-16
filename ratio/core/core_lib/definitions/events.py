
from enum import StrEnum


class FileEventType(StrEnum):
    """
    Enum representing the type of file event.
    """
    CREATED = "created"
    DELETED = "deleted"
    UPDATED = "updated"
    VERSION_CREATED = "version_created"
    VERSION_DELETED = "version_deleted"