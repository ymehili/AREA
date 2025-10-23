"""RSS plugin for AREA - Implements RSS/Atom feed parsing and content monitoring.

This plugin integrates with RSS/Atom feeds to provide:
- Real-time RSS feed parsing and content extraction
- New item detection with deduplication
- Keyword-based filtering and triggering
- Content sanitization and variable extraction

RSS feeds are polled at configurable intervals to detect new content.
"""

from __future__ import annotations

import logging
import hashlib
import feedparser
import bleach
import httpx
from typing import TYPE_CHECKING, Any, Dict, List, Set
from datetime import datetime

from app.models.area import Area
from app.integrations.simple_plugins.exceptions import (
    RSSError,
    RSSFeedError,
    RSSConnectionError,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger("area")


# RSS feed cache and deduplication
class RSSFeedManager:
    """Manages RSS feed parsing, caching, and duplicate detection."""

    def __init__(self):
        self.cache: Dict[str, tuple] = {}  # url -> (feed_data, timestamp)
        self.seen_items: Dict[str, Set[str]] = {}  # area_id -> set of seen hashes
        self.cache_ttl = 300  # 5 minutes cache TTL

    def _generate_item_hash(self, entry: Dict[str, Any]) -> str:
        """Generate unique hash to detect duplicate RSS items.

        Args:
            entry: RSS feed entry dictionary

        Returns:
            MD5 hash of entry content for deduplication
        """
        # Combine multiple fields to generate unique hash
        content_parts = [
            entry.get("id", ""),
            entry.get("title", ""),
            entry.get("link", ""),
            entry.get("published", ""),
            entry.get("summary", "")[:200],  # First 200 chars of summary
        ]
        content = "".join(str(part) for part in content_parts)
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _is_new_item(self, item_hash: str, area_id: str) -> bool:
        """Check if RSS item is new for a specific area.

        Args:
            item_hash: Hash of the RSS item
            area_id: Area ID to check against

        Returns:
            True if item is new, False if already seen
        """
        if area_id not in self.seen_items:
            self.seen_items[area_id] = set()

        if item_hash in self.seen_items[area_id]:
            return False

        self.seen_items[area_id].add(item_hash)

        # Limit seen items to prevent memory bloat
        if len(self.seen_items[area_id]) > 1000:
            # Remove oldest 200 items
            items_list = list(self.seen_items[area_id])
            items_list.sort()  # Simple approach - assumes hashes are somewhat ordered
            self.seen_items[area_id] = set(items_list[200:])

        return True

    def _sanitize_content(self, content: str) -> str:
        """Sanitize HTML content from RSS feeds.

        Args:
            content: Raw HTML content

        Returns:
            Sanitized plain text content
        """
        if not content:
            return ""

        # Remove HTML tags but preserve text content
        allowed_tags = ["p", "br", "strong", "em", "u", "a"]
        allowed_attributes = {"a": ["href"]}

        # First bleach with allowed tags, then strip remaining tags
        sanitized = bleach.clean(
            content, tags=allowed_tags, attributes=allowed_attributes, strip=True
        )

        return sanitized.strip()

    async def parse_feed(
        self, feed_url: str, area: Area = None, db: Session = None
    ) -> Dict[str, Any]:
        """Parse RSS feed and return new items with deduplication.

        Args:
            feed_url: URL of the RSS feed
            area: Area being executed (for deduplication)
            db: Database session

        Returns:
            Dictionary containing feed info and new items

        Raises:
            RSSConnectionError: If feed fetch fails
            RSSFeedError: If feed parsing fails
        """
        try:
            # Check cache first
            now = datetime.now()
            cache_key = f"{feed_url}:{area.id if area else 'preview'}"

            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (now - cached_time).seconds < self.cache_ttl:
                    logger.debug(f"Using cached RSS feed: {feed_url}")
                    return cached_data

            logger.info(f"Parsing RSS feed: {feed_url}")

            # Fetch RSS feed with timeout
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(feed_url)
                response.raise_for_status()

            # Parse RSS feed using feedparser
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(
                    f"Malformed RSS feed detected: {feed_url} - {feed.bozo_exception}",
                    extra={
                        "feed_url": feed_url,
                        "area_id": str(area.id) if area else None,
                        "bozo_exception": str(feed.bozo_exception)
                        if feed.bozo_exception
                        else None,
                    },
                )

            # Validate feed has required structure
            if not hasattr(feed, "feed") or not hasattr(feed, "entries"):
                raise RSSFeedError(f"Invalid RSS feed structure: {feed_url}")

            if not feed.entries:
                logger.info(f"No entries found in RSS feed: {feed_url}")
                result = {
                    "feed_info": {
                        "title": getattr(feed.feed, "title", "Unknown Feed"),
                        "description": getattr(feed.feed, "description", ""),
                        "link": getattr(feed.feed, "link", ""),
                        "url": feed_url,
                    },
                    "new_items": [],
                    "total_items": 0,
                }

                # Cache result
                self.cache[cache_key] = (result, now)
                return result

            # Process entries and detect new items
            new_items = []
            total_items = len(feed.entries)

            for entry in feed.entries:
                item_hash = self._generate_item_hash(entry)

                # Check if this is a new item (skip if no area provided for preview)
                if area and not self._is_new_item(item_hash, str(area.id)):
                    continue

                # Extract and sanitize item data
                item_data = {
                    "id": entry.get("id", ""),
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": self._sanitize_content(entry.get("description", "")),
                    "summary": self._sanitize_content(entry.get("summary", "")),
                    "author": entry.get("author", ""),
                    "published": entry.get("published", ""),
                    "updated": entry.get("updated", ""),
                    "categories": [
                        tag.get("term", "") for tag in entry.get("tags", [])
                    ],
                    "hash": item_hash,
                }

                # Handle content field (may contain full HTML content)
                if hasattr(entry, "content") and entry.content:
                    content_value = entry.content[0] if entry.content else {}
                    if isinstance(content_value, dict):
                        item_data["content"] = self._sanitize_content(
                            content_value.get("value", "")
                        )
                    else:
                        item_data["content"] = self._sanitize_content(
                            str(content_value)
                        )
                else:
                    item_data["content"] = (
                        item_data["description"] or item_data["summary"]
                    )

                new_items.append(item_data)

            # Extract feed information
            feed_info = {
                "title": getattr(feed.feed, "title", "Unknown Feed"),
                "description": getattr(feed.feed, "description", ""),
                "link": getattr(feed.feed, "link", ""),
                "url": feed_url,
                "language": getattr(feed.feed, "language", ""),
                "updated": getattr(feed.feed, "updated", ""),
                "generator": getattr(feed.feed, "generator", ""),
            }

            result = {
                "feed_info": feed_info,
                "new_items": new_items,
                "total_items": total_items,
                "processed_items": len(new_items),
            }

            # Cache result
            self.cache[cache_key] = (result, now)

            logger.info(
                "RSS feed parsed successfully",
                extra={
                    "feed_url": feed_url,
                    "area_id": str(area.id) if area else None,
                    "total_items": total_items,
                    "new_items": len(new_items),
                    "feed_title": feed_info.get("title", "Unknown"),
                },
            )

            return result

        except httpx.RequestError as e:
            error_msg = f"Failed to fetch RSS feed: {str(e)}"
            logger.error(
                "RSS connection error",
                extra={
                    "feed_url": feed_url,
                    "area_id": str(area.id) if area else None,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise RSSConnectionError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to parse RSS feed: {str(e)}"
            logger.error(
                "RSS parsing error",
                extra={
                    "feed_url": feed_url,
                    "area_id": str(area.id) if area else None,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise RSSFeedError(error_msg) from e


# Global RSS feed manager instance
rss_feed_manager = RSSFeedManager()


def _get_rss_feed_url(area: Area, db: Session) -> str:
    """Get RSS feed URL from area parameters.

    Args:
        area: The Area being executed
        db: Database session

    Returns:
        RSS feed URL string

    Raises:
        RSSFeedError: If feed URL not found in area parameters
    """
    feed_url = area.trigger_params.get("feed_url")
    if not feed_url:
        raise RSSFeedError("RSS feed URL is required in trigger parameters")

    return feed_url


def _check_keywords(content: str, keywords: List[str]) -> bool:
    """Check if content contains any of the specified keywords.

    Args:
        content: Content to search in
        keywords: List of keywords to search for

    Returns:
        True if any keyword found, False otherwise
    """
    if not keywords or not content:
        return False

    content_lower = content.lower()
    return any(keyword.lower() in content_lower for keyword in keywords)


async def rss_new_item_handler(
    area: Area, params: dict, event: dict, db: "Session" = None
) -> None:
    """Handle RSS new item trigger.

    This trigger fires when new items are detected in an RSS feed.
    Each new item triggers the automation workflow independently.

    Args:
        area: The Area being executed
        params: Trigger parameters (feed_url, check_interval, max_items)
        event: Event data dictionary (will be populated with RSS data)
        db: Database session

    Raises:
        RSSFeedError: If feed parsing fails
        RSSConnectionError: If feed connection fails

    Example trigger_params:
        {
            "feed_url": "https://example.com/rss.xml",
            "check_interval": 300,
            "max_items": 10
        }
    """
    try:
        # Get RSS feed URL from area parameters
        feed_url = _get_rss_feed_url(area, db)

        logger.info(
            "Starting RSS new_item trigger",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "feed_url": feed_url,
            },
        )

        # Parse RSS feed and get new items
        result = await rss_feed_manager.parse_feed(feed_url, area, db)

        new_items = result.get("new_items", [])
        feed_info = result.get("feed_info", {})

        if not new_items:
            logger.info(
                f"No new RSS items found for area {area.id}",
                extra={
                    "area_id": str(area.id),
                    "feed_url": feed_url,
                    "total_items": result.get("total_items", 0),
                },
            )
            return

        # Process each new item
        for item in new_items:
            # Populate event with RSS variables for template substitution
            event.update(
                {
                    "rss.title": item.get("title", ""),
                    "rss.description": item.get("description", ""),
                    "rss.summary": item.get("summary", ""),
                    "rss.content": item.get("content", ""),
                    "rss.link": item.get("link", ""),
                    "rss.author": item.get("author", ""),
                    "rss.published": item.get("published", ""),
                    "rss.updated": item.get("updated", ""),
                    "rss.categories": ", ".join(item.get("categories", [])),
                    "rss.id": item.get("id", ""),
                    "rss.hash": item.get("hash", ""),
                    "rss.feed_title": feed_info.get("title", ""),
                    "rss.feed_url": feed_url,
                    "rss.feed_description": feed_info.get("description", ""),
                }
            )

            # Store full RSS data for execution logs
            event["rss_data"] = {
                "item": item,
                "feed_info": feed_info,
                "triggered_at": datetime.now().isoformat(),
            }

            logger.info(
                "RSS new item trigger fired",
                extra={
                    "area_id": str(area.id),
                    "area_name": area.name,
                    "user_id": str(area.user_id),
                    "feed_url": feed_url,
                    "item_title": item.get("title"),
                    "item_link": item.get("link"),
                    "item_published": item.get("published"),
                },
            )

        logger.info(
            "RSS new_item trigger completed",
            extra={
                "area_id": str(area.id),
                "feed_url": feed_url,
                "new_items_count": len(new_items),
                "feed_title": feed_info.get("title", ""),
            },
        )

    except RSSError:
        # Re-raise RSS-specific errors
        raise
    except Exception as e:
        logger.error(
            "RSS new_item handler failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise RSSFeedError(f"RSS new item handler failed: {str(e)}") from e


async def rss_keyword_detected_handler(
    area: Area, params: dict, event: dict, db: "Session" = None
) -> None:
    """Handle RSS keyword detection trigger.

    This trigger fires when new RSS items contain specific keywords.
    Keywords are searched in title, description, and content fields.

    Args:
        area: The Area being executed
        params: Trigger parameters (feed_url, keywords, check_fields)
        event: Event data dictionary (will be populated with RSS data)
        db: Database session

    Raises:
        RSSFeedError: If feed parsing fails
        RSSConnectionError: If feed connection fails
        ValueError: If keywords parameter is missing or invalid

    Example trigger_params:
        {
            "feed_url": "https://example.com/rss.xml",
            "keywords": ["python", "programming", "tutorial"],
            "check_fields": ["title", "description", "content"],
            "match_all": false
        }
    """
    try:
        # Get RSS feed URL from area parameters
        feed_url = _get_rss_feed_url(area, db)

        # Validate keywords parameter
        keywords = params.get("keywords", [])
        if not keywords or not isinstance(keywords, list):
            raise ValueError("Keywords parameter is required and must be a list")

        check_fields = params.get("check_fields", ["title", "description", "content"])
        match_all = params.get(
            "match_all", False
        )  # false = ANY keyword match, true = ALL keywords match

        logger.info(
            "Starting RSS keyword_detected trigger",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "feed_url": feed_url,
                "keywords": keywords,
                "check_fields": check_fields,
                "match_all": match_all,
            },
        )

        # Parse RSS feed and get new items
        result = await rss_feed_manager.parse_feed(feed_url, area, db)

        new_items = result.get("new_items", [])
        feed_info = result.get("feed_info", {})

        if not new_items:
            logger.info(
                "No new RSS items found for keyword detection",
                extra={
                    "area_id": str(area.id),
                    "feed_url": feed_url,
                    "total_items": result.get("total_items", 0),
                },
            )
            return

        # Filter items by keywords
        matching_items = []

        for item in new_items:
            keyword_matches = []

            # Check each specified field for keywords
            for field in check_fields:
                field_content = item.get(field, "")
                if field_content:
                    field_matches = [
                        kw for kw in keywords if kw.lower() in field_content.lower()
                    ]
                    keyword_matches.extend(field_matches)

            # Determine if item matches keyword criteria
            if match_all:
                # Must match ALL keywords
                unique_matches = set(kw.lower() for kw in keyword_matches)
                required_keywords = set(kw.lower() for kw in keywords)
                item_matches = required_keywords.issubset(unique_matches)
            else:
                # Must match ANY keyword
                item_matches = len(keyword_matches) > 0

            if item_matches:
                item["matched_keywords"] = list(
                    set(keyword_matches)
                )  # Remove duplicates
                matching_items.append(item)

        if not matching_items:
            logger.info(
                "No RSS items matched keywords",
                extra={
                    "area_id": str(area.id),
                    "feed_url": feed_url,
                    "keywords": keywords,
                    "new_items_count": len(new_items),
                },
            )
            return

        # Process each matching item
        for item in matching_items:
            # Populate event with RSS variables
            event.update(
                {
                    "rss.title": item.get("title", ""),
                    "rss.description": item.get("description", ""),
                    "rss.summary": item.get("summary", ""),
                    "rss.content": item.get("content", ""),
                    "rss.link": item.get("link", ""),
                    "rss.author": item.get("author", ""),
                    "rss.published": item.get("published", ""),
                    "rss.updated": item.get("updated", ""),
                    "rss.categories": ", ".join(item.get("categories", [])),
                    "rss.id": item.get("id", ""),
                    "rss.hash": item.get("hash", ""),
                    "rss.feed_title": feed_info.get("title", ""),
                    "rss.feed_url": feed_url,
                    "rss.feed_description": feed_info.get("description", ""),
                    "rss.matched_keywords": ", ".join(item.get("matched_keywords", [])),
                    "rss.keyword_match_count": len(item.get("matched_keywords", [])),
                }
            )

            # Store full RSS data including keyword matches
            event["rss_data"] = {
                "item": item,
                "feed_info": feed_info,
                "matched_keywords": item.get("matched_keywords", []),
                "trigger_type": "keyword_detected",
                "triggered_at": datetime.now().isoformat(),
            }

            logger.info(
                "RSS keyword detected trigger fired",
                extra={
                    "area_id": str(area.id),
                    "area_name": area.name,
                    "user_id": str(area.user_id),
                    "feed_url": feed_url,
                    "item_title": item.get("title"),
                    "item_link": item.get("link"),
                    "matched_keywords": item.get("matched_keywords", []),
                    "keyword_match_count": len(item.get("matched_keywords", [])),
                },
            )

        logger.info(
            "RSS keyword_detected trigger completed",
            extra={
                "area_id": str(area.id),
                "feed_url": feed_url,
                "total_new_items": len(new_items),
                "matching_items_count": len(matching_items),
                "keywords": keywords,
                "feed_title": feed_info.get("title", ""),
            },
        )

    except RSSError:
        # Re-raise RSS-specific errors
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for RSS keyword_detected trigger",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "RSS keyword_detected handler failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise RSSFeedError(f"RSS keyword detected handler failed: {str(e)}") from e


async def extract_feed_info_handler(
    area: Area, params: dict, event: dict, db: "Session" = None
) -> None:
    """Extract basic RSS feed information as a reaction.

    This reaction extracts metadata about an RSS feed without processing items.
    Useful for feed validation and information display.

    Args:
        area: The Area being executed
        params: Reaction parameters (feed_url)
        event: Event data dictionary (will be populated with feed info)
        db: Database session

    Raises:
        RSSFeedError: If feed parsing fails
        RSSConnectionError: If feed connection fails

    Example params:
        {"feed_url": "https://example.com/rss.xml"}
    """
    try:
        feed_url = params.get("feed_url")
        if not feed_url:
            raise ValueError("feed_url parameter is required")

        logger.info(
            "Extracting RSS feed information",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "feed_url": feed_url,
            },
        )

        # Parse feed without area (preview mode - no deduplication)
        result = await rss_feed_manager.parse_feed(feed_url, None, db)

        feed_info = result.get("feed_info", {})

        # Populate event with feed information
        event.update(
            {
                "rss.feed_title": feed_info.get("title", ""),
                "rss.feed_description": feed_info.get("description", ""),
                "rss.feed_link": feed_info.get("link", ""),
                "rss.feed_url": feed_url,
                "rss.feed_language": feed_info.get("language", ""),
                "rss.feed_generator": feed_info.get("generator", ""),
                "rss.feed_updated": feed_info.get("updated", ""),
                "rss.total_items": result.get("total_items", 0),
            }
        )

        # Store full feed data
        event["rss_feed_data"] = {
            "feed_info": feed_info,
            "total_items": result.get("total_items", 0),
            "extracted_at": datetime.now().isoformat(),
        }

        logger.info(
            "RSS feed information extracted",
            extra={
                "area_id": str(area.id),
                "feed_url": feed_url,
                "feed_title": feed_info.get("title", ""),
                "total_items": result.get("total_items", 0),
            },
        )

    except RSSError:
        # Re-raise RSS-specific errors
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for RSS feed info extraction",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "RSS feed info extraction failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise RSSFeedError(f"RSS feed info extraction failed: {str(e)}") from e


__all__ = [
    "rss_new_item_handler",
    "rss_keyword_detected_handler",
    "extract_feed_info_handler",
    "rss_feed_manager",
]
