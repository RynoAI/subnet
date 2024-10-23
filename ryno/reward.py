# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
from __future__ import annotations
from transformers import logging as hf_logging

hf_logging.set_verbosity_error()

import re
import io
import torch
import asyncio
import aiohttp
import traceback
import numpy as np
from numpy.linalg import norm
import bittensor as bt
from ryno import utils
from PIL import Image
from scipy.spatial.distance import cosine
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import CLIPProcessor, CLIPModel


# ==== TEXT ====

def calculate_text_similarity(text1: str, text2: str):
    try:
        text1 = str(text1).lower()
        text2 = str(text2).lower()
        # Initialize the TF-IDF Vectorizer
        vectorizer = TfidfVectorizer()

        # Vectorize the texts
        tfidf_matrix = vectorizer.fit_transform([text1, text2])

        # Calculate the Cosine Similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        return similarity
    except Exception as e:
        bt.logging.error(f"Error in calculate_text_similarity: {traceback.format_exc()}")
        raise


async def api_score(api_answer: str, response: str, weight: float, temperature: float, provider: str) -> float:
    try:
        if api_answer is None or response is None:
            return 0
        loop = asyncio.get_running_loop()
        similarity = await loop.run_in_executor(None, calculate_text_similarity, api_answer, response)

        words_in_response = len(response.split())
        words_in_api = len(api_answer.split())

        word_count_over_threshold = words_in_api * 1.4
        word_count_under_threshold = words_in_api * 0.50

        # Check if the word count of the response is within the thresholds
        if words_in_response <= word_count_over_threshold and words_in_response >= word_count_under_threshold:
            score = weight * similarity
        else:
            score = 0

        return score
    except Exception as e:
        bt.logging.error(f"Exception in api_score: {traceback.format_exc()}")


# ==== IMAGES =====

# Load the CLIP model and processor
model = CLIPModel.from_pretrained("lucataco/animate-diff")
processor = CLIPProcessor.from_pretrained("lucataco/animate-diff")

# Could also verify the date from the url
url_regex = (
    r'https://(?:oaidalleapiprodscus|dalleprodsec)\.blob\.core\.windows\.net/private/org-[\w-]+/'
    r'user-[\w-]+/img-[\w-]+\.(?:png|jpg)\?'
    r'st=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&'
    r'se=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&'
    r'(?:sp=\w+&)?'
    r'sv=\d{4}-\d{2}-\d{2}&'
    r'sr=\w+&'
    r'rscd=\w+&'
    r'rsct=\w+/[\w-]+&'
    r'skoid=[\w-]+&'
    r'sktid=[\w-]+&'
    r'skt=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&'
    r'ske=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&'
    r'sks=\w+&'
    r'skv=\d{4}-\d{2}-\d{2}&'
    r'sig=[\w/%+=]+'
)


