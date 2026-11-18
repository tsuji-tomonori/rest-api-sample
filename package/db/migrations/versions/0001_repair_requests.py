"""Create the repair request register."""

from alembic import op
import sqlalchemy as sa

revision = "0001_repair_requests"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repair_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.CheckConstraint("status IN ('open', 'completed')", name="ck_repair_requests_status"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("repair_requests")
