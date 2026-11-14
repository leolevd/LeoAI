import json
import requests
from pathlib import Path

# Example OpenAI-compatible chat-completions payload:
# sample_payload = {
#     "model": "gpt-4o-mini",
#     "messages": [
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "Hello!"},
#     ],
# }
# forward_openai_request(sample_payload, "provider_name")

def construct_payload(payload: dict, model: str):
    payload["model"] = model
    return payload


def forward_openai_request(payload: dict, name: str) -> dict | None:
    """Pass an OpenAI-compatible chat-completions payload."""
    print(f"Forwarding request to {name}...")
    config_path = Path(__file__).with_name("config.json")
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
        url = config[name]["base"]
        key = config[name]["key"]
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payloadfinal = construct_payload(payload, config[name]["model"])
    response = requests.post(url, headers=headers, json=payloadfinal, timeout=60)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    return response.json()
