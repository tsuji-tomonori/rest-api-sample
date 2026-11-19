"""実装編の最初のルートを、読者と同じ掲載コードで動かす。"""

import re
import runpy
from pathlib import Path

from fastapi.testclient import TestClient


def test_first_route_returns_the_documented_responses(tmp_path: Path):
    guide = Path(__file__).resolve().parents[2] / "docs/implementation/README.md"
    markdown = guide.read_text(encoding="utf-8")
    snippet = re.search(r"^```python\n(.*?)^```$", markdown, re.MULTILINE | re.DOTALL)
    assert snippet, "実装編 README の Python コードが見つかりません"

    # 読者が保存するファイルをそのまま読み込み、2本の curl 例と同じ URL を呼ぶ。
    route_file = tmp_path / "first_route.py"
    route_file.write_text(snippet.group(1), encoding="utf-8")
    with TestClient(runpy.run_path(str(route_file))["app"]) as client:
        found = client.get("/repair-requests/42")
        assert found.status_code == 200
        assert found.json() == {"id": 42, "title": "椅子がぐらつく"}
        assert client.get("/repair-requests/43").status_code == 404
