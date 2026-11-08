"""Use timezone-aware timestamp columns.

Revision ID: 002_timezone_aware_datetimes
Revises: 001_initial_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "002_timezone_aware_datetimes"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

TABLES_AND_COLUMNS = {
    "users": ("created_at", "updated_at"),
    "user_profiles": ("date_of_birth",),
    "activation_tokens": ("expires_at",),
    "password_reset_tokens": ("expires_at",),
    "refresh_tokens": ("expires_at",),
    "favorites": ("added_at",),
    "ratings": ("created_at",),
    "comments": ("created_at", "updated_at"),
    "comment_likes": ("created_at",),
    "movie_reactions": ("created_at",),
    "notifications": ("created_at",),
    "cart_items": ("added_at",),
}


def upgrade() -> None:
    """Convert timestamp columns to TIMESTAMP WITH TIME ZONE."""
    for table, columns in TABLES_AND_COLUMNS.items():
        for column in columns:
            op.alter_column(
                table, column, type_=sa.DateTime(timezone=True), postgresql_using=f"{column} AT TIME ZONE 'UTC'"
            )


def downgrade() -> None:
    """Convert timestamp columns back to timezone-naive values."""
    for table, columns in TABLES_AND_COLUMNS.items():
        for column in columns:
            op.alter_column(
                table, column, type_=sa.DateTime(timezone=False), postgresql_using=f"{column} AT TIME ZONE 'UTC'"
            )
