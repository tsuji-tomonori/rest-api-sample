"""Export the FastAPI contract or compare it with a checked-in copy."""

import argparse
import json
from pathlib import Path

from .main import app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="path to the OpenAPI JSON file")
    parser.add_argument("--check", action="store_true", help="report an outdated file without writing it")
    args = parser.parse_args()
    # 同じ API からは同じファイルを生成する。キーの順序をそろえると、仕様の変更箇所を比較しやすい。
    document = json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    # CI は --check で生成結果と公開用ファイルを照合し、違いがあれば終了コード 1 で知らせる。
    if args.check:
        if args.output.is_file() and args.output.read_text(encoding="utf-8") == document:
            print(f"Up to date: {args.output}")
            return 0
        print(f"Regenerate the OpenAPI document: {args.output}")
        return 1

    args.output.write_text(document, encoding="utf-8", newline="\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
