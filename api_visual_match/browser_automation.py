import os
import random
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def visual_tab_url(search_url: str) -> str:
    parsed = urlparse(search_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["udm"] = ["44"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def get_visual_match_html(image_url: str) -> str:
    headless_value = os.getenv("BA_HEADLESS", os.getenv("HYBRID_HEADLESS", "0"))
    headless = headless_value.strip().lower() in {"1", "true", "yes", "on"}
    width, height = random.choice([(1366, 768), (1536, 864), (1600, 900), (1707, 825)])
    proxy_server = os.getenv("BA_PROXY_SERVER")
    proxy_username = os.getenv("BA_PROXY_USERNAME")
    proxy_password = os.getenv("BA_PROXY_PASSWORD")
    proxy = None
    if proxy_server:
        proxy = {"server": proxy_server}
        if proxy_username and proxy_password:
            proxy["username"] = proxy_username
            proxy["password"] = proxy_password

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            proxy=proxy,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                f"--window-size={width},{height}",
            ],
        )
        context = browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
        )
        page = context.new_page()

        try:
            # Small browser tweaks so the page is closer to a normal Chrome session.
            page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                window.chrome = window.chrome || { runtime: {} };
                """
            )

            page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(random.randint(250, 700))

            page.mouse.move(random.randint(60, width // 3), random.randint(60, height // 3))
            for _ in range(random.randint(4, 7)):
                page.mouse.move(
                    random.randint(30, width - 30),
                    random.randint(80, height - 40),
                    steps=random.randint(8, 20),
                )
                page.wait_for_timeout(random.randint(90, 220))

            lens_url = f"https://lens.google.com/uploadbyurl?url={image_url}"
            page.goto(lens_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(random.randint(300, 850))

            parsed = urlparse(page.url)
            if not (parsed.netloc == "www.google.com" and parsed.path == "/search"):
                try:
                    page.wait_for_url("**/search**", timeout=70000)
                except PlaywrightTimeoutError:
                    raise RuntimeError(f"Lens did not redirect to Google Search. Final URL: {page.url}")

            search_url = page.url

            clicked_visual = False
            for selector in ["text=Visual matches", "text=Visual results", "a[href*='udm=44']", "[aria-label*='Visual']"]:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    locator.click(timeout=4000)
                    clicked_visual = True
                    break

            if not clicked_visual:
                page.goto(visual_tab_url(search_url), wait_until="domcontentloaded", timeout=60000)

            try:
                page.wait_for_load_state("networkidle", timeout=25000)
            except PlaywrightTimeoutError:
                page.wait_for_timeout(2000)

            page.mouse.wheel(0, random.randint(350, 900))
            page.wait_for_timeout(random.randint(200, 500))
            page.mouse.wheel(0, random.randint(-200, -40))
            page.wait_for_timeout(random.randint(300, 700))

            return page.content()
        finally:
            context.close()
            browser.close()
