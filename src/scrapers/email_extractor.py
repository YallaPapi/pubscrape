from botasaurus.browser import browser
import re
from typing import Optional


@browser(headless=True, block_images=True)
def extract_emails_from_website(driver, website_url: str) -> Optional[str]:
    """
    Visit website and extract a likely business email address.
    """
    if not website_url or not website_url.startswith("http"):
        return None
    try:
        driver.get(website_url)

        # Try contact/about pages
        for sel in [
            "a[href*='contact']",
            "a[href*='about']",
            "a:contains('Contact')",
            "a:contains('About')",
        ]:
            try:
                link = driver.find_element("css selector", sel)
                link.click()
                break
            except Exception:
                continue

        page_html = driver.page_source
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        emails = re.findall(email_pattern, page_html)
        filtered = [e.lower() for e in emails if not any(x in e.lower() for x in ['example', 'test', 'demo', 'noreply'])]

        preferred_prefixes = ("info@", "contact@", "sales@", "support@", "hello@", "admin@")
        for e in filtered:
            if e.startswith(preferred_prefixes):
                return e
        return filtered[0] if filtered else None
    except Exception:
        return None
