from __future__ import annotations

import aioboto3
import ast
import asyncio
import base64
import io
import json
import math
import httpx
import os
import random
import re
import traceback
from typing import Any, Optional

import bittensor as bt
import boto3
import ryno
import requests
import wandb

from . import client

list_update_lock = asyncio.Lock()


# Function to get API key from environment variables
def get_api_key(service_name, env_var):
    key = os.environ.get(env_var)
    if not key:
        raise ValueError(
            f"{service_name} API key not found in environment variables. "
            f"Go to the respective service's settings to get one. Then set it as {env_var} in your .env"
        )
    return key


pixabay_key = get_api_key("Pixabay", "PIXABAY_API_KEY")

# Stability API
# stability_key = get_api_key("Stability", "STABILITY_API_KEY")
# stability_api = stability_client.StabilityInference(key=stability_key, verbose=True)

# Anthropic
anthropic_key = get_api_key("Anthropic", "ANTHROPIC_API_KEY")
anthropic_client = AsyncAnthropic()
anthropic_client.api_key = anthropic_key

# Google
google_key = get_api_key("Google", "GOOGLE_API_KEY")
genai.configure(api_key=google_key)

# Anthropic Bedrock
anthropic_bedrock_client = AsyncAnthropicBedrock()

# Groq
groq_key = get_api_key("Groq", "GROQ_API_KEY")
groq_client = AsyncGroq()
groq_client.api_key = groq_key

# AWS Bedrock
bedrock_client_parameters = {
    "service_name": 'bedrock-runtime',
    "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY"),
    "aws_secret_access_key": os.environ.get("AWS_SECRET_KEY"),
    "region_name": "us-east-1"
}


def validate_state(data):
    expected_structure = {
        "text": {"themes": list, "questions": list, "theme_counter": int, "question_counter": int},
        "images": {"themes": list, "questions": list, "theme_counter": int, "question_counter": int},
    }

    def check_subdict(subdict, expected):
        if not isinstance(subdict, dict):
            return False
        for key, expected_type in expected.items():
            if key not in subdict or not isinstance(subdict[key], expected_type):
                return False
        return True

    def check_list_of_dicts(lst):
        if not isinstance(lst, list):
            return False
        for item in lst:
            if not isinstance(item, dict):
                return False
        return True

    if not isinstance(data, dict):
        return False
    for key, expected_subdict in expected_structure.items():
        if key not in data or not check_subdict(data[key], expected_subdict):
            return False
        if key == "text" and not check_list_of_dicts(data[key]["questions"]):
            return False

    return True


def load_state_from_file(filename: str):
    load_success = False
    state_is_valid = False

    # Check if the file exists
    if os.path.exists(filename):
        with open(filename, "r") as file:
            try:
                # Attempt to load JSON from the file
                bt.logging.debug("loaded previous state")
                state = json.load(file)
                state_is_valid = validate_state(state)
                if not state_is_valid:
                    raise Exception("State is invalid")
                load_success = True  # Set flag to true as the operation was successful
                return state
            except Exception as e:  # Catch specific exceptions for better error handling
                bt.logging.error(f"error loading state, deleting and resetting it. Error: {e}")
                os.remove(filename)  # Delete if error

    # If the file does not exist or there was an error
    if not load_success or not state_is_valid:
        bt.logging.debug("initialized new global state")
        # Return the default state structure
        return {
            "text": {"themes": [], "questions": [], "theme_counter": 0, "question_counter": 0},
            "images": {"themes": [], "questions": [], "theme_counter": 0, "question_counter": 0},
        }


state = None


def get_state(path):
    global state
    if not state:
        state = load_state_from_file(path)
    return state


def save_state_to_file(state, filename="state.json"):
    with open(filename, "w") as file:
        bt.logging.success(f"saved global state to {filename}")
        json.dump(state, file)


def fetch_random_image_urls(num_images):
    try:
        url = f"https://pixabay.com/api/?key={pixabay_key}&per_page={num_images}&order=popular"
        response = requests.get(url)
        response.raise_for_status()
        images = response.json().get('hits', [])
        return [image['webformatURL'] for image in images]
    except Exception as e:
        bt.logging.error(f"Error fetching random images: {e}")
        return []


async def update_counters_and_get_new_list(category, item_type, num_questions_needed, vision, theme=None):
    async def get_items(category, item_type, theme=None):
        if item_type == "themes":
            if category == "images":
                return ryno.IMAGE_THEMES
            return ryno.INSTRUCT_DEFAULT_THEMES
        else:
            # Never fail here, retry until valid list is found
            while True:
                theme = await get_random_theme(category)
                if theme is not None:
                    return await get_list(f"{category}_questions", num_questions_needed, theme)

    async def get_random_theme(category):
        themes = state[category]["themes"]
        if not themes:
            themes = await get_items(category, "themes")
            state[category]["themes"] = themes
        return random.choice(themes)

    async def get_item_from_list(items, vision):
        if vision:
            return items.pop() if items else None
        else:
            for i, itm in enumerate(items):
                if 'image' not in itm:
                    return items.pop(i)
            return None

    list_type = f"{category}_{item_type}"

    async with list_update_lock:
        items = state[category][item_type]

        bt.logging.trace(f"Queue for {list_type}: {len(items) if items else 0} items")

        item = await get_item_from_list(items, vision)

        if not item:
            bt.logging.trace(f"Item not founded in items: {items}. Calling get_items!")
            items = await get_items(category, item_type, theme)
            bt.logging.trace(f"Items generated: {items}")
            state[category][item_type] = items
            bt.logging.trace(f"Fetched new list for {list_type}, containing {len(items)} items")

            item = await get_item_from_list(items, vision)

        if not items:
            state[category][item_type] = []

    return item


async def get_question(category, num_questions_needed, vision=False):
    if category not in ["text", "images"]:
        raise ValueError("Invalid category. Must be 'text' or 'images'.")

    question = await update_counters_and_get_new_list(category, "questions", num_questions_needed, vision)
    return question


def preprocess_string(text: str) -> str:
    processed_text = text.replace("\t", "")
    placeholder = "___SINGLE_QUOTE___"
    processed_text = re.sub(r"(?<=\w)'(?=\w)", placeholder, processed_text)
    processed_text = processed_text.replace("'", '"').replace(placeholder, "'")

    # First, remove all comments, ending at the next quote
    no_comments_text = ""
    i = 0
    in_comment = False
    while i < len(processed_text):
        if processed_text[i] == "#":
            in_comment = True
        elif processed_text[i] == '"' and in_comment:
            in_comment = False
            no_comments_text += processed_text[i]  # Keep the quote that ends the comment
            i += 1
            continue
        if not in_comment:
            no_comments_text += processed_text[i]
        i += 1

    # Now process the text without comments for quotes
    cleaned_text = []
    inside_quotes = False
    found_first_bracket = False

    i = 0
    while i < len(no_comments_text):
        char = no_comments_text[i]

        if not found_first_bracket:
            if char == "[":
                found_first_bracket = True
            cleaned_text.append(char)
            i += 1
            continue

        if char == '"':
            # Look for preceding comma or bracket, skipping spaces
            preceding_char_index = i - 1
            found_comma_or_bracket = False

            while preceding_char_index >= 0:
                if no_comments_text[preceding_char_index] in "[,":  # Check for comma or opening bracket
                    found_comma_or_bracket = True
                    break
                if no_comments_text[preceding_char_index] not in " \n":  # Ignore spaces and new lines
                    break
                preceding_char_index -= 1

            following_char_index = i + 1
            while following_char_index < len(no_comments_text) and no_comments_text[following_char_index] in " \n":
                following_char_index += 1

            if found_comma_or_bracket or (
                    following_char_index < len(no_comments_text) and no_comments_text[following_char_index] in "],"
            ):
                inside_quotes = not inside_quotes
            else:
                i += 1
                continue  # Skip this quote

            cleaned_text.append(char)
            i += 1
            continue

        if char == " ":
            # Skip spaces if not inside quotes and if the space is not between words
            if not inside_quotes and (i == 0 or no_comments_text[i - 1] in " ,[" or no_comments_text[i + 1] in " ,]"):
                i += 1
                continue

        cleaned_text.append(char)
        i += 1

    cleaned_str = "".join(cleaned_text)
    cleaned_str = re.sub(r"\[\s+", "[", cleaned_str)
    cleaned_str = re.sub(r"\s+\]", "]", cleaned_str)
    cleaned_str = re.sub(r"\s*,\s*", ", ", cleaned_str)  # Ensure single space after commas

    start, end = cleaned_str.find("["), cleaned_str.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned_str = cleaned_str[start: end + 1]

    return cleaned_str


def convert_to_list(text: str) -> list[str]:
    pattern = r"\d+\.\s"
    items = [item.strip() for item in re.split(pattern, text) if item]
    return items


def extract_python_list(text: str):
    try:
        if re.match(r"\d+\.\s", text):
            return convert_to_list(text)

        text = preprocess_string(text)
        bt.logging.trace(f"Postprocessed text = {text}")

        # Extracting list enclosed in square brackets
        match = re.search(r'\[((?:[^][]|"(?:\\.|[^"\\])*")*)\]', text, re.DOTALL)
        if match:
            list_str = match.group(1)

            # Using ast.literal_eval to safely evaluate the string as a list
            evaluated = ast.literal_eval("[" + list_str + "]")
            if isinstance(evaluated, list):
                return evaluated

    except Exception as e:
        bt.logging.error(f"found double quotes in list, trying again")

    return None




# Github unauthorized rate limit of requests per hour is 60. Authorized is 5000.
def get_version(line_number: int = 22) -> Optional[str]:
    url = "https://api.github.com/repos/RynoAI/subnet/contents/ryno/__init__.py"
    response = requests.get(url, timeout=10)
    if not response.ok:
        bt.logging.error("github api call failed")
        return None

    content = response.json()["content"]
    decoded_content = base64.b64decode(content).decode("utf-8")
    lines = decoded_content.split("\n")
    if line_number > len(lines):
        raise Exception("Line number exceeds file length")

    version_line = lines[line_number - 1]
    version_match = re.search(r'__version__ = "(.*?)"', version_line)
    if not version_match:
        raise Exception("Version information not found in the specified line")

    return version_match.group(1)


def send_discord_alert(message, webhook_url):
    data = {"content": f"@everyone {message}", "username": "Subnet 224 Updates"}
    try:
        response = requests.post(webhook_url, json=data, timeout=10)
        if response.status_code == 204:
            print("Discord alert sent successfully!")
        else:
            print(f"Failed to send Discord alert. Status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")
