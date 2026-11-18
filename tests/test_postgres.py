"""Set TEST_POSTGRES_URL to the owner URL of a fresh, disposable PostgreSQL cluster."""

import json
import os
import secrets

import boto3
import pytest
from botocore.stub import Stubber
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

from package.db.migrate import upgrade


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"), reason="requires a disposable PostgreSQL cluster"
)
def test_migration_grants_runtime_crud_and_reserves_ddl_for_owner(monkeypatch):
    owner_url = os.environ["TEST_POSTGRES_URL"]
    secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:repair-api-test"
    password = secrets.token_urlsafe(32)
    runtime_url = make_url(owner_url).set(username="repair_api", password=password)
    monkeypatch.setenv("DATABASE_URL", owner_url)
    monkeypatch.delenv("DB_SECRET_ARN", raising=False)
    monkeypatch.setenv("DB_APP_SECRET_ARN", secret_arn)

    # Use a local stub for the AWS secret and a real PostgreSQL connection for all SQL.
    client = boto3.client(
        "secretsmanager", region_name="us-east-1",
        aws_access_key_id="test", aws_secret_access_key="test",
    )
    monkeypatch.setattr(boto3, "client", lambda service: client)
    with Stubber(client) as stub:
        for _ in range(2):
            stub.add_response(
                "get_secret_value",
                {"SecretString": json.dumps({"username": "repair_api", "password": password})},
                {"SecretId": secret_arn},
            )
            upgrade()
        stub.assert_no_pending_responses()

    engine = create_engine(runtime_url)
    try:
        with engine.begin() as conn:
            owner = conn.scalar(text(
                "SELECT tableowner FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = 'repair_requests'"
            ))
            assert owner == make_url(owner_url).username
            assert conn.scalar(text("SELECT current_user")) == "repair_api"
            request_id = conn.scalar(text(
                "INSERT INTO public.repair_requests (title, location) "
                "VALUES ('Chair', 'East room') RETURNING id"
            ))
            key = {"id": request_id}
            status = conn.scalar(text("SELECT status FROM public.repair_requests WHERE id = :id"), key)
            assert status == "open"
            updated = conn.scalar(text(
                "UPDATE public.repair_requests SET status = 'completed' WHERE id = :id RETURNING status"
            ), key)
            assert updated == "completed"
            deleted = conn.scalar(text("DELETE FROM public.repair_requests WHERE id = :id RETURNING id"), key)
            assert deleted == request_id

        with pytest.raises(ProgrammingError) as denied:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE public.repair_requests ADD COLUMN internal_note text"))
        assert denied.value.orig.sqlstate == "42501"  # insufficient_privilege
    finally:
        engine.dispose()
