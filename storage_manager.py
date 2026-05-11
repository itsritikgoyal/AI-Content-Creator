"""JSON-backed storage for workflow state and history."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STATE: dict[str, Any] = {
    "used_topics": [],
    "approved_posts": [],
    "pending_approval": None,
    "regeneration_count": 0,
}


@dataclass(slots=True)
class StorageManager:
    """Manages persistent state in storage.json."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            # First boot: initialize canonical state file.
            self._write(DEFAULT_STATE)
            return

        current = self._read()
        changed = False
        # Forward compatibility: auto-backfill newly introduced state keys.
        for key, default_value in DEFAULT_STATE.items():
            if key not in current:
                current[key] = deepcopy(default_value)
                changed = True
        if changed:
            self._write(current)

    def get_used_topics(self) -> set[str]:
        data = self._read()
        return set(data.get("used_topics", []))

    def add_used_topic(self, topic_title: str) -> None:
        data = self._read()
        # Store normalized titles so dedupe is case-insensitive.
        used_topics = set(data.get("used_topics", []))
        used_topics.add(topic_title.strip().lower())
        data["used_topics"] = sorted(used_topics)
        self._write(data)

    def get_pending_approval(self) -> dict[str, Any] | None:
        return self._read().get("pending_approval")

    def set_pending_approval(self, payload: dict[str, Any]) -> None:
        data = self._read()
        data["pending_approval"] = payload
        self._write(data)

    def clear_pending_approval(self) -> None:
        data = self._read()
        data["pending_approval"] = None
        self._write(data)

    def get_regeneration_count(self) -> int:
        return int(self._read().get("regeneration_count", 0))

    def set_regeneration_count(self, count: int) -> None:
        data = self._read()
        data["regeneration_count"] = count
        self._write(data)

    def add_approved_post(
        self,
        approval_id: str,
        topic_title: str,
        post_text: str,
        source_link: str,
        linkedin_post_id: str | None = None,
    ) -> None:
        data = self._read()
        approved_posts = data.get("approved_posts", [])
        approved_posts.append(
            {
                "approval_id": approval_id,
                "topic_title": topic_title,
                "post_text": post_text,
                "source_link": source_link,
                "linkedin_post_id": linkedin_post_id,
                "approved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        data["approved_posts"] = approved_posts
        self._write(data)

    def _read(self) -> dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8")
        return json.loads(raw)

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
