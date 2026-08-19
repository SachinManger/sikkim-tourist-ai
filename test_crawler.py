from crawler.web import crawl


seed_url = "https://www.sikkimtourism.gov.in/"

pages = crawl(
    seed_url=seed_url,
    max_pages=3,
    timeout=30
)

print("\n==============================")
print("REAL CRAWLER TEST")
print("==============================")

print("Total pages collected:", len(pages))

for number, page in enumerate(pages, start=1):

    print("\n------------------------------")
    print(f"PAGE {number}")
    print("------------------------------")

    print("URL:")
    print(page["url"])

    print("\nTITLE:")
    print(page["title"])

    print("\nTEXT LENGTH:")
    print(len(page["text"]))

    print("\nTEXT PREVIEW:")
    print(page["text"][:1500])

    print("\nLINKS FOUND:")
    print(len(page["links"]))

print("\n==============================")
print("REAL CRAWLER TEST FINISHED")
print("==============================")