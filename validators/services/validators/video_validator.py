import asyncio
import random
import wandb

import ryno.reward
from ryno.protocol import VideoResponse
from validators import utils
from validators.utils import error_handler, save_or_get_answer_from_cache
from ryno.utils import get_question
import bittensor as bt


class VideoValidator:
    def __init__(self, config, metagraph=None):
        super().__init__(config, metagraph)
        self.num_uids_to_pick = 30
        self.streaming = False
        self.query_type = "videos"
        self.model = "animate-diff"
        self.weight = .5
        self.provider = "lucataco"
        self.size = "1792x1024"
        self.width = 1024
        self.height = 1024
        self.quality = "standard"
        self.style = ""
        self.steps = 30
        self.wandb_data = {
            "modality": "videos",
            "prompts": {},
            "responses": {},
            "videos": {},
            "scores": {},
            "timestamps": {},
        }

    def select_random_provider_and_model(self):
        # Randomly choose the provider based on specified probabilities
        providers = ["lucataco"] * 1 + ["anotherjesse"] * 10
        self.provider = random.choice(providers)
        self.num_uids_to_pick = 30

        if self.provider == "lucataco":
            self.model = "animate-diff"
        elif self.provider == "anotherjesse":
            self.model = "zeroscope-v2-xl"

    def get_provider_to_models(self):
        return [("lucataco", "animate-diff")]

    async def get_question(self):
        question = await get_question("videos", 1)
        return question

    async def create_query(self, uid, provider=None, model=None) -> bt.Synapse:
        question = await self.get_question()
        syn = VideoResponse(messages=question, model=model, size=self.size, quality=self.quality,
                            style=self.style, provider=provider, seed=self.seed, steps=self.steps)
        bt.logging.info(f"uid = {uid}, syn = {syn}")
        return syn

    def should_i_score(self):
        rand = random.random()
        return rand < 1 / 1

    async def get_scoring_task(self, uid, answer, response: VideoResponse):
        if response is None:
            bt.logging.trace(f"response is None. so return score with 0 for this uid {uid}.")
            return 0
        # TODO
        score = 0
        return score

    @save_or_get_answer_from_cache
    async def get_answer_task(self, uid, synapse: VideoResponse, response):
        return synapse

    @error_handler
    async def build_wandb_data(self, scores, responses):
      # TODO
      pass

    @classmethod
    def get_task_type(cls):
        return VideoResponse.__name__

    @staticmethod
    def get_synapse_from_json(data):
        synapse = VideoResponse.parse_raw(data)
        return synapse