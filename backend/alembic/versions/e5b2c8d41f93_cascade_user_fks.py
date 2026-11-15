"""cascade user foreign keys

Revision ID: e5b2c8d41f93
Revises: d7e1b4a08c52
Create Date: 2026-11-14

"""
from alembic import op

revision = "e5b2c8d41f93"
down_revision = "d7e1b4a08c52"
branch_labels = None
depends_on = None

# (table, constraint name) - names measured from pg_constraint on the real DB.
_FKS = [
    ("refresh_tokens", "refresh_tokens_user_id_fkey"),
    ("sentences", "sentences_user_id_fkey"),
    ("scenes", "scenes_user_id_fkey"),
    ("review_events", "review_events_user_id_fkey"),
]


def upgrade() -> None:
    for table, name in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name, table, "users", ["user_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    for table, name in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "users", ["user_id"], ["id"])