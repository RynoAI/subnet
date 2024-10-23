from abc import abstractmethod
import asyncio
from collections import defaultdict

from ryno import StreamPrompting
from rich.table import Table
from rich.console import Console

import random
from typing import Tuple

import bittensor as bt

from ryno.metaclasses import ValidatorRegistryMeta
from validators.utils import error_handler, get_bandwidth

dataset = None


class BaseValidator(metaclass=ValidatorRegistryMeta):
    def __init__(self, config, metagraph):
        self.config = config
        self.metagraph = metagraph
        self.dendrite = config.dendrite
        self.wallet = config.wallet
        self.timeout = config.async_time_out
        self.streaming = False
        self.provider = None
        self.model = None
        self.seed = random.randint(1111, 9999)
        self.uid_to_questions = dict()
        self.available_uids = []
        self.num_samples = 100
        self.wandb_data = {}

    async def query_miner(self, metagraph, uid, syn):
        try:
            responses = await self.dendrite([metagraph.axons[uid]], syn, deserialize=False, timeout=self.timeout,
                                            streaming=self.streaming)
            return await self.handle_response(uid, responses)

        except Exception as e:
            bt.logging.error(f"Exception during query for uid {uid}: {e}")
            return uid, None

    @abstractmethod
    def select_random_provider_and_model(self):
        pass

    def get_provider_to_models(self):
        pass

    async def handle_response(self, uid, response) -> Tuple[int, bt.Synapse]:
        if type(response) == list and response:
            response = response[0]
        return uid, response

    @abstractmethod
    async def create_query(self, uid):
        pass

    @abstractmethod
    async def build_wandb_data(self, scores, responses):
        pass

    @abstractmethod
    async def get_answer_task(self, uid, synapse, response):
        pass

    @abstractmethod
    async def get_scoring_task(self, uid, answer, response):
        pass

    @staticmethod
    def get_synapse_from_json(data):
        pass

    @error_handler
    async def score_responses(self, uid_to_query_resps, uid_to_capacity):
        answering_tasks = []
        scoring_tasks = []
        scored_response = []

        for uid, query_resp in uid_to_query_resps:
            task = self.get_answer_task(uid, query_resp.get("query"), query_resp.get("response"))
            answering_tasks.append((uid, task))

        answers_results = await asyncio.gather(*[task for _, task in answering_tasks])

        for (uid, query_resp), answer in zip(uid_to_query_resps, answers_results):
            task = self.get_scoring_task(uid, answer, query_resp.get("response"))
            scoring_tasks.append((uid, task))

        # Await all scoring tasks
        scored_responses = await asyncio.gather(*[task for _, task in scoring_tasks])
        average_score = sum(0 if score is None else score for score in scored_responses) / len(
            scored_responses) if scored_responses else 0
        bt.logging.debug(f"scored responses = {scored_responses}, average score = {average_score}")

        uid_scores_dict = self.get_uid_to_scores_dict(uid_to_query_resps, scored_responses, uid_to_capacity)

        bt.logging.trace("score_responses process completed.")

        return uid_scores_dict, scored_response, uid_to_query_resps

    def get_uid_to_scores_dict(self, uid_to_query_resps, scored_responses: tuple[float], uid_to_capacity):
        uid_provider_model_scores_dict = defaultdict(list)

        # collect all scores per each uid, provider, model
        for (uid, query_resp), scored_response in zip(uid_to_query_resps, scored_responses):
            synapse: StreamPrompting = query_resp.get('query')
            provider = synapse.provider
            model = synapse.model
            if scored_response is not None:
                bt.logging.trace(f"scored response is {scored_response} for uid {uid} for provider {provider} "
                                 f"and for model {model}")
                uid_provider_model_scores_dict[f"{uid}::{provider}::{model}"].append((float(scored_response), synapse))
            else:
                uid_provider_model_scores_dict[f"{uid}::{provider}::{model}"].append((0, synapse))

        # get avg score value for each uid, provider, model
        uid_provider_model_scores_avg_dict = {}
        for key, score_syns in uid_provider_model_scores_dict.items():
            if len(score_syns) == 0:
                bt.logging.debug(f"no scores found for this uid {key}")
            scores = [item[0] for item in score_syns]
            syns = [item[1] for item in score_syns]
            avg_score = sum(scores) / len(scores)
            uid_provider_model_scores_avg_dict[key] = (avg_score, syns)

        # apply weight for each model and calculate score based on weight of models.
        uid_scores_dict = defaultdict(float)
        table_data = [
            ["uid", "provider", "model", 'similarity', 'weight', 'bandwidth', 'weighted_score']
        ]
        for key, avg_score_syns in uid_provider_model_scores_avg_dict.items():
            avg_score, syns = avg_score_syns
            uid = int(str(key).split("::")[0])
            provider = str(key).split("::")[1]
            model = str(key).split("::")[2]
            model_weight = 1
            #if model_weight is None:
            #    bt.logging.debug(f"no weight found for this provider {provider} and model {model}")
            #    model_weight = 0

            band_width = get_bandwidth(uid_to_capacity, uid, provider, model)

            if band_width is None:
                bt.logging.debug(f"no band_width found for this uid {uid}")
                band_width = 1
            weighted_score = avg_score * model_weight * band_width
            uid_scores_dict[uid] += weighted_score
            table_data.append([uid, provider, model, avg_score, model_weight, band_width, weighted_score])
            for syn in syns:
                syn: StreamPrompting
                syn.similarity = avg_score
                syn.score = weighted_score

        self.show_pretty_table_score(table_data)

        if not len(uid_scores_dict):
            validator_type = self.__class__.__name__
            bt.logging.debug(f"{validator_type} scores is {uid_scores_dict}")
        return uid_scores_dict

    @staticmethod
    def show_pretty_table_score(table_data):
        table = Table(title="All Weights")
        header = table_data[0]
        for col in header:
            table.add_column(col)

        rows = table_data[1:]
        rows = sorted(rows, key=lambda x: x[0])
        for row in rows:
            renderable_list = [str(item) for item in row]
            table.add_row(*renderable_list)
        console = Console()
        console.print(table)

    @classmethod
    def get_task_type(cls):
        pass
