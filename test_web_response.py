import requests

url = "https://www.sikkimtourism.gov.in/"

response = requests.get(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
    },
    timeout=30
)

print("STATUS CODE:", response.status_code)
print("CONTENT TYPE:", response.headers.get("content-type"))
print("HTML LENGTH:", len(response.text))

print("\n===== FIRST 3000 CHARACTERS =====\n")
print(response.text[:3000])