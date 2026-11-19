"""Compose で動いている API の応答を、教材で公開する OpenAPI 定義と照合する。"""

import re
from pathlib import Path

import requests
import schemathesis
from hypothesis import Phase, example, given, settings


BASE_URL = "http://127.0.0.1:8000"
CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
COLLECTION = "/repair-requests"
DETAIL = "/repair-requests/{request_id}"


def check_docs(session, contract):
    page = session.get(f"{BASE_URL}/docs", timeout=10)
    page.raise_for_status()
    assert page.headers["Content-Type"].startswith("text/html")
    assert 'id="swagger-ui"' in page.text and "SwaggerUIBundle(" in page.text
    match = re.search(r"""\burl\s*:\s*["']([^"']+)["']""", page.text)
    assert match and match[1] == "/openapi.json", "Swagger UI should load /openapi.json"
    published = session.get(BASE_URL + match[1], timeout=10)
    published.raise_for_status()
    assert published.json() == contract.raw_schema, "Published OpenAPI differs from docs/openapi.json"


def check_api(session, contract):
    covered = set()

    def call(method, path, expected, *, request_id=None, **kwargs):
        url = BASE_URL + (path if request_id is None else path.format(request_id=request_id))
        response = session.request(method, url, timeout=10, allow_redirects=False, **kwargs)
        assert response.status_code == expected, f"{method} {url}: {response.status_code} {response.text}"
        assert str(expected) in contract.raw_schema["paths"][path][method.lower()]["responses"]
        if expected == 204:
            assert response.content == b"", "204 must have an empty body"
        else:
            media_type = "application/problem+json" if expected == 404 else "application/json"
            assert response.headers["Content-Type"].split(";")[0].strip() == media_type
        contract[path][method].validate_response(response)
        if 200 <= expected < 300:
            covered.add((method, path))
        return response

    submission = {"title": "契約テスト用の椅子", "location": "第2会議室"}
    created = call("POST", COLLECTION, 201, json=submission)
    repair_id = created.json()["id"]
    removed = False
    try:
        assert created.headers["Location"] == f"{COLLECTION}/{repair_id}"
        repair = {**submission, "id": repair_id, "status": "open"}
        assert created.json() == repair
        assert call("GET", DETAIL, 200, request_id=repair_id).json() == repair

        # 手動で登録した依頼がすでにあっても、このテストの1件から一覧を読み始める。
        params = {"status": "open", "limit": 1}
        if repair_id > 1:
            params["after"] = repair_id - 1
        page = call("GET", COLLECTION, 200, params=params).json()
        assert page["items"] == [repair]

        # 契約に列挙された状態から更新値を作り、先ほど登録した依頼だけを変更する。
        changes = contract[DETAIL]["PATCH"].as_strategy(path_parameters={"request_id": repair_id})

        @settings(max_examples=4, deadline=None, derandomize=True, phases=(Phase.explicit, Phase.generate))
        @example(status="completed")
        @given(status=changes.map(lambda case: case.body["status"]))
        def check_update(status):
            changed = call("PATCH", DETAIL, 200, request_id=repair_id, json={"status": status})
            assert changed.json() == {**repair, "status": status}
            assert call("GET", DETAIL, 200, request_id=repair_id).json() == changed.json()

        check_update()
        call("DELETE", DETAIL, 204, request_id=repair_id)
        removed = True
        missing = call("GET", DETAIL, 404, request_id=repair_id)
        assert missing.json()["status"] == 404
    finally:
        if not removed:
            cleanup = session.delete(f"{BASE_URL}{COLLECTION}/{repair_id}", timeout=10)
            if cleanup.status_code != 404:
                cleanup.raise_for_status()

    methods = {"get", "post", "patch", "put", "delete", "head", "options", "trace"}
    documented = {
        (method.upper(), path)
        for path, item in contract.raw_schema["paths"].items()
        for method in item if method in methods
    }
    assert covered == documented, f"Operations without a successful response: {documented - covered}"


if __name__ == "__main__":
    contract = schemathesis.openapi.from_path(CONTRACT)
    with requests.Session() as session:
        check_docs(session, contract)
        check_api(session, contract)
    print("Swagger UI and OpenAPI match. All documented operations passed the live lifecycle check.")
