"""FastAPI から OpenAPI を書き出す。--check では保存済みの定義と照合する。"""

import argparse
import json
from pathlib import Path

from .main import app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", nargs="+", type=Path, help="出力先。拡張子 .yaml と .yml は YAML、それ以外は JSON")
    parser.add_argument("--check", action="store_true", help="ファイルを更新せず、生成結果との差を確認する")
    args = parser.parse_args()
    schema = app.openapi()
    result = 0
    for output in args.outputs:
        if output.suffix.lower() in {".yaml", ".yml"}:
            import yaml

            document = yaml.safe_dump(schema, allow_unicode=True, sort_keys=False)
        else:
            document = json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

        # CI ではすべての出力先を調べ、一つでも古ければ終了コード 1 を返す。
        if not args.check:
            output.write_text(document, encoding="utf-8", newline="\n")
            print(f"Wrote {output}")
        elif output.is_file() and output.read_text(encoding="utf-8") == document:
            print(f"Up to date: {output}")
        else:
            print(f"Regenerate the OpenAPI document: {output}")
            result = 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
