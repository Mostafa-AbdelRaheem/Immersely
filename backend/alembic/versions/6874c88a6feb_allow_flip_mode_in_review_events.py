"""allow flip mode in review_events

Revision ID: 6874c88a6feb
Revises: 0578ca22844c
Create Date: 2026-10-31 22:07:29.358869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6874c88a6feb'
down_revision: Union[str, Sequence[str], None] = '0578ca22844c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = 'ck_review_events_mode_valid'
OLD_MODES = "mode in ('isolated','cloze_in_scene','free_production')"
NEW_MODES = "mode in ('isolated','cloze_in_scene','free_production','flip')"


def upgrade() -> None:
    """Allow 'flip' as a review_events.mode.

    Postgres can't edit a check constraint in place, so drop and recreate it.
    Alembic autogenerate doesn't detect check-constraint changes, which is why
    this migration is written by hand.
    """
    op.drop_constraint(CONSTRAINT, 'review_events', type_='check')
    op.create_check_constraint(CONSTRAINT, 'review_events', NEW_MODES)


def downgrade() -> None:
    """Restore the original three modes. Refuses to run if flip rows exist."""
    flip_rows = op.get_bind().execute(
        sa.text("select count(*) from review_events where mode = 'flip'")
    ).scalar()
    if flip_rows:
        raise RuntimeError(
            f"Cannot downgrade: {flip_rows} review_events rows use mode 'flip'. "
            "Delete or convert them first; refusing to drop review history."
        )
    op.drop_constraint(CONSTRAINT, 'review_events', type_='check')
    op.create_check_constraint(CONSTRAINT, 'review_events', OLD_MODES)