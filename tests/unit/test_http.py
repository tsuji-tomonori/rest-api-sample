"""エラー応答を作る関数を、HTTP サーバーやデータベースを起動せずに確かめる。"""

import json

from package.app.http import problem


def test_validation_problem_uses_the_http_status_and_rfc_title():
    response = problem(422, "件名を入力してください。")
    assert response.status_code == 422
    assert response.headers["Content-Type"] == "application/problem+json"
    assert json.loads(response.body) == {
        "type": "about:blank",
        "status": 422,
        "title": "Unprocessable Content",
        "detail": "件名を入力してください。",
    }


def test_method_not_allowed_preserves_the_allow_header():
    response = problem(405, "この操作は利用できません。", headers={"Allow": "GET, POST"})
    assert response.status_code == 405
    assert response.headers["Allow"] == "GET, POST"
