import os

from playwright.sync_api import sync_playwright


def main() -> int:
    base_url = (os.getenv("E2E_BASE_URL") or "").strip().rstrip("/")
    username = (os.getenv("E2E_USERNAME") or "").strip()
    password = (os.getenv("E2E_PASSWORD") or "").strip()

    if not base_url:
        raise SystemExit("E2E_BASE_URL is required (e.g. https://your-app.streamlit.app)")
    if not username or not password:
        raise SystemExit("E2E_USERNAME and E2E_PASSWORD are required")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Sign In").click()

        # Successful login should show the sidebar with "New Chat" quickly.
        page.get_by_role("button", name="＋  New Chat").wait_for(timeout=60_000)

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

