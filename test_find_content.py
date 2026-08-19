import requests

url = "https://www.sikkimtourism.gov.in/"

response = requests.get(
    url,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
        )
    },
    timeout=30
)

html = response.text

keywords = [
    "Sikkim",
    "Tourism",
    "Gangtok",
    "Pelling",
    "Tsomgo",
    "Kanchenjunga",
    "destination",
    "tourist"
]

print("HTML length:", len(html))

print("\n===== KEYWORD SEARCH =====")

for keyword in keywords:
    count = html.lower().count(keyword.lower())
    print(f"{keyword}: {count}")

print("\n===== SEARCHING FOR PELLING =====")

position = html.lower().find("pelling")

if position >= 0:
    start = max(0, position - 1000)
    end = min(len(html), position + 2000)

    print(html[start:end])
else:
    print("Pelling was not found in the raw HTML.")