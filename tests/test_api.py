import pytest
from fastapi.testclient import TestClient

from package.app.main import app
from package.db.migrate import upgrade


COLLECTION = "/repair-requests"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_SECRET_ARN", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'repairs.db').as_posix()}")
    upgrade()
    with TestClient(app) as test_client:
        yield test_client


def create(client, title="椅子の脚がぐらつく"):
    response = client.post(COLLECTION, json={"title": title, "location": "会議室A"})
    assert response.status_code == 201
    return response


def test_lifecycle(client):
    created = create(client, "  椅子の脚がぐらつく  ")
    location = created.headers["Location"]
    record = created.json()
    assert record == {"id": 1, "title": "椅子の脚がぐらつく", "location": "会議室A", "status": "open"}
    assert location == f"{COLLECTION}/1"
    assert client.get(location).json() == record
    assert client.get(location).headers["Cache-Control"] == "no-store"

    completed = client.patch(location, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json() == {**record, "status": "completed"}
    assert client.get(COLLECTION, params={"status": "open"}).json() == {"items": [], "next_after": None}

    removed = client.delete(location)
    assert removed.status_code == 204
    assert removed.content == b""
    assert client.delete(location).status_code == 404
    missing = client.get(location)
    assert missing.status_code == 404
    assert missing.headers["Content-Type"] == "application/problem+json"
    assert missing.json() == {
        "type": "about:blank", "title": "Not Found", "status": 404, "detail": "修理依頼が見つかりません。"
    }
    assert create(client).headers["Location"] != location


def test_filtered_pages_continue_after_deleted_cursor(client):
    locations = [create(client, str(i)).headers["Location"] for i in range(5)]
    client.patch(locations[1], json={"status": "completed"})
    first = client.get(COLLECTION, params={"status": "open", "limit": 2}).json()
    assert [r["id"] for r in first["items"]] == [1, 3]
    assert first["next_after"] == 3
    client.delete(locations[2])

    second = client.get(COLLECTION, params={"status": "open", "limit": 2, "after": first["next_after"]}).json()
    assert [r["id"] for r in second["items"]] == [4, 5]
    assert second["next_after"] is None


@pytest.mark.parametrize("body", [
    {"title": "   ", "location": "A"},
    {"title": "椅子", "location": "A" * 101},
    {"title": "椅子\x00", "location": "A"},
    {"title": "椅子"},
    {"title": "椅子", "location": "A", "status": "completed"},
])
def test_invalid_create_does_not_insert(client, body):
    response = client.post(COLLECTION, json=body)
    assert response.status_code == 422
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json()["status"] == 422
    assert client.get(COLLECTION).json()["items"] == []


@pytest.mark.parametrize(("path", "code"), [
    ("?limit=0", 422), ("?limit=101", 422), ("?after=0", 422),
    ("?status=done", 422), ("?after=99999999999999999999", 422),
    ("/0", 422), ("/2147483648", 422), ("/42", 404),
])
def test_read_errors(client, path, code):
    response = client.get(COLLECTION + path)
    assert response.status_code == code
    assert response.json()["status"] == code


def test_body_format_and_failed_update(client):
    malformed = client.post(COLLECTION, content="{", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 400
    for headers in ({}, {"Content-Type": "text/plain"}):
        assert client.post(COLLECTION, content=b"{}", headers=headers).status_code == 415
    location = create(client).headers["Location"]
    for data in ({}, {"status": "done"}, {"status": "completed", "title": "変更"}):
        assert client.patch(location, json=data).status_code == 422
    assert client.get(location).json()["status"] == "open"
    assert client.patch(f"{COLLECTION}/42", json={"status": "completed"}).status_code == 404


def test_openapi_matches_error_media_type_and_creation(client):
    paths = client.get("/openapi.json").json()["paths"]
    responses = paths[COLLECTION]["post"]["responses"]
    assert "Location" in responses["201"]["headers"]
    assert set(responses["201"]["content"]) == {"application/json"}
    for code in ("400", "415", "422"):
        assert set(responses[code]["content"]) == {"application/problem+json"}
    assert "content" not in paths[COLLECTION + "/{request_id}"]["delete"]["responses"]["204"]
