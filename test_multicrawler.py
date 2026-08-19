from crawler.web import crawl


SEED_URL = "https://www.sikkimtourism.gov.in/"
MAX_PAGES = 20


print("\n===================================")
print("SIKKIM TOURIST AI - MULTI PAGE CRAWLER TEST")
print("===================================\n")


# --------------------------------------------------
# STEP 1: START CRAWLER
# --------------------------------------------------

print("[STEP 1] Starting multi-page crawler...\n")


pages = crawl(
    SEED_URL,
    max_pages=MAX_PAGES
)


print(
    f"\n[STEP 1 COMPLETE] "
    f"Pages collected: {len(pages)}"
)


# --------------------------------------------------
# STEP 2: DISPLAY RESULTS
# --------------------------------------------------

print("\n===================================")
print("CRAWL RESULTS")
print("===================================")


for page_number, page in enumerate(
    pages,
    start=1
):

    print("\n-----------------------------------")
    print(
        f"PAGE {page_number}/{len(pages)}"
    )
    print("-----------------------------------")

    print(
        "URL:"
    )

    print(
        page["url"]
    )

    print(
        "\nTITLE:"
    )

    print(
        page["title"]
    )

    print(
        "\nTEXT LENGTH:"
    )

    print(
        len(page["text"])
    )

    # Show first 500 characters
    # of the webpage text.

    print(
        "\nTEXT PREVIEW:"
    )

    print(
        page["text"][:500]
    )


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

print("\n\n===================================")
print("CRAWLER TEST COMPLETE")
print("===================================")

print(
    "Total pages collected:",
    len(pages)
)

print(
    "Maximum pages allowed:",
    MAX_PAGES
)

print(
    "\nCrawler is working successfully."
)