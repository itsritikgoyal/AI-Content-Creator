"""Human-friendly setup checks for the LinkedIn content workflow."""

from __future__ import annotations

import re
from pathlib import Path

from dotenv import dotenv_values


REQUIRED_KEYS = [
    "OPENAI_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_TO",
    "IMAP_USERNAME",
    "IMAP_PASSWORD",
    "LINKEDIN_ACCESS_TOKEN",
    "LINKEDIN_AUTHOR_URN",
]

INTEGER_KEYS = [
    "SMTP_PORT",
    "IMAP_PORT",
    "MAX_REGEN_ATTEMPTS",
    "LOG_MAX_BYTES",
    "LOG_BACKUP_COUNT",
]


def main() -> int:
    """Validate local .env shape without printing secrets."""
    env_path = Path(".env")
    if not env_path.exists():
        print("NOT READY: .env file is missing.")
        print("Create it from .env.example, then fill your real credentials.")
        return 1

    env = dotenv_values(env_path)
    problems: list[str] = []

    for key in REQUIRED_KEYS:
        value = (env.get(key) or "").strip()
        if not value:
            problems.append(f"{key} is missing.")
        elif _looks_like_placeholder(value):
            problems.append(f"{key} still looks like a placeholder.")

    for key in INTEGER_KEYS:
        value = (env.get(key) or "").strip()
        if value and not value.isdigit():
            problems.append(f"{key} must be a number.")

    linkedin_version = (env.get("LINKEDIN_API_VERSION") or "202604").strip()
    if not re.fullmatch(r"\d{6}", linkedin_version):
        problems.append("LINKEDIN_API_VERSION must use YYYYMM format, for example 202604.")

    author_urn = (env.get("LINKEDIN_AUTHOR_URN") or "").strip()
    if author_urn and not re.fullmatch(
        r"urn:li:(person|organization):\S+|urn:li:(member|company):\d+",
        author_urn,
    ):
        problems.append(
            "LINKEDIN_AUTHOR_URN must look like urn:li:person:<id>, "
            "urn:li:organization:<id>, urn:li:member:<numeric_id>, "
            "or urn:li:company:<numeric_id>."
        )

    token = (env.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if token and len(token) < 20:
        problems.append("LINKEDIN_ACCESS_TOKEN looks too short.")

    if problems:
        print("NOT READY")
        for problem in problems:
            print(f"- {problem}")
        print("\nFix these in .env, then run: python check_setup.py")
        return 1

    print("READY: .env has the required values and basic formats look valid.")
    print("Next:")
    print("1. Run python main.py to create/send a draft email.")
    print("2. Approve from email.")
    print("3. Run python main.py again to publish to LinkedIn.")
    return 0


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    placeholder_markers = [
        "your_",
        "your-",
        "paste_",
        "paste-",
        "actual_",
        "example",
        "xxxx",
    ]
    return any(marker in normalized for marker in placeholder_markers)


if __name__ == "__main__":
    raise SystemExit(main())
