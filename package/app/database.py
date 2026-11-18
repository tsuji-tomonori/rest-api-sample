import json
import os
from collections.abc import Iterator

from sqlalchemy import CheckConstraint, String, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


class RepairRequest(Base):
    __tablename__ = "repair_requests"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'completed')", name="ck_repair_requests_status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(16), server_default="open")


def database_url() -> URL:
    if "DB_SECRET_ARN" not in os.environ:
        return make_url(os.getenv("DATABASE_URL", "sqlite:///./repairs.db"))

    import boto3

    secret = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])
    credentials = json.loads(secret["SecretString"])
    return URL.create(
        "postgresql+psycopg",
        username=credentials["username"],
        password=credentials["password"],
        host=os.environ["DB_HOST"],
        port=5432,
        database=os.environ["DB_NAME"],
        query={"sslmode": "verify-full", "sslrootcert": "/opt/rds-global-bundle.pem"},
    )


def session() -> Iterator[Session]:
    # 教材では1回の要求で1接続を使い、終了時に閉じる。
    engine = create_engine(database_url(), poolclass=NullPool)
    with Session(engine, expire_on_commit=False) as db:
        yield db
