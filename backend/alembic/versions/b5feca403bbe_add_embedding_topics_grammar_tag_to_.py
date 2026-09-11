"""add embedding topics grammar_tag to sentences

Revision ID: b5feca403bbe
Revises: 0d0f79cf2f59
Create Date: 2026-09-08 22:35:44.227358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'b5feca403bbe'
down_revision: Union[str, Sequence[str], None] = '0d0f79cf2f59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "sentences",
        sa.Column(
            "topics",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "sentences",
        sa.Column("grammar_tag", sa.Text(), nullable=True),
    )
    op.add_column(
        "sentences",
        sa.Column("embedding", Vector(768), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sentences", "embedding")
    op.drop_column("sentences", "grammar_tag")
    op.drop_column("sentences", "topics")
    # Deliberately NOT dropping the vector extension here — it's shared
    # infrastructure, not scoped to this migration. See explanation above.