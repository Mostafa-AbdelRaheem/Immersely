"""add email_tokens table

Revision ID: d7e1b4a08c52
Revises: c3a9f1d27e40
Create Date: 2026-11-09 20:00:00.000000

Hand-written. The purpose values are a frozen copy on purpose: later edits to
the TokenPurpose enum must never change what this migration does.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7e1b4a08c52'
down_revision: Union[str, Sequence[str], None] = 'c3a9f1d27e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'email_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('verify_email', 'reset_password')",
            name='ck_email_tokens_purpose',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='email_tokens_token_hash_key'),
    )
    op.create_index(
        'ix_email_tokens_user_purpose', 'email_tokens', ['user_id', 'purpose'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_email_tokens_user_purpose', table_name='email_tokens')
    op.drop_table('email_tokens')