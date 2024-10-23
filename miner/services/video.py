import bittensor as bt
from ryno.protocol import VideoResponse
from typing import Tuple

from .base import BaseService
from ryno import VIDEO_BLACKLIST_STAKE


class VideoService(BaseService):
    def __init__(self, metagraph, blacklist_amt=VIDEO_BLACKLIST_STAKE):
        super().__init__(metagraph, blacklist_amt)

    async def forward_fn(self, synapse: VideoResponse):
        provider = self.get_instance_of_provider(synapse.provider)(synapse)
        bt.logging.info(f"selected video provider is {provider}")
        service = provider.image_service if provider is not None else None
        bt.logging.info("video service is executed.")
        try:
            resp = await service(synapse)
        except Exception as err:
            bt.logging.exception(err)
            return None
        return resp

    def blacklist_fn(self, synapse: VideoResponse) -> Tuple[bool, str]:
        blacklist = self.base_blacklist(synapse)
        bt.logging.info(blacklist[1])
        return blacklist
