# filename: task1_hello.py
# Description: Task 1 - Simple test of Nebius Chat Completions API.

import os
import httpx
from dotenv import load_dotenv

# 1. Load environment variables from the .env file
load_dotenv()
api_key = os.getenv("NEBIUS_API_KEY")

if not api_key:
    raise ValueError("NEBIUS_API_KEY not found in .env file or environment variables.")

# 2. Define API constants and request details
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"
NEBIUS_MODEL = "openai/gpt-oss-120b"  # Inexpensive model for testing

url = f"{NEBIUS_BASE_URL}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": NEBIUS_MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Hello! Can you tell me a short fact about mitochondria?",
        },
    ],
    "max_tokens": 50,
    "temperature": 0.7,
}

# 3. Make the API request
print(f"Sending request to Nebius API endpoint: {url}...")
try:
    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

    # 4. Print the results
    print(f"Status Code: {response.status_code}")
    print("\n--- Full JSON Response ---")
    print(response.json())  # Print the entire JSON response

except httpx.HTTPStatusError as e:
    print(f"HTTP Error occurred: {e.response.status_code} - {e.response.text}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

# Sample output
# {
#     "id": "chatcmpl-4e2d1dffeadc47e0ba34c8f0db4d8259",
#     "choices": [
#         {
#             "finish_reason": "length",
#             "index": 0,
#             "logprobs": None,
#             "message": {
#                 "content": "Sure! Mitochondria are often called the “powerhouses of the",
#                 "refusal": None,
#                 "role": "assistant",
#                 "annotations": None,
#                 "audio": None,
#                 "function_call": None,
#                 "tool_calls": [],
#                 "reasoning_content": 'User asks: "Hello! Can you tell me a short fact about mitochondria?" This is allowed. Provide short fact.',
#             },
#             "stop_reason": None,
#             "token_ids": None,
#         }
#     ],
#     "created": 1760979321,
#     "model": "openai/gpt-oss-120b",
#     "object": "chat.completion",
#     "service_tier": None,
#     "system_fingerprint": None,
#     "usage": {
#         "completion_tokens": 50,
#         "prompt_tokens": 94,
#         "total_tokens": 144,
#         "completion_tokens_details": None,
#         "prompt_tokens_details": None,
#     },
#     "prompt_logprobs": None,
#     "prompt_token_ids": None,
#     "kv_transfer_params": None,
# }
