"""FastAPI から OpenAPI を YAML に書き出す。--check では保存済みの定義と照合する。"""

import argparse
from pathlib import Path

import yaml

from .main import app


DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT, help="出力先（既定は docs/openapi.yaml）")
    parser.add_argument("--check", action="store_true", help="ファイルを更新せず、生成結果との差を確認する")
    args = parser.parse_args()
    output: Path = args.output
    if output.suffix.lower() not in {".yaml", ".yml"}:
        parser.error("出力先の拡張子には .yaml または .yml を指定してください。")
    document = yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False)
    if args.check:
        if output.is_file() and output.read_text(encoding="utf-8") == document:
            print(f"Up to date: {output}")
            return 0
        print(f"Regenerate the OpenAPI document: {output}")
        return 1
    output.write_text(document, encoding="utf-8", newline="\n")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
