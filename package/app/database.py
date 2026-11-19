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
    # 修理依頼1件がテーブルの1行に対応する。SQLite でも削除した依頼の ID は再利用しない。
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
    # 手元では SQLite で始められる。別のデータベースで試すときは DATABASE_URL を指定する。
    if "DB_SECRET_ARN" not in os.environ:
        return make_url(os.getenv("DATABASE_URL", "sqlite:///./repairs.db"))

    import boto3

    # AWS では Secrets Manager から認証情報を取得し、CDK が渡した Aurora の接続先と組み合わせる。
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
    # yield でセッションを渡し、処理が終わると with を抜ける。NullPool は使い終えた接続を閉じる。
    engine = create_engine(database_url(), poolclass=NullPool)
    # 登録・更新を確定した後も、同じ行の値を使って応答を組み立てられる。
    with Session(engine, expire_on_commit=False) as db:
        yield db
