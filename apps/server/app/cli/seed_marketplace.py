"""Seed default categories and tags for marketplace."""

import click
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
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
    "email",
    "gmail",
    "slack",
    "discord",
    "github",
    "gitlab",
    "google-drive",
    "dropbox",
    "calendar",
    "google-calendar",
    "notion",
    "trello",
    "asana",
    "jira",
    "automation",
    "productivity",
    "notifications",
    "backup",
    "sync",
    "reporting",
    "monitoring",
    "alerts",
    "webhooks",
    "api",
    "integration",
    "workflow",
    "task-management",
    "time-tracking",
    "project-management",
    "team-collaboration",
]


def seed_categories(db: Session) -> None:
    """Seed default categories into the database."""
    click.echo("Seeding categories...")
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if category already exists
        existing = db.query(TemplateCategory).filter(
            TemplateCategory.slug == cat_data["slug"]
        ).first()
        
        if existing:
            click.echo(f"  ⏭️  Category '{cat_data['name']}' already exists, skipping")
            continue
        
        category = TemplateCategory(**cat_data)
        db.add(category)
        click.echo(f"  ✅ Created category: {cat_data['name']}")
    
    db.commit()
    click.echo(f"✨ Categories seeded successfully!")


def seed_tags(db: Session) -> None:
    """Seed default tags into the database."""
    click.echo("\nSeeding tags...")
    
    for tag_name in DEFAULT_TAGS:
        # Check if tag already exists
        existing = db.query(TemplateTag).filter(
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
        db.add(tag)
    
    db.commit()
    click.echo(f"✨ {len(DEFAULT_TAGS)} tags seeded successfully!")


@click.command()
def seed_marketplace() -> None:
    """Seed marketplace with default categories and tags."""
    click.echo("🌱 Seeding marketplace data...\n")
    
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_tags(db)
        click.echo("\n✅ Marketplace seeding complete!")
    except Exception as e:
        click.echo(f"\n❌ Error seeding marketplace: {e}", err=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_marketplace()

```