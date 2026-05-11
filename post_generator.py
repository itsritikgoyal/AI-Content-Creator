"""LinkedIn post generation and regeneration via OpenAI."""

from __future__ import annotations

import logging

from openai import OpenAI

from rss_fetcher import NewsItem


class PostGenerator:
    """Generates professional LinkedIn posts for selected topics."""

    def __init__(self, api_key: str, model: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, item: NewsItem, reason: str) -> str:
        """Generate a first-draft LinkedIn post from a selected news topic."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write sharp, practical LinkedIn posts for automation builders, "
                        "AI agents practitioners, RPA teams, and enterprise AI operators. "
                        "Your style is concise, specific, and useful. Never write like a news article."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Write a LinkedIn post for automation and AI agents professionals.\n\n"
                        "Use this exact strategy:\n"
                        "1. Start with a punchy 1-2 line hook.\n"
                        "2. Add one short context line based on the topic.\n"
                        "3. Give 3-5 practical bullet points using hyphens.\n"
                        "4. Add one short 'What this means:' takeaway.\n"
                        "5. End with one discussion question.\n"
                        "6. Add 3-5 relevant hashtags.\n\n"
                        "Style rules:\n"
                        "- Keep it under 180 words.\n"
                        "- Use short lines and scannable points.\n"
                        "- Write for people building AI agents, workflow automation, RPA, and enterprise AI systems.\n"
                        "- Focus on practical implications, not article summary.\n"
                        "- Have a clear point of view.\n"
                        "- No emojis.\n"
                        "- No long essay paragraphs.\n"
                        "- Avoid buzzwords: revolutionary, game-changer, unlock, leverage, ever-evolving, cutting-edge, seamless, robust.\n"
                        "- Do not mention that you are using this structure.\n\n"
                        f"Topic title: {item.title}\n"
                        f"Topic summary: {item.summary}\n"
                        f"Source link: {item.link}\n"
                        f"Why this topic matters: {reason}"
                    ),
                },
            ],
            temperature=0.7,
        )
        return (response.choices[0].message.content or "").strip()

    def regenerate(self, item: NewsItem, previous_post: str, attempt: int) -> str:
        """Regenerate an improved draft after rejection."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You rewrite LinkedIn posts for automation builders and AI agents practitioners. "
                        "Your revisions make posts shorter, sharper, more practical, and easier to scan."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Rewrite this LinkedIn post using a tighter point-based format.\n\n"
                        "Required structure:\n"
                        "- Punchy 1-2 line hook\n"
                        "- One context line\n"
                        "- 3-5 practical bullet points using hyphens\n"
                        "- One 'What this means:' takeaway\n"
                        "- One discussion question\n"
                        "- 3-5 relevant hashtags\n\n"
                        "Rules:\n"
                        "- Keep it under 180 words.\n"
                        "- Target automation, AI agents, RPA, and enterprise AI professionals.\n"
                        "- Make it practical and opinionated.\n"
                        "- No emojis.\n"
                        "- No essay-style paragraphs.\n"
                        "- Avoid buzzwords: revolutionary, game-changer, unlock, leverage, ever-evolving, cutting-edge, seamless, robust.\n\n"
                        f"Regeneration attempt: {attempt}\n"
                        f"Topic title: {item.title}\n"
                        f"Topic summary: {item.summary}\n\n"
                        f"Current draft:\n{previous_post}"
                    ),
                },
            ],
            temperature=0.8,
        )
        return (response.choices[0].message.content or "").strip()
