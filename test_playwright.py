from playwright.sync_api import sync_playwright


url = "https://www.sikkimtourism.gov.in/"


with sync_playwright() as p:

    print("Starting Chromium...")

    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    )

    print("Opening website...")

    page.goto(
    url,
    wait_until="domcontentloaded",
    timeout=60000
    )
    page.wait_for_timeout(10000)

    print("Page loaded.")

    print("\nPAGE TITLE:")
    print(page.title())

    text = page.locator("body").inner_text()

    print("\nTEXT LENGTH:")
    print(len(text))

    print("\n===== TEXT PREVIEW =====\n")
    print(text[:5000])

    print("\n===== LINK COUNT =====")

    links = page.locator("a").all()

    print(len(links))

    browser.close()

print("\n===== PLAYWRIGHT TEST FINISHED =====")