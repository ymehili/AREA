#!/usr/bin/env python3
"""Quick script to seed marketplace categories and tags."""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models to ensure relationships are loaded
from app.db.session import SessionLocal
from app.models import marketplace_template, template_category, template_tag, template_usage
from app.models.template_category import TemplateCategory
from app.models.template_tag import TemplateTag


DEFAULT_CATEGORIES = [
    {
        "name": "Productivity",
        "slug": "productivity",
        "description": "Templates to boost your productivity and automate repetitive tasks",
        "icon": "💼",
        "display_order": 1,
    },
    {
        "name": "Communication",
        "slug": "communication",
        "description": "Email, messaging, and notification automation templates",
        "icon": "💬",
        "display_order": 2,
    },
    {
        "name": "Development",
        "slug": "development",
        "description": "DevOps, CI/CD, and code management automation templates",
        "icon": "⚙️",
        "display_order": 3,
    },
    {
        "name": "Social Media",
        "slug": "social-media",
        "description": "Social media posting, monitoring, and engagement templates",
        "icon": "📱",
        "display_order": 4,
    },
    {
        "name": "Data & Analytics",
        "slug": "data-analytics",
        "description": "Data collection, analysis, and reporting templates",
        "icon": "📊",
        "display_order": 5,
    },
    {
        "name": "Marketing",
        "slug": "marketing",
        "description": "Marketing automation, lead generation, and campaign management",
        "icon": "📈",
        "display_order": 6,
    },
    {
        "name": "E-commerce",
        "slug": "ecommerce",
        "description": "Online store management and order processing templates",
        "icon": "🛒",
        "display_order": 7,
    },
    {
        "name": "Finance",
        "slug": "finance",
        "description": "Financial tracking, reporting, and payment automation",
        "icon": "💰",
        "display_order": 8,
    },
    {
        "name": "Education",
        "slug": "education",
        "description": "Learning management and educational content automation",
        "icon": "📚",
        "display_order": 9,
    },
    {
        "name": "Utilities",
        "slug": "utilities",
        "description": "General purpose automation templates and helpers",
        "icon": "🔧",
        "display_order": 10,
    },
]

DEFAULT_TAGS = [
    "email", "gmail", "slack", "discord", "github", "gitlab",
    "google-drive", "dropbox", "calendar", "google-calendar",
    "notion", "trello", "asana", "jira", "automation",
    "productivity", "notifications", "backup", "sync",
    "reporting", "monitoring", "alerts", "webhooks", "api",
    "integration", "workflow", "task-management",
    "time-tracking", "project-management", "team-collaboration",
]


def seed_marketplace_data(db_session=None):
    """Seed marketplace with default categories and tags.

    Args:
        db_session: Optional database session. If None, creates a new session.

    Returns:
        tuple: (created_categories, created_tags) counts
    """
    close_session = False
    if db_session is None:
        db_session = SessionLocal()
        close_session = True

    try:
        # Seed categories
        created_categories = 0
        for cat_data in DEFAULT_CATEGORIES:
            existing = db_session.query(TemplateCategory).filter(
                TemplateCategory.slug == cat_data["slug"]
            ).first()

            if existing:
                continue

            category = TemplateCategory(**cat_data)
            db_session.add(category)
            created_categories += 1

        db_session.commit()

        # Seed tags
        created_tags = 0
        for tag_name in DEFAULT_TAGS:
            existing = db_session.query(TemplateTag).filter(
                TemplateTag.name == tag_name
            ).first()

            if existing:
                continue

            slug = tag_name.lower().replace(" ", "-")
            tag = TemplateTag(
                name=tag_name,
                slug=slug,
                usage_count=0,
            )
            db_session.add(tag)
            created_tags += 1

        db_session.commit()

        return created_categories, created_tags

    except Exception as e:
        db_session.rollback()
        raise
    finally:
        if close_session:
            db_session.close()


def main():
    """Seed marketplace with default categories and tags (CLI entry point)."""
    print("🌱 Seeding marketplace data...\n")

    try:
        print("Seeding categories and tags...")
        created_categories, created_tags = seed_marketplace_data()

        print(f"\n✨ {created_categories} categories seeded!")
        print(f"✨ {created_tags} tags seeded!\n")
        print("✅ Marketplace seeding complete!")

    except Exception as e:
        print(f"\n❌ Error seeding marketplace: {e}")
        raise


if __name__ == "__main__":
    main()
