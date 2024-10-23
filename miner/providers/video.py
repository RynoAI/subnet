import asyncio
import bittensor as bt
from starlette.types import Send

from .base import Provider
from miner.config import config
from miner.error_handler import error_handler


class VideoModel(Provider):
    def __init__(self, synapse):
        super().__init__(synapse)

    async def video_service(self, synapse):
        video_data = {}
        # TODO: Generate video using models
        # meta = ...
        # video_url = meta.data[0].url
        # video_data["url"] = video_url
        # bt.logging.info(f"returning video response of {video_url}")
        # synapse.completion = video_data
        # return synapse

   

  