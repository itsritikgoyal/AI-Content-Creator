"""Main orchestration flow for the Agentic LinkedIn Intelligence Engine."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from approval_checker import ApprovalChecker
from config import Settings, get_rss_sources, setup_logging
from email_service import EmailService
from linkedin_service import LinkedInService
from post_generator import PostGenerator
from rss_fetcher import RSSFetcher
from storage_manager import StorageManager
from topic_selector import TopicSelector


logger = logging.getLogger("LinkedInAgent")


def run() -> None:
    """Execute one cycle of the autonomous approval workflow."""
    settings = Settings.from_env()
    setup_logging(
        settings.log_level,
        settings.log_file,
        settings.log_max_bytes,
        settings.log_backup_count,
    )
    logger.info("Starting LinkedIn agent run")
    logger.info(
        "Runtime config: model=%s storage=%s log_file=%s",
        settings.openai_model,
        settings.storage_file,
        settings.log_file,
    )

    try:
        storage = StorageManager(settings.storage_file)
        pending = storage.get_pending_approval()
        logger.info("Loaded state: pending=%s regen_count=%d", bool(pending), storage.get_regeneration_count())

        email_service = EmailService(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            email_from=settings.email_from,
            email_to=settings.email_to,
        )
        approval_checker = ApprovalChecker(
            imap_host=settings.imap_host,
            imap_port=settings.imap_port,
            username=settings.imap_username,
            password=settings.imap_password,
        )
        post_generator = PostGenerator(api_key=settings.openai_api_key, model=settings.openai_model)
        linkedin_service = LinkedInService(
            access_token=settings.linkedin_access_token,
            author_urn=settings.linkedin_author_urn,
            api_version=settings.linkedin_api_version,
        )

        # State-machine entrypoint:
        # If no pending item exists, create a new draft and start approval flow.
        if not pending:
            logger.info("No pending approval found. Starting new topic discovery cycle.")
            _start_new_cycle(settings, storage, email_service, post_generator)
            return

        approval_id = pending["approval_id"]
        logger.info("Pending approval found: id=%s topic=%s", approval_id, pending["topic_title"])
        result = approval_checker.check(approval_id=approval_id)
        if not result:
            logger.info("No approval reply yet for ID=%s", approval_id)
            return

        # Positive decision finalizes the post and prevents future duplicate topic reuse.
        if result.decision == "APPROVE":
            logger.info("Decision received: APPROVE for ID=%s", approval_id)
            linkedin_result = linkedin_service.publish_text_post(pending["post_text"])
            storage.add_approved_post(
                approval_id=approval_id,
                topic_title=pending["topic_title"],
                post_text=pending["post_text"],
                source_link=pending["source_link"],
                linkedin_post_id=linkedin_result.post_id,
            )
            storage.add_used_topic(pending["topic_title"])
            storage.clear_pending_approval()
            storage.set_regeneration_count(0)
            logger.info(
                "Post approved, published, and stored for ID=%s linkedin_post_id=%s",
                approval_id,
                linkedin_result.post_id,
            )
            return

        # Negative decision triggers rewrite loop with hard stop to avoid infinite churn.
        current_count = storage.get_regeneration_count() + 1
        logger.info("Decision received: DENY for ID=%s. Regeneration attempt=%d", approval_id, current_count)
        if current_count > settings.max_regeneration_attempts:
            logger.warning(
                "Max regeneration attempts exceeded for ID=%s (limit=%d)",
                approval_id,
                settings.max_regeneration_attempts,
            )
            return

        regenerated = post_generator.regenerate(
            item=_pending_to_news_item(pending),
            previous_post=pending["post_text"],
            attempt=current_count,
        )
        logger.info("Regeneration successful for ID=%s attempt=%d", approval_id, current_count)
        pending["post_text"] = regenerated
        pending["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

        storage.set_pending_approval(pending)
        storage.set_regeneration_count(current_count)
        email_service.send_approval_request(
            approval_id=approval_id,
            topic_title=pending["topic_title"],
            post_text=regenerated,
            attempt=current_count,
        )
        logger.info("Sent regenerated draft for ID=%s attempt=%d", approval_id, current_count)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Workflow execution failed: %s", exc)
        raise


def _start_new_cycle(
    settings: Settings,
    storage: StorageManager,
    email_service: EmailService,
    post_generator: PostGenerator,
) -> None:
    # Pull recent candidate topics and remove anything already used.
    used_topics = storage.get_used_topics()
    logger.info("Used topic count=%d", len(used_topics))
    rss_fetcher = RSSFetcher(get_rss_sources())
    candidates = rss_fetcher.fetch_recent(used_topics=used_topics, limit=10)
    logger.info("Candidate topics fetched=%d", len(candidates))
    if len(candidates) < 1:
        logger.info("No new candidate topics found in the last 7 days.")
        return

    # Use LLM twice: first to choose the best topic, then to draft the post.
    topic_selector = TopicSelector(api_key=settings.openai_api_key, model=settings.openai_model)
    selection = topic_selector.select(candidates[:10])
    logger.info("Selected topic: %s", selection.item.title)
    post_text = post_generator.generate(item=selection.item, reason=selection.reason)
    logger.info("Post generation completed (chars=%d)", len(post_text))

    approval_id = uuid.uuid4().hex[:12]
    # Persist complete pending context so future runs can resume without recomputation.
    pending_payload = {
        "approval_id": approval_id,
        "topic_title": selection.item.title,
        "topic_summary": selection.item.summary,
        "source_link": selection.item.link,
        "selection_reason": selection.reason,
        "post_text": post_text,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
    }

    storage.set_pending_approval(pending_payload)
    storage.set_regeneration_count(0)
    email_service.send_approval_request(
        approval_id=approval_id,
        topic_title=selection.item.title,
        post_text=post_text,
        attempt=0,
    )
    logger.info("Created new pending approval ID=%s", approval_id)


def _pending_to_news_item(pending: dict) -> "NewsItem":
    from rss_fetcher import NewsItem

    # Regeneration API expects NewsItem shape, so we reconstruct from stored state.
    return NewsItem(
        title=pending["topic_title"],
        summary=pending.get("topic_summary", ""),
        link=pending.get("source_link", ""),
        published_at=datetime.now(timezone.utc),
        source="stored-pending",
    )


if __name__ == "__main__":
    run()
