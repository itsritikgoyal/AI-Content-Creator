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
                        "You are a senior Enterprise Automation Architect with deep expertise in "
                        "AI Agents, RPA, workflow automation, LLMs, enterprise software, and digital transformation. "
                        "You write LinkedIn posts that sound like an experienced practitioner sharing real-world insights. "
                        "Never sound like a journalist, marketer, or news reporter. "
                        "Your writing is concise, practical, opinionated, and backed by the supplied information. "
                        "Never invent facts, numbers, or quotes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Write a LinkedIn post for professionals building AI Agents, RPA, workflow automation, "
                        "and enterprise AI solutions.\n\n"
                    
                        "The reader already knows the headline.\n"
                        "Do NOT summarize the news article.\n"
                        "Instead, explain WHY this matters and WHAT experienced engineers should learn from it.\n\n"
                    
                        "Structure:\n"
                        "1. Start with a surprising observation, bold opinion, or thought-provoking question (1-2 lines).\n"
                        "2. Add one short context sentence.\n"
                        "3. Give 3-5 practical bullet points using hyphens.\n"
                        "4. Whenever possible, include one realistic enterprise example.\n"
                        "5. Add a short section titled 'What I'd do next:' with one practical recommendation.\n"
                        "6. End with one discussion question.\n"
                        "7. Add 3-5 relevant hashtags.\n\n"
                    
                        "Writing Rules:\n"
                        "- Maximum 180 words.\n"
                        "- Short lines.\n"
                        "- Easy to scan.\n"
                        "- Practical instead of theoretical.\n"
                        "- Opinionated but balanced.\n"
                        "- Write like an experienced engineer.\n"
                        "- No emojis.\n"
                        "- No essay paragraphs.\n"
                        "- Never copy the article.\n"
                        "- Never include the source URL.\n"
                        "- Never say 'according to the article'.\n"
                        "- Use the source only for context.\n"
                        "- Never invent facts, statistics, quotes, or company statements.\n\n"
                    
                        "Avoid these words and phrases:\n"
                        "- revolutionary\n"
                        "- game-changer\n"
                        "- unlock\n"
                        "- leverage\n"
                        "- cutting-edge\n"
                        "- seamless\n"
                        "- robust\n"
                        "- transformative\n"
                        "- next-generation\n"
                        "- ever-evolving\n"
                        "- In today's fast-paced world\n"
                        "- As we all know\n"
                        "- Dive into\n"
                        "- Delve into\n\n"
                    
                        "The reader should finish the post thinking:\n"
                        "'That was practical. I learned something useful.'\n\n"
                    
                        f"Topic Title:\n{item.title}\n\n"
                        f"Topic Summary:\n{item.summary}\n\n"
                        f"Source Link (context only):\n{item.link}\n\n"
                        f"Why this topic matters:\n{reason}"
                    ),
                },
            ],
            temperature=0.55,
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
                        "You are an experienced Enterprise Automation Architect rewriting LinkedIn posts. "
                        "Your job is to make every revision more insightful, practical, concise, and engaging. "
                        "Never sound like a marketer or journalist. "
                        "Never invent facts."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Rewrite this LinkedIn post.\n\n"
                    
                        "The goal is NOT to rewrite the wording.\n"
                        "The goal is to make it significantly more valuable.\n\n"
                    
                        "Required structure:\n"
                        "- Strong hook\n"
                        "- One context sentence\n"
                        "- 3-5 practical bullet points\n"
                        "- One realistic enterprise example when possible\n"
                        "- 'What I'd do next:' recommendation\n"
                        "- One discussion question\n"
                        "- 3-5 relevant hashtags\n\n"
                    
                        "Rules:\n"
                        "- Under 180 words.\n"
                        "- Easy to scan.\n"
                        "- Practical.\n"
                        "- Opinionated.\n"
                        "- No emojis.\n"
                        "- No long paragraphs.\n"
                        "- Don't summarize the article.\n"
                        "- Don't mention the source.\n"
                        "- Never invent facts.\n"
                        "- Make this version noticeably better than the previous one.\n\n"
                    
                        f"Attempt: {attempt}\n\n"
                        f"Topic:\n{item.title}\n\n"
                        f"Summary:\n{item.summary}\n\n"
                        f"Previous Draft:\n{previous_post}"
                    ),
                },
            ],
            temperature=0.65,
        )
        return (response.choices[0].message.content or "").strip()
