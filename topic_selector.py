"""Topic selection service backed by OpenAI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from rss_fetcher import NewsItem


@dataclass(slots=True)
class TopicSelection:
    """Selected item plus rationale."""

    item: NewsItem
    reason: str


class TopicSelector:
    """Uses OpenAI to pick the strongest topic for LinkedIn."""

    def __init__(self, api_key: str, model: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def select(self, items: list[NewsItem]) -> TopicSelection:
        """Select the most LinkedIn-worthy topic from candidate items."""
        if not items:
            raise ValueError("No items provided for topic selection.")

        # Flatten candidates into deterministic text block for ranking.
        prompt = "\n\n---\n\n".join(
            f"Item {idx + 1}\n{item.as_prompt_line()}" for idx, item in enumerate(items)
        )

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior content strategist for AI agents, RPA, and enterprise automation."
                        " Pick one topic that will perform strongly with automation builders, AI agents "
                        "practitioners, and enterprise AI operators on LinkedIn."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Select the most relevant topic for automation and AI agents professionals on LinkedIn.\n"
                        "Prioritize practical enterprise impact, agentic workflows, RPA modernization, "
                        "AI operations, and implementation lessons over generic market-size news.\n\n"
                        "Return JSON with keys: selected_title, reason.\n\n"
                        f"Candidates:\n{prompt}"
                    ),
                },
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        selected_title = payload.get("selected_title", "").strip().lower()
        reason = payload.get("reason", "High relevance for enterprise AI professionals.").strip()

        for item in items:
            if item.title.strip().lower() == selected_title:
                return TopicSelection(item=item, reason=reason)

        # Fallback keeps pipeline moving even if model title formatting drifts.
        self.logger.warning("Model returned unmatched title. Falling back to first item.")
        return TopicSelection(item=items[0], reason=reason)
