"""Apply all pending database revisions from the CLI or a Lambda invocation."""

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
            # Start a real SQLite transaction before the first schema change.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            # Serialize concurrent upgrades until this PostgreSQL transaction ends.
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(78452701)")
        config.attributes["connection"] = connection
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
