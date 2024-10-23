from typing import AsyncIterator, Dict, List, Optional, Union
import bittensor as bt
import pydantic
from starlette.responses import StreamingResponse
import sys


class IsAlive(bt.Synapse):
    answer: Optional[str] = None
    completion: str = pydantic.Field(
        "",
        title="Completion",
        description="Completion status of the current StreamPrompting object. "
                    "This attribute is mutable and can be updated.",
    )


class Bandwidth(bt.Synapse):
    bandwidth_rpm: Optional[Dict[str, dict]] = None

class VideoResponse(bt.Synapse):
    """ A class to represent the response for an video-related request. """

    completion: Optional[Dict] = pydantic.Field(
        None,
        title="Completion",
        description="The completion data of the video response."
    )

    messages: str = pydantic.Field(
        ...,
        title="Messages",
        description="Messages related to the video response."
    )

    provider: str = pydantic.Field(
        default="lucataco",
        title="Provider",
        description="The provider to use when calling for your response."
    )

    seed: int = pydantic.Field(
        default=1234,
        title="Seed",
        description="The seed that which to generate the video with"
    )

    samples: int = pydantic.Field(
        default=1,
        title="Samples",
        description="The number of samples to generate"
    )

    steps: int = pydantic.Field(
        default=30,
        title="Seed",
        description="The steps to take in generating the video"
    )

    model: str = pydantic.Field(
        default="animate-diff",
        title="Model",
        description="The model used for generating the video."
    )

    style: str = pydantic.Field(
        default="",
        title="Style",
        description="The style of the video."
    )

    size: str = pydantic.Field(
        default="1024x1024",
        title="The size of the video.",
        description="The size of the video."
    )

    height: int = pydantic.Field(
        default=1024,
        title="Height.",
        description="height"
    )

    width: int = pydantic.Field(
        default=1024,
        title="Width.",
        description="width"
    )

    quality: str = pydantic.Field(
        default="standard",
        title="Quality",
        description="The quality of the video."
    )

    uid: int = pydantic.Field(
        default=3,
        title="uid",
        description="The UID to send the synapse to",
    )

    timeout: int = pydantic.Field(
        default=60,
        title="timeout",
        description="The timeout for the dendrite of the synapse",
    )

    required_hash_fields: List[str] = pydantic.Field(
        ["messages"],
        title="Required Hash Fields",
        description="A list of fields required for the hash."
    )

    process_time: int = pydantic.Field(
        default=9999,
        title="process time",
        description="processed time of querying dendrite.",
    )
    task_id: str = pydantic.Field(
        default="9999"
    )

    def deserialize(self) -> Optional[Dict]:
        """ Deserialize the completion data of the video response. """
        return self.completion
