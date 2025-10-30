"""Create marketplace tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202510301200"
down_revision = "202510131645"  # Latest migration before marketplace
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create template_categories table
    op.create_table(
        "template_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_template_categories_name"),
        sa.UniqueConstraint("slug", name="uq_template_categories_slug"),
    )

    # Create template_tags table
    op.create_table(
        "template_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_template_tags_name"),
        sa.UniqueConstraint("slug", name="uq_template_tags_slug"),
    )
    op.create_index("ix_template_tags_name", "template_tags", ["name"])

    # Create published_templates table
    op.create_table(
        "published_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_area_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("publisher_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("template_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column("visibility", sa.String(length=50), nullable=False, server_default='public'),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default='0'),
        sa.Column("clone_count", sa.Integer(), nullable=False, server_default='0'),
        sa.Column("rating_average", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default='0'),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["original_area_id"],
            ["areas.id"],
            name="fk_published_templates_original_area_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["publisher_user_id"],
            ["users.id"],
            name="fk_published_templates_publisher_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_published_templates_approved_by_user_id",
            ondelete="SET NULL",
        ),
    )
    
    # Create indexes for published_templates
    op.create_index("ix_published_templates_publisher", "published_templates", ["publisher_user_id"])
    op.create_index("ix_published_templates_category", "published_templates", ["category"])
    op.create_index("ix_published_templates_status", "published_templates", ["status", "visibility"])
    op.create_index("ix_published_templates_usage", "published_templates", ["usage_count"])
    op.create_index("ix_published_templates_created_at", "published_templates", ["created_at"])
    # GIN index for full-text search
    op.create_index(
        "ix_published_templates_search",
        "published_templates",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create template_tag_mappings association table
    op.create_table(
        "template_tag_mappings",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("template_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["published_templates.id"],
            name="fk_template_tag_mappings_template_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["template_tags.id"],
            name="fk_template_tag_mappings_tag_id",
            ondelete="CASCADE",
        ),
    )

    # Create template_usage table
    op.create_table(
        "template_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_area_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["published_templates.id"],
            name="fk_template_usage_template_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_template_usage_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_area_id"],
            ["areas.id"],
            name="fk_template_usage_created_area_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_template_usage_template", "template_usage", ["template_id"])
    op.create_index("ix_template_usage_user", "template_usage", ["user_id"])

    # Create trigger for updated_at on published_templates (reuse existing function)
    op.execute("""
        CREATE TRIGGER update_published_templates_updated_at 
        BEFORE UPDATE ON published_templates 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create trigger to automatically update search_vector on insert/update
    op.execute("""
        CREATE OR REPLACE FUNCTION update_published_templates_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.long_description, '')), 'C');
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_published_templates_search_vector_trigger
        BEFORE INSERT OR UPDATE ON published_templates
        FOR EACH ROW
        EXECUTE FUNCTION update_published_templates_search_vector();
    """)


def downgrade() -> None:
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_published_templates_search_vector_trigger ON published_templates;")
    op.execute("DROP FUNCTION IF EXISTS update_published_templates_search_vector();")
    op.execute("DROP TRIGGER IF EXISTS update_published_templates_updated_at ON published_templates;")
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index("ix_template_usage_user", table_name="template_usage")
    op.drop_index("ix_template_usage_template", table_name="template_usage")
    op.drop_table("template_usage")
    
    op.drop_table("template_tag_mappings")
    
    op.drop_index("ix_published_templates_search", table_name="published_templates")
    op.drop_index("ix_published_templates_created_at", table_name="published_templates")
    op.drop_index("ix_published_templates_usage", table_name="published_templates")
    op.drop_index("ix_published_templates_status", table_name="published_templates")
    op.drop_index("ix_published_templates_category", table_name="published_templates")
    op.drop_index("ix_published_templates_publisher", table_name="published_templates")
    op.drop_table("published_templates")
    
    op.drop_index("ix_template_tags_name", table_name="template_tags")
    op.drop_table("template_tags")
    
    op.drop_table("template_categories")
