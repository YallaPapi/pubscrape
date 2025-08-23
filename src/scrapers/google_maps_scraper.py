from botasaurus.browser import browser
from selenium.webdriver.common.by import By
from typing import List, Dict, Optional


@browser(headless=False, block_images=True, window_size="1920,1080")
def scrape_google_maps_businesses(driver, search_query: str, max_results: int = 100) -> List[Dict]:
    """
    Visit Google Maps and extract real businesses for the given search query.
    """
    driver.get("https://www.google.com/maps")

    # Search
    search_box = driver.find_element(By.ID, "searchboxinput")
    search_box.clear()
    search_box.send_keys(search_query + "\n")

    businesses: List[Dict] = []
    cards_seen = set()

    # Attempt to find result cards and scroll to load more
    for _ in range(20):
        result_cards = driver.find_elements(By.CSS_SELECTOR, "[data-result-index]")
        for card in result_cards:
            try:
                cid = card.get_attribute("data-result-index") or card.get_attribute("data-cid") or id(card)
                if cid in cards_seen:
                    continue
                data = _extract_business_data(card)
                if data:
                    businesses.append(data)
                    cards_seen.add(cid)
                    if len(businesses) >= max_results:
                        return businesses
            except Exception:
                continue
        driver.execute_script("window.scrollBy(0, 600)")

    return businesses


def _extract_business_data(card) -> Optional[Dict]:
    try:
        name = None
        for sel in [
            '[data-value="title"]',
            'div[class*="fontHeadline"]',
            'h3, h2, h1',
        ]:
            try:
                elem = card.find_element(By.CSS_SELECTOR, sel)
                if elem and elem.text.strip():
                    name = elem.text.strip()
                    break
            except Exception:
                continue
        if not name:
            return None

        address = _get_text(card, '[data-value="address"], span[class*="address"], div[class*="address"]')

        phone = None
        try:
            tel = card.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
            phone = (tel.get_attribute('href') or '').replace('tel:', '').strip()
        except Exception:
            pass

        website = None
        try:
            w = card.find_element(By.CSS_SELECTOR, 'a[data-value="website"], a[href^="http"]')
            website = w.get_attribute('href')
        except Exception:
            pass

        return {
            'name': name,
            'address': address,
            'phone': phone,
            'website': website,
            'source': 'google_maps'
        }
    except Exception:
        return None


def _get_text(node, selector: str) -> Optional[str]:
    try:
        elem = node.find_element(By.CSS_SELECTOR, selector)
        txt = elem.text.strip()
        return txt if txt else None
    except Exception:
        return None
