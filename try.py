payloaddict = {
    "messages": [
        {"role": "system", "content": "Ur a meowy assistant"},
        {"role": "user", "content": "hiii how are u?"},
    ]
}
import requests
print(requests.post("https://ai.leolevd.dev/api/v1/chat/completions", json=payloaddict).json())