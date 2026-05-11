"""RSS fetching and filtering logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser


@dataclass(slots=True)
class NewsItem:
    """Represents a single news item extracted from RSS feeds."""

    title: str
    summary: str
    link: str
    published_at: datetime
    source: str

    def as_prompt_line(self) -> str:
        """String format used when passing items to LLM prompts."""
        date_text = self.published_at.strftime("%Y-%m-%d")
        return (
            f"Title: {self.title}\n"
            f"Summary: {self.summary}\n"
            f"Link: {self.link}\n"
            f"Source: {self.source}\n"
            f"Published: {date_text}"
        )


class RSSFetcher:
    """Fetch and filter AI/RPA content from RSS feeds."""

    def __init__(self, rss_sources: Iterable[str]) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rss_sources = list(rss_sources)

    def fetch_recent(self, used_topics: set[str], limit: int = 10) -> list[NewsItem]:
        """Return recent, unused items from configured feeds."""
        # All sources are normalized against one UTC cutoff to keep behavior consistent.
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        collected: list[NewsItem] = []
        seen_titles: set[str] = set()
        used_topics_normalized = {topic.strip().lower() for topic in used_topics}

        for source_url in self.rss_sources:
            try:
                feed = feedparser.parse(source_url)
                source_title = feed.feed.get("title", source_url)
                for entry in feed.entries:
                    item = self._entry_to_news_item(entry, source_title)
                    if not item:
                        continue

                    normalized_title = item.title.strip().lower()
                    # Skip duplicates across feeds and already-approved topics.
                    if normalized_title in seen_titles:
                        continue
                    if normalized_title in used_topics_normalized:
                        continue
                    if item.published_at < cutoff:
                        continue

                    seen_titles.add(normalized_title)
                    collected.append(item)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.exception("Failed to parse feed %s: %s", source_url, exc)

        # Most recent first gives selector fresher context.
        collected.sort(key=lambda item: item.published_at, reverse=True)
        if limit > 0:
            collected = collected[:limit]

        self.logger.info("Collected %d recent unused items", len(collected))
        return collected

    def _entry_to_news_item(self, entry: feedparser.FeedParserDict, source: str) -> NewsItem | None:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            return None

        published_at = self._parse_published_at(entry)
        if not published_at:
            return None

        return NewsItem(
            title=title,
            summary=summary,
            link=link,
            published_at=published_at,
            source=source,
        )

    @staticmethod
    def _parse_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
        """Parse published datetime from common RSS fields."""
        for field in ("published", "updated"):
            raw_value = entry.get(field)
            if not raw_value:
                continue
            try:
                parsed = parsedate_to_datetime(raw_value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
        return None
