"""API module"""

from .routes import router
from .schemas import SmartInboxResponse, MessageDetail, SyncResponse

__all__ = ["router", "SmartInboxResponse", "MessageDetail", "SyncResponse"]

