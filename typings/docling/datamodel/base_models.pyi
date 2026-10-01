from enum import Enum

class InputFormat(Enum):
    PDF = "pdf"

class ConversionStatus(Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILURE = "failure"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    SKIPPED = "skipped"
