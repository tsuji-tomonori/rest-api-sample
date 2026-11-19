"""修理依頼の台帳を作る。"""

from alembic import op
import sqlalchemy as sa

# この変更には版を表す ID を付ける。初版なので、一つ前の版はない。
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
        # 削除済みの受付番号を別の依頼に割り当てると、古い URL が別の依頼を指してしまう。
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("repair_requests")
