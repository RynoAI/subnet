from typing import Union

from miner.services.video import VideoService
from .check_status import IsAliveService
from .capacity import CapacityService

ALL_SERVICE_TYPE = Union[VideoService, IsAliveService, CapacityService]
__all__ = [VideoService, CapacityService, ALL_SERVICE_TYPE]
