import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from botocore.credentials import Credentials

from package.infra import post_deploy


def migration_result(payload=b'{"migration":"up-to-date"}', **overrides):
    return {"StatusCode": 200, "Payload": io.BytesIO(payload), **overrides}


def test_synchronous_migration_requires_success_payload():
    client = Mock()
    client.invoke.return_value = migration_result()
    post_deploy.apply_migrations(client, "repair-migrate")
    client.invoke.assert_called_once_with(FunctionName="repair-migrate", InvocationType="RequestResponse", Payload=b"{}")


@pytest.mark.parametrize("result", [
    migration_result(FunctionError="Unhandled"), migration_result(StatusCode=202), migration_result(b"{}"),
])
def test_failed_migration_stops_deployment(result):
    client = Mock()
    client.invoke.return_value = result
    with pytest.raises(RuntimeError):
        post_deploy.apply_migrations(client, "repair-migrate")


REGION = "ap-northeast-1"
API = "https://api123.execute-api.ap-northeast-1.amazonaws.com"
CREDS = Credentials("example", "unit-test-secret", "unit-test-token")


def response(code=200, data=b'{"items":[],"next_after":null}'):
    return SimpleNamespace(status_code=code, content=data)


def test_smoke_signs_read_only_get_and_retries_transient_failure(monkeypatch):
    http = Mock()
    http.send.side_effect = [response(503), response()]
    monkeypatch.setattr(post_deploy, "sleep", lambda _: None)
    post_deploy.check_api(API, REGION, CREDS, http)
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
        post_deploy.check_api(API, REGION, CREDS, http)


def test_smoke_rejects_unexpected_destination_before_signing():
    http = Mock()
    with pytest.raises(ValueError):
        post_deploy.check_api("https://example.org", REGION, CREDS, http)
    http.send.assert_not_called()
