import base64
import bittensor as bt
from functools import partial
import httpx
from starlette.types import Send
from abc import abstractmethod

from ryno.protocol import Embeddings, VideoResponse, IsAlive
from ryno import VIDEO_SYNAPSE_TYPE
from ryno.metaclasses import ProviderRegistryMeta
from miner.error_handler import error_handler

class Provider(metaclass=ProviderRegistryMeta):
    def __init__(self, synapse: VIDEO_SYNAPSE_TYPE):
        self.model = synapse.model
        self.uid = synapse.uid
        self.timeout = synapse.timeout
        if type(synapse) is VideoResponse:
            self.completion = synapse.completion
            self.messages = synapse.messages
            self.provider = synapse.provider
            self.seed = synapse.seed
            self.samples = synapse.samples
            self.cfg_scale = synapse.cfg_scale
            self.sampler = synapse.sampler
            self.steps = synapse.steps
            self.style = synapse.style
            self.size = synapse.size
            self.height = synapse.height
            self.width = synapse.width
            self.quality = synapse.quality
            self.required_hash_fields = synapse.required_hash_fields
        elif type(synapse) is IsAlive:
            self.answer = synapse.answer
            self.completion = synapse.completion
        else:
            bt.logging.error(f"unknown synapse {type(synapse)}")

    @error_handler
    def prompt_service(self, synapse: bt.StreamingSynapse):
        token_streamer = partial(self._prompt, synapse)
        return synapse.create_streaming_response(token_streamer)

    @abstractmethod
    async def _prompt(self, synapse, send: Send):
        pass

    @abstractmethod
    async def image_service(self, synapse: bt.Synapse):
        pass

    @abstractmethod
    async def embeddings_service(self, synapse: bt.Synapse):
        pass
