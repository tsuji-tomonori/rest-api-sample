"""Compose の一時 DB と別プロセスの API を使い、利用者から見た業務フローを検証する。"""

import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


pytestmark = pytest.mark.skipif(
    os.getenv("REPAIR_COMPOSE_TEST") != "1", reason="run with docker compose run --rm integration"
)


@pytest.fixture()
def api():
    # Compose のサービス名を使う。通常の開発用 URL に誤って書き込まない。
    with httpx.Client(base_url="http://api:8000", timeout=10, trust_env=False) as client:
        yield client


@pytest.fixture()
def database():
    url = URL.create(
        "postgresql+psycopg", host="db", database="repairs", username="repair_api",
        password=Path("/run/repair-api/password").read_text().strip(),
    )
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def test_repair_from_registration_to_deletion(api, database):
    # 同時に別のテストが動いても、自分が登録した依頼だけを追跡する。
    title = f"椅子の脚の修理 {uuid4().hex}"
    created = api.post("/repair-requests", json={"title": title, "location": "会議室A"})
    assert created.status_code == 201
    repair = created.json()
    request_id = repair["id"]
    path = f"/repair-requests/{request_id}"
    assert created.headers["Location"] == path
    try:
        assert repair == {"id": request_id, "title": title, "location": "会議室A", "status": "open"}
        assert api.get(path).json() == repair

        # 入力に失敗したあとも元の状態を読めるか、実際の HTTP 境界を越えて確認する。
        rejected = api.patch(path, json={"status": "unknown"})
        assert rejected.status_code == 422
        assert rejected.headers["Content-Type"] == "application/problem+json"
        assert api.get(path).json()["status"] == "open"

        updated = api.patch(path, json={"status": "completed"})
        assert updated.status_code == 200
        assert updated.json() == {**repair, "status": "completed"}
        query = text("SELECT status FROM repair_requests WHERE id = :id")
        with database.connect() as conn:
            # 別の DB 接続から見えれば、API の更新は PostgreSQL で確定している。
            assert conn.scalar(query, {"id": request_id}) == "completed"

        removed = api.delete(path)
        assert removed.status_code == 204
        assert removed.content == b""
        assert api.delete(path).status_code == 404
        assert api.get(path).status_code == 404
        with database.connect() as conn:
            assert conn.scalar(query, {"id": request_id}) is None
    finally:
        api.delete(path)
