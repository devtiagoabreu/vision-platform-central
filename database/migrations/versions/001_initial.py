"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.String(128), nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("camera_id", sa.String(64), nullable=False),
        sa.Column("captured_at", sa.String(), nullable=False),
        sa.Column("image_uri", sa.String(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("algorithm_version", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_observations_observation_id", "image_observations", ["observation_id"], unique=True)
    op.create_index("ix_image_observations_local_id", "image_observations", ["local_id"])
    op.create_index("ix_image_observations_camera_id", "image_observations", ["camera_id"])
    op.create_index("ix_image_observations_status", "image_observations", ["status"])

    op.create_table(
        "locals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("local_name", sa.String(128), nullable=False),
        sa.Column("api_url", sa.String(256), nullable=False),
        sa.Column("api_token", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locals_local_id", "locals", ["local_id"], unique=True)


def downgrade() -> None:
    op.drop_table("locals")
    op.drop_table("image_observations")
