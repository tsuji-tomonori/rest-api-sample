"""Record the outcome of the AWS checks without publishing requests or business data."""

import argparse
import json
import os
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic


CASES = {
    "migration": ("マイグレーション Lambda の完了", 200),
    "iam": ("署名なしの一覧取得を拒否", 403),
    "list": ("署名付きで Aurora の一覧を取得", 200),
    "invalid_limit": ("入力エラーを Problem Details で取得", 422),
}


class CheckFailed(RuntimeError):
    """A fixed error code that may safely be published in the report."""


@dataclass
class Check:
    id: str
    expected_http: int
    status: str = "not_run"
    actual_http: int | None = None
    attempts: int = 0
    duration_ms: int | None = None
    error: str | None = None

    @contextmanager
    def run(self):
        started = monotonic()
        try:
            yield self
        except Exception as error:
            self.status = "failed"
            self.error = str(error) if isinstance(error, CheckFailed) else "operation_error"
            raise
        else:
            self.status = "passed"
        finally:
            self.duration_ms = round((monotonic() - started) * 1000)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SmokeReport:
    def __init__(self):
        self.started_at = utc_now()
        self.checks = {name: Check(name, expected) for name, (_, expected) in CASES.items()}

    def write(self, path: Path, status: str, reason: str | None = None) -> None:
        revision = os.environ.get("VERIFIED_SHA", "")
        data = {
            "schema_version": 1, "target": "aws", "status": status, "reason": reason,
            "revision": revision if re.fullmatch("[a-f0-9]{40}", revision) else None,
            "started_at": self.started_at, "finished_at": utc_now(),
            "checks": [asdict(check) for check in self.checks.values()],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = [
            "## AWS 実環境の疎通確認", "", f"結果 **{status}**" + (f"（`{reason}`）" if reason else ""),
            "", "| 確認項目 | 結果 | HTTP 期待 / 実測 | 試行 | ミリ秒 | エラー |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
        for check in self.checks.values():
            lines.append(
                f"| {CASES[check.id][0]} | {check.status} | {check.expected_http} / {check.actual_http or '—'} "
                f"| {check.attempts} | {check.duration_ms if check.duration_ms is not None else '—'} | {check.error or '—'} |"
            )
        summary = "\n".join(lines) + "\n"
        if destination := os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(destination).open("a", encoding="utf-8") as file:
                file.write(summary)
        print(f"AWS smoke: {status}" + (f" ({reason})" if reason else ""))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Report why the AWS smoke checks did not start.")
    parser.add_argument("report", type=Path)
    parser.add_argument("reason", choices=[
        "aws_target_not_configured", "newer_revision", "deployment_failed", "preparation_failed",
    ])
    args = parser.parse_args(argv)
    status = "failed" if args.reason.endswith("_failed") else "not_run"
    SmokeReport().write(args.report, status, args.reason)


if __name__ == "__main__":
    main()
