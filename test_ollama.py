import requests

url = "http://127.0.0.1:11434/api/generate"

payload = {
    "model": "qwen2.5:7b",
    "prompt": 'Return only JSON: {"test":"ok"}',
    "stream": False
}

print("Sending request to Ollama...")

try:
    r = requests.post(url, json=payload, timeout=120)

    print("STATUS:", r.status_code)
    print("RESPONSE:")
    print(r.text[:2000])

except Exception as e:
    print("ERROR:", repr(e))
