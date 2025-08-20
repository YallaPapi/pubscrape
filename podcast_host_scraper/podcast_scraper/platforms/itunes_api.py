"""
Apple iTunes Search API scraper for bulk podcast discovery.
Avoids brittle DOM scraping by using the public search endpoint.
"""

import logging
import requests
from typing import List, Optional
from urllib.parse import quote_plus

from ..base import BasePlatformScraper, PodcastData

logger = logging.getLogger(__name__)


class ITunesApiScraper(BasePlatformScraper):
	"""Scraper using iTunes Search API for podcasts."""

	BASE_URL = "https://itunes.apple.com/search"

	def __init__(self):
		super().__init__()
		self.platform_name = "iTunesAPI"

	def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
		self.logger.info(f"Starting iTunes API scrape for topic: {topic}")
		q = quote_plus(topic or "podcast")
		params = {
			"term": q,
			"media": "podcast",
			"entity": "podcast",
			"limit": max(1, min(limit, 200)),
		}
		podcasts: List[PodcastData] = []
		try:
			resp = requests.get(self.BASE_URL, params=params, timeout=20)
			resp.raise_for_status()
			data = resp.json()
			results = data.get("results", [])
			self.logger.info(f"iTunes API returned {len(results)} results")
			for item in results:
				name = item.get("collectionName") or item.get("trackName") or "Unknown Podcast"
				apple_url = item.get("collectionViewUrl") or item.get("trackViewUrl")
				rss_url = item.get("feedUrl")
				p = PodcastData(
					podcast_name=self.clean_text(name),
					apple_podcasts_url=apple_url,
					rss_feed_url=rss_url,
					platform_source="iTunesAPI",
				)
				if self.validate_podcast_data(p):
					podcasts.append(p)
		except Exception as e:
			self.logger.error(f"iTunes API error: {e}")
			return []
		self.scraped_podcasts = podcasts
		self.logger.info(f"Completed iTunes API scraping: {len(podcasts)} valid podcasts")
		return podcasts
