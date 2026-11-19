"""第7章の仕様書は抜粋。掲載した項目が配布 YAML と食い違ったら知らせる。"""

import re
from pathlib import Path

import yaml


DOCS = Path(__file__).resolve().parents[2] / "docs"


def assert_excerpt(example, published, path=""):
    if isinstance(example, dict):
        for key, value in example.items():
            assert key in published, f"Missing in openapi.yaml: {path}/{key}"
            assert_excerpt(value, published[key], f"{path}/{key}")
    elif isinstance(example, list):
        assert len(example) == len(published), path
        for index, value in enumerate(example):
            assert_excerpt(value, published[index], f"{path}/{index}")
    else:
        assert published == example, path


def test_chapter_seven_yaml_matches_the_published_operations_and_schemas():
    chapter = (DOCS / "07-openapi.md").read_text(encoding="utf-8")
    published = yaml.safe_load((DOCS / "openapi.yaml").read_text(encoding="utf-8"))
    snippets = re.findall(r"^```yaml\n(.*?)^```$", chapter, re.MULTILINE | re.DOTALL)
    assert snippets, "第7章の YAML の抜粋が見つかりません"
    for snippet in snippets:
        assert_excerpt(yaml.safe_load(snippet), published)
