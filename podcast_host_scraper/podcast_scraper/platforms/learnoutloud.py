"""
LearnOutLoud scraper for discovering podcast pages and external websites.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..base import BasePlatformScraper, PodcastData
from ..config import config

logger = logging.getLogger(__name__)


class LearnOutLoudScraper(BasePlatformScraper):
	"""Scraper for LearnOutLoud Podcast Directory."""

	BASE_URL = "https://www.learnoutloud.com"
	DIRECTORY_PATH = "/Podcast-Directory"

	def __init__(self):
		super().__init__()
		self.platform_name = "LearnOutLoud"
		self.session = requests.Session()
		self.session.headers.update({"User-Agent": config.USER_AGENT})

	def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
		"""
		Scrape LearnOutLoud podcast directory for a given topic.
		Falls back to first results if topic filtering yields none.
		"""
		self.logger.info(f"Starting LearnOutLoud scrape for topic: {topic}")

		start_url = urljoin(self.BASE_URL, self.DIRECTORY_PATH)
		podcast_urls: List[str] = []

		try:
			resp = self.session.get(start_url, timeout=15)
			resp.raise_for_status()
			podcast_urls.extend(self._extract_podcast_links(resp.text, topic))

			# If not enough results, try a few common category pages (best-effort)
			if len(podcast_urls) < limit:
				category_guesses = [
					"/Podcast-Directory/Technology",
					"/Podcast-Directory/Business",
					"/Podcast-Directory/Science",
					"/Podcast-Directory/Education-and-Professional",
				]
				for path in category_guesses:
					if len(podcast_urls) >= limit:
						break
					try:
						cat_url = urljoin(self.BASE_URL, path)
						cat_resp = self.session.get(cat_url, timeout=15)
						if cat_resp.ok:
							podcast_urls.extend(self._extract_podcast_links(cat_resp.text, topic))
					except Exception as e:
						self.logger.debug(f"Category fetch failed {path}: {e}")

			# Deduplicate and trim
			seen = set()
			unique_urls = []
			for u in podcast_urls:
				if u not in seen:
					seen.add(u)
					unique_urls.append(u)
			podcast_urls = unique_urls[:limit]
			self.logger.info(f"LearnOutLoud: collected {len(podcast_urls)} podcast detail URLs")
		except Exception as e:
			self.logger.error(f"Error scraping LearnOutLoud directory: {e}")
			return []

		podcasts: List[PodcastData] = []
		for i, url in enumerate(podcast_urls):
			if len(podcasts) >= limit:
				break
			try:
				self.logger.info(f"Processing LearnOutLoud podcast {i+1}/{len(podcast_urls)}: {url}")
				p = self._parse_podcast_page(url)
				if p and self.validate_podcast_data(p):
					podcasts.append(p)
				else:
					self.logger.debug("Invalid or incomplete podcast data")
			except Exception as e:
				self.logger.warning(f"Error processing {url}: {e}")
				continue

		self.scraped_podcasts = podcasts
		self.logger.info(f"Completed LearnOutLoud scraping: {len(podcasts)} valid podcasts")
		return podcasts

	def _extract_podcast_links(self, html: str, topic: str) -> List[str]:
		"""Extract candidate podcast detail page links from directory-like pages."""
		soup = BeautifulSoup(html, "lxml")
		links: List[str] = []
		topic_lower = (topic or "").lower()

		for a in soup.find_all("a", href=True):
			href = a["href"].strip()
			if not href.startswith("/Podcast-Directory/"):
				continue
			# Skip the top-level directory page itself
			path_parts = href.strip("/").split("/")
			if len(path_parts) < 3:
				# Require at least /Podcast-Directory/<Category>/<Name or Id>
				continue
			# Do not filter by topic here to maximize yield
			links.append(urljoin(self.BASE_URL, href))

		return links

	def _parse_podcast_page(self, url: str) -> Optional[PodcastData]:
		"""Parse a podcast detail page to create PodcastData, preferring external website."""
		resp = self.session.get(url, timeout=20)
		resp.raise_for_status()
		soup = BeautifulSoup(resp.text, "lxml")

		# Title
		title = None
		h1 = soup.find("h1")
		if h1 and h1.get_text(strip=True):
			title = h1.get_text(strip=True)
		if not title:
			title_tag = soup.find("title")
			if title_tag and title_tag.get_text(strip=True):
				title = title_tag.get_text(strip=True)
		title = title or "Unknown Podcast"

		# Find external website link (exclude learnoutloud and major directories)
		external_site = None
		for a in soup.find_all("a", href=True):
			href = a["href"].strip()
			if href.startswith("/"):
				href_full = urljoin(self.BASE_URL, href)
			else:
				href_full = href
			parsed = urlparse(href_full)
			host = parsed.netloc.lower()
			if not parsed.scheme.startswith("http"):
				continue
			blocked = [
				"learnoutloud.com",
				"podcasts.apple.com",
				"apple.com",
				"open.spotify.com",
				"spotify.com",
			]
			if any(b in host for b in blocked):
				continue
			# Prefer anchors whose text suggests website
			anchor_txt = (a.get_text(" ") or "").strip().lower()
			if any(w in anchor_txt for w in ["website", "official", "home", "visit"]):
				external_site = href_full
				break
			# Otherwise take the first external that looks like the show site (not social platforms)
			if not external_site and not any(s in host for s in ["twitter.com", "instagram.com", "linkedin.com", "youtube.com", "facebook.com"]):
				external_site = href_full

		podcast = PodcastData(
			podcast_name=self.clean_text(title),
			podcast_description=None,
			podcast_website=external_site,
			platform_source="LearnOutLoud",
			apple_podcasts_url=None,
			rss_feed_url=None,
			raw_data={"source_url": url}
		)

		return podcast
