#!/usr/bin/env python3
"""
Updated Gemini diagnostic script — tests if retry logic works.
"""

import os
import sys
import time
from google import genai
from google.genai import types

# Load API Key (simplified logic)
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

print(f"Testing model: {model}")
client = genai.Client(api_key=api_key)

# The same logic as in llm_parser.py (the function calling part)
extract_func = types.FunctionDeclaration(
    name="extract_storage_constraints",
    description="Extract structured storage requirements",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "primary_goal": types.Schema(type=types.Type.STRING),
            "access_pattern": types.Schema(type=types.Type.STRING),
        },
        required=["primary_goal", "access_pattern"],
    ),
)
tool = types.Tool(function_declarations=[extract_func])

def test_call():
    # Retry with exponential backoff (logic copied from llm_parser.py)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}...")
            response = client.models.generate_content(
                model=model,
                contents="Store backup...",
                config=types.GenerateContentConfig(
                    system_instruction="Extract constraints only.",
                    tools=[tool],
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(mode="ANY")
                    ),
                ),
            )
            print("Success!")
            return
        except Exception as exc:
            exc_str = str(exc)
            if "503" in exc_str or "UNAVAILABLE" in exc_str:
                wait = 2 ** attempt
                print(f"Got 503 error, retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise

test_call()
