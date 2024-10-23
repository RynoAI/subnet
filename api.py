import bittensor as bt
import pydantic
from enum import Enum
from typing import AsyncIterator, Dict, List, Literal, Optional
from starlette.responses import StreamingResponse
import asyncio
import traceback
import random

# TODO
class VideoGeneration(bt.StreamingSynapse):
    pass

async def query_miner(dendrite, axon_to_use, synapse, timeout, streaming):
    try:
        print(f"calling vali axon {axon_to_use} to miner uid {synapse.uid} for query {synapse.messages}")
        responses = dendrite.query(
            axons=[axon_to_use],
            synapse=synapse,
            deserialize=False,
            timeout=timeout,
            streaming=streaming,
        )
        return await handle_response(responses)
    except Exception as e:
        print(f"Exception during query: {traceback.format_exc()}")
        return None

async def handle_response(responses):
    full_response = ""
    try:
        for resp in responses:
            async for chunk in resp:
                if isinstance(chunk, str):
                    full_response += chunk
                    print(chunk, end='', flush=True)
                else:
                    print(f"\n\nFinal synapse: {chunk}\n")
    except Exception as e:
        print(f"Error processing response for uid {e}")
    return full_response

async def main():
    print("synching metagraph, this takes way too long.........")
    meta = bt.metagraph( netuid=224, network="test" )
    print("metagraph synched!")

    # This needs to be your validator wallet that is running your subnet 224 validator
    wallet = bt.wallet( name="validator", hotkey="default" )
    dendrite = bt.dendrite( wallet=wallet )
    vali_uid = meta.hotkeys.index( wallet.hotkey.ss58_address)
    axon_to_use = meta.axons[vali_uid]

    # This is the question to send your validator to send your miner.
    prompt = "video of a rhino in the jungle"

    # You can edit this to pick a specific miner uid, just change miner_uid to the uid that you desire.
    # Currently, it just picks a random miner form the top 100 uids.
    # top_miners_to_use = 100
    # top_miner_uids = meta.I.argsort(descending=True)[:top_miners_to_use]
    # miner_uid = random.choice(top_miner_uids)
    miner_uid = 3

   # TODO

if __name__ == "__main__":
    asyncio.run(main())