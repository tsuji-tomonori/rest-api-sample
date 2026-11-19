import asyncio
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from botocore.credentials import Credentials
from botocore.exceptions import ClientError

from package.infra import post_deploy


def migration_result(payload=b'{"migration":"up-to-date"}', **overrides):
    return {"StatusCode": 200, "Payload": io.BytesIO(payload), **overrides}


def test_synchronous_migration_requires_success_payload():
    client = Mock()
    client.invoke.return_value = migration_result()
    post_deploy.apply_migrations(client, "repair-migrate", post_deploy.SmokeReport().checks["migration"])
    client.invoke.assert_called_once_with(FunctionName="repair-migrate", InvocationType="RequestResponse", Payload=b"{}")


def test_migration_retries_a_pre_execution_iam_denial(monkeypatch):
    client = Mock()
    refused = ClientError({"Error": {"Code": "AccessDeniedException"}}, "Invoke")
    client.invoke.side_effect = [refused, migration_result()]
    monkeypatch.setattr(post_deploy, "sleep", lambda _: None)
    post_deploy.apply_migrations(client, "repair-migrate", post_deploy.SmokeReport().checks["migration"])
    assert client.invoke.call_count == 2


@pytest.mark.parametrize("result", [
    migration_result(FunctionError="Unhandled"), migration_result(StatusCode=202), migration_result(b"{}"),
])
def test_failed_migration_stops_deployment(result):
    client = Mock()
    client.invoke.return_value = result
    with pytest.raises(RuntimeError):
        post_deploy.apply_migrations(client, "repair-migrate", post_deploy.SmokeReport().checks["migration"])
    assert client.invoke.call_count == 1


REGION = "ap-northeast-1"
API = "https://api123.execute-api.ap-northeast-1.amazonaws.com"
CREDS = Credentials("example", "unit-test-secret", "unit-test-token")


def response(code=200, data=b'{"items":[],"next_after":null}', media_type="application/json"):
    return SimpleNamespace(status_code=code, content=data, headers={"Content-Type": media_type})


def test_smoke_signs_read_only_get_and_retries_transient_failure(monkeypatch):
    http = Mock()
    http.send.side_effect = [response(503), response()]
    monkeypatch.setattr(post_deploy, "sleep", lambda _: None)
    post_deploy.check_api(API, REGION, CREDS, http, post_deploy.SmokeReport().checks["list"])
    assert http.send.call_count == 2
    for call in http.send.call_args_list:
        request = call.args[0]
        assert (request.method, request.url) == ("GET", API + "/repair-requests?limit=1")
        assert "/ap-northeast-1/execute-api/aws4_request" in request.headers["Authorization"]
        assert request.headers["X-Amz-Security-Token"] == "unit-test-token"


@pytest.mark.parametrize("reply", [response(404), response(200, b"{}"), response(200, b"not-json")])
def test_failed_smoke_is_reported(reply):
    http = Mock()
    http.send.return_value = reply
    with pytest.raises(RuntimeError):
        post_deploy.check_api(API, REGION, CREDS, http, post_deploy.SmokeReport().checks["list"])


def test_smoke_rejects_unexpected_destination_before_signing():
    http = Mock()
    with pytest.raises(ValueError):
        post_deploy.check_api("https://example.org", REGION, CREDS, http, post_deploy.SmokeReport().checks["list"])
    http.send.assert_not_called()


@pytest.fixture
def deployed(tmp_path, monkeypatch):
    """Substitute AWS transport; use the normal signer, migration and response checks."""
    monkeypatch.delenv("DB_SECRET_ARN", raising=False)
    monkeypatch.delenv("DB_APP_SECRET_ARN", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'smoke.db').as_posix()}")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    outputs = tmp_path / "stack.json"
    outputs.write_text(json.dumps({"RepairApi": {"ApiUrl": API, "MigrateFunction": "fixture"}}), encoding="utf-8")
    session = Mock(region_name=REGION)
    session.get_credentials.return_value = CREDS
    session.client.return_value.invoke.return_value = migration_result()
    http = Mock()
    monkeypatch.setattr(post_deploy.boto3, "Session", lambda: session)
    monkeypatch.setattr(post_deploy, "URLLib3Session", lambda **kwargs: http)
    return outputs, tmp_path / "aws-smoke.json", summary, session, http


def test_reports_real_application_responses_through_lambda_adapter(deployed):
    from package.app.main import handler
    from package.db.migrate import handler as migrate

    outputs, report, summary, session, http = deployed
    session.client.return_value.invoke.side_effect = lambda **kwargs: migration_result(json.dumps(migrate({}, None)).encode())

    def send(request):
        path = urlsplit(request.url)
        if "Authorization" not in request.headers:
            return response(403)  # This boundary is supplied by IAM in a deployed environment.
        assert "/execute-api/aws4_request" in request.headers["Authorization"]
        event = {
            "version": "2.0", "rawPath": path.path, "rawQueryString": path.query,
            "headers": {"host": path.hostname},
            "requestContext": {"stage": "$default", "http": {
                "method": request.method, "path": path.path, "sourceIp": "127.0.0.1", "protocol": "HTTP/1.1",
            }},
        }
        with asyncio.Runner():
            result = handler(event, None)
        # API Gateway restores bytes when the Lambda proxy response marks its body as Base64.
        body = base64.b64decode(result["body"]) if result.get("isBase64Encoded") else result["body"].encode()
        return response(result["statusCode"], body, result["headers"]["content-type"])

    http.send.side_effect = send
    assert post_deploy.main([str(outputs), "--report", str(report)]) == 0
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["status"] == "passed"
    assert [c["actual_http"] for c in receipt["checks"]] == [200, 403, 200, 422]
    assert all(c["duration_ms"] >= 0 and c["attempts"] == 1 for c in receipt["checks"])
    assert "AWS 実環境の疎通確認" in summary.read_text(encoding="utf-8")


@pytest.mark.parametrize(("replies", "failed_case"), [
    ([response(200)], "iam"),
    ([response(403), response(200, b'{"items":[{"sensitive":"private-example"}]}')], "list"),
    ([response(403), response(), response(422, b"private-example", "text/html")], "invalid_limit"),
])
def test_failed_check_leaves_a_redacted_report_and_skips_later_checks(deployed, replies, failed_case):
    outputs, report, summary, session, http = deployed
    http.send.side_effect = replies
    assert post_deploy.main([str(outputs), "--smoke-only", "--report", str(report)]) == 1
    session.client.assert_not_called()
    assert http.send.call_count == len(replies)
    text = report.read_text(encoding="utf-8")
    receipt = json.loads(text)
    assert receipt["status"] == "failed" and receipt["reason"] == failed_case
    assert receipt["checks"][0]["status"] == "not_run"
    failed = next(i for i, case in enumerate(receipt["checks"]) if case["status"] == "failed")
    assert receipt["checks"][failed]["actual_http"] == replies[-1].status_code
    assert all(case["status"] == "not_run" for case in receipt["checks"][failed + 1:])
    for private in ("private-example", "unit-test-token", CREDS.secret_key, API):
        assert private not in text + summary.read_text(encoding="utf-8")


def test_unreadable_stack_outputs_produce_a_failed_report(deployed):
    outputs, report, summary, session, http = deployed
    assert post_deploy.main([str(Path(str(outputs) + ".missing")), "--report", str(report)]) == 1
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["reason"] == "setup_failed"
    assert all(case["status"] == "not_run" for case in receipt["checks"])
