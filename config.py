"""Configuration management for the Agentic LinkedIn Intelligence Engine."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    openai_api_key: str
    openai_model: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: str
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    linkedin_access_token: str
    linkedin_author_urn: str
    linkedin_api_version: str
    storage_file: Path
    max_regeneration_attempts: int
    log_level: str
    log_file: Path
    log_max_bytes: int
    log_backup_count: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables and defaults."""
        load_dotenv()

        base_dir = Path(__file__).resolve().parent
        linkedin_author_urn = _required("LINKEDIN_AUTHOR_URN")
        linkedin_api_version = os.getenv("LINKEDIN_API_VERSION", "202604")
        _validate_linkedin_settings(linkedin_author_urn, linkedin_api_version)

        return cls(
            openai_api_key=_required("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=_required("SMTP_USERNAME"),
            smtp_password=_required("SMTP_PASSWORD"),
            email_from=os.getenv("EMAIL_FROM", _required("SMTP_USERNAME")),
            email_to=_required("EMAIL_TO"),
            imap_host=os.getenv("IMAP_HOST", "imap.gmail.com"),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            imap_username=_required("IMAP_USERNAME"),
            imap_password=_required("IMAP_PASSWORD"),
            linkedin_access_token=_required("LINKEDIN_ACCESS_TOKEN"),
            linkedin_author_urn=linkedin_author_urn,
            linkedin_api_version=linkedin_api_version,
            storage_file=Path(os.getenv("STORAGE_FILE", str(base_dir / "storage.json"))),
            max_regeneration_attempts=int(os.getenv("MAX_REGEN_ATTEMPTS", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=Path(os.getenv("LOG_FILE", str(base_dir / "logs" / "agent.log"))),
            log_max_bytes=int(os.getenv("LOG_MAX_BYTES", str(2 * 1024 * 1024))),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )


def setup_logging(level: str, log_file: Path, max_bytes: int, backup_count: int) -> None:
    """Configure console + rotating file logging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # Avoid duplicate handlers on repeated in-process runs (tests/manual reruns).
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
        )
    )

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_rss_sources() -> list[str]:
    """Return the RSS sources used by the engine."""
    return [
        "https://news.google.com/rss/search?q=AI+RPA+automation+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://blogs.microsoft.com/ai/feed/",
        "https://www.automationanywhere.com/blog/feed",
    ]


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _validate_linkedin_settings(author_urn: str, api_version: str) -> None:
    if not re.fullmatch(r"urn:li:(person|organization):\S+", author_urn) and not re.fullmatch(
        r"urn:li:(member|company):\d+",
        author_urn,
    ):
        raise ValueError(
            "Invalid LINKEDIN_AUTHOR_URN. Use urn:li:person:<id>, "
            "urn:li:organization:<id>, urn:li:member:<numeric_id>, "
            "or urn:li:company:<numeric_id>."
        )
    if not re.fullmatch(r"\d{6}", api_version):
        raise ValueError("Invalid LINKEDIN_API_VERSION. Use YYYYMM format, for example 202604.")
