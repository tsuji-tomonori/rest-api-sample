"""手元のコマンドと移行用 Lambda から、同じ手順で DB を最新版にする。"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from package.app.database import database_url


def upgrade() -> None:
    engine = create_engine(database_url(), poolclass=NullPool)
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            # SQLite は最初に書き込み権を確保し、同時に起動した移行処理を待たせる。
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            # PostgreSQL は移行処理で共有する番号をロックし、トランザクション終了時に解放する。
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(78452701)")
        config.attributes["connection"] = connection
        # Alembic が DB に記録された版を読み、最新版までの未適用分だけを実行する。
        command.upgrade(config, "head")

        if app_secret := os.environ.get("DB_APP_SECRET_ARN"):
            from package.db.app_role import grant_api_access

            grant_api_access(connection, app_secret)


def handler(event, context):
    upgrade()
    return {"migration": "up-to-date"}


if __name__ == "__main__":
    upgrade()
    print("Database is up to date.")
