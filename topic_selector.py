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
                        "You are a Senior Enterprise Automation Architect and AI Strategy Advisor. "
                        "Your audience consists of automation engineers, AI Agent developers, "
                        "RPA architects, solution architects, and enterprise technology leaders. "
                        "Your job is to identify the ONE topic that offers the highest practical value "
                        "for professionals building or deploying AI and automation systems. "
                        "Ignore clickbait and focus on topics that teach something useful. "
                        "Never optimize for sensational headlines."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Choose ONE topic that is most valuable for enterprise AI and automation professionals.\n\n"
                    
                        "Ranking priorities (highest to lowest):\n"
                        "1. Practical implementation lessons\n"
                        "2. AI Agents and agentic workflows\n"
                        "3. Enterprise automation\n"
                        "4. RPA modernization\n"
                        "5. LLM applications\n"
                        "6. AI governance, security, compliance\n"
                        "7. Productivity improvements\n"
                        "8. Engineering best practices\n\n"
                    
                        "Avoid selecting articles that are mainly about:\n"
                        "- Company funding\n"
                        "- Stock prices\n"
                        "- Market reports\n"
                        "- Executive appointments\n"
                        "- Product marketing\n"
                        "- Press releases\n"
                        "- Generic AI hype\n\n"
                    
                        "Prefer topics containing:\n"
                        "- Enterprise deployment lessons\n"
                        "- Technical architecture\n"
                        "- Real customer use cases\n"
                        "- AI orchestration\n"
                        "- Multi-agent systems\n"
                        "- MCP\n"
                        "- Workflow automation\n"
                        "- Human-in-the-loop\n"
                        "- AI evaluation\n"
                        "- Observability\n"
                        "- Governance\n"
                        "- Prompt engineering\n"
                        "- Production AI systems\n\n"
                    
                        "Return ONLY valid JSON.\n\n"
                    
                        "Format:\n"
                        "{\n"
                        '  "selected_title": "...",\n'
                        '  "reason": "..."\n'
                        "}\n\n"
                    
                        f"Candidates:\n{prompt}"
                    ),
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        selected_title = payload.get("selected_title", "").strip().lower()
        reason = payload.get("reason", "Reason should explain WHY the topic matters in 20-40 words. Mention enterprise impact or implementation value.").strip()

        for item in items:
            if item.title.strip().lower() == selected_title:
                return TopicSelection(item=item, reason=reason)

        # Fallback keeps pipeline moving even if model title formatting drifts.
        self.logger.warning("Model returned unmatched title. Falling back to first item.")
        return TopicSelection(item=items[0], reason=reason)
