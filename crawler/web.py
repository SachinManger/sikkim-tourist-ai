from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # Playwright is optional on lightweight cloud deployments.
    sync_playwright = None


def normalize_url(url):
    """
    Normalize URL by removing fragments and trailing slash.
    """

    parsed = urlparse(url)

    clean = parsed._replace(
        fragment=""
    ).geturl()

    if clean.endswith("/") and parsed.path != "/":
        clean = clean[:-1]

    return clean


def is_same_domain(base_url, url):
    """
    Allow only URLs belonging to the same website domain.
    """

    base_domain = urlparse(base_url).netloc.lower()
    target_domain = urlparse(url).netloc.lower()

    return target_domain == base_domain


def is_valid_page(url):
    """
    Ignore files that are not normal webpages.
    """

    blocked_extensions = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".zip",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".mp4",
        ".mp3",
    )

    path = urlparse(url).path.lower()

    return not path.endswith(blocked_extensions)


def extract_page(page, url):
    """
    Extract title, visible text and links from a webpage.
    """

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # Give JavaScript applications some time to render.
    page.wait_for_timeout(1500)

    title = page.title()

    text = page.locator("body").inner_text()

    links = page.locator("a").evaluate_all(
        """
        elements => elements.map(a => ({
            href: a.href,
            text: a.innerText
        }))
        """
    )

    discovered_links = []

    for link in links:

        href = link.get("href")

        if not href:
            continue

        absolute_url = urljoin(
            url,
            href
        )

        absolute_url = normalize_url(
            absolute_url
        )

        if not is_valid_page(absolute_url):
            continue

        discovered_links.append(
            absolute_url
        )

    return {
        "url": url,
        "title": title,
        "text": text,
        "links": discovered_links
    }


def extract_page_with_requests(url, timeout=20):
    """Extract a normal HTML page when a browser engine is unavailable."""
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; SikkimTouristAI/1.0; "
                "+https://www.sikkimtourism.gov.in/)"
            )
        },
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else url
    text = "\n".join(
        line.strip()
        for line in soup.get_text("\n").splitlines()
        if line.strip()
    )
    discovered_links = []
    for anchor in soup.find_all("a", href=True):
        absolute_url = normalize_url(urljoin(url, anchor["href"]))
        if is_valid_page(absolute_url):
            discovered_links.append(absolute_url)

    return {
        "url": url,
        "title": title,
        "text": text,
        "links": list(dict.fromkeys(discovered_links)),
    }


def crawl_with_requests(seed_url, max_pages=20):
    """Breadth-first crawler used on free hosts without Chromium."""
    visited = set()
    queue = [normalize_url(seed_url)]
    results = []

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not is_same_domain(seed_url, url):
            continue

        try:
            data = extract_page_with_requests(url)
        except Exception as error:
            print(f"[ERROR] Failed to crawl {url}: {error}")
            continue

        results.append({
            "url": data["url"],
            "title": data["title"],
            "text": data["text"],
        })
        for link in data["links"]:
            if (
                link not in visited
                and link not in queue
                and is_same_domain(seed_url, link)
            ):
                queue.append(link)

    return results


def crawl(
    seed_url,
    max_pages=20
):
    """
    Crawl pages belonging to the same domain.

    The crawler performs breadth-first crawling.
    """

    if sync_playwright is None:
        print("[INFO] Chromium unavailable; using the lightweight HTML crawler.")
        return crawl_with_requests(seed_url, max_pages=max_pages)

    print("[INFO] Starting Chromium...")

    visited = set()
    queue = [normalize_url(seed_url)]
    results = []

    playwright_context = None
    try:
        playwright_context = sync_playwright()
        playwright = playwright_context.__enter__()

        browser = playwright.chromium.launch(
            headless=True
        )
    except Exception as error:
        try:
            if playwright_context is not None:
                playwright_context.__exit__(None, None, None)
        except Exception:
            pass
        print(f"[INFO] Chromium could not start ({error}); using the lightweight HTML crawler.")
        return crawl_with_requests(seed_url, max_pages=max_pages)

    try:
        page = browser.new_page()

        while queue and len(results) < max_pages:

            url = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)

            if not is_same_domain(
                seed_url,
                url
            ):
                continue

            print(
                f"[INFO] Crawling page "
                f"{len(results) + 1}/{max_pages}: "
                f"{url}"
            )

            try:

                data = extract_page(
                    page,
                    url
                )

                text = data["text"]

                print(
                    f"[INFO] Text length: "
                    f"{len(text)}"
                )

                print(
                    f"[INFO] Links found: "
                    f"{len(data['links'])}"
                )

                results.append(
                    {
                        "url": data["url"],
                        "title": data["title"],
                        "text": data["text"]
                    }
                )

                # Add newly discovered links
                # to the crawling queue.
                for link in data["links"]:

                    if link not in visited \
                            and link not in queue:

                        if is_same_domain(
                            seed_url,
                            link
                        ):

                            queue.append(link)

            except Exception as error:

                print(
                    f"[ERROR] Failed to crawl: "
                    f"{url}"
                )

                print(error)

    finally:
        browser.close()
        if playwright_context is not None:
            playwright_context.__exit__(None, None, None)

    print(
        f"[INFO] Crawl finished. "
        f"Pages collected: {len(results)}"
    )

    return results
