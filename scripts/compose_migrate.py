"""Compose 専用の一時 DB を用意し、API には読み書き用のロールを渡す。"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from package.db.app_role import grant_runtime_role
from package.db.migrate import upgrade


def main() -> None:
    owner = URL.create(
        "postgresql+psycopg", host="db", database="repairs", username="repair_admin",
        password=Path("/run/repair-admin/password").read_text().strip(),
    )
    os.environ["DATABASE_URL"] = owner.render_as_string(hide_password=False)
    upgrade()

    # この処理が完了してから Compose が API を起動する。
    with create_engine(owner, poolclass=NullPool).begin() as conn:
        grant_runtime_role(conn, Path("/run/repair-api/password").read_text().strip())


if __name__ == "__main__":
    main()
