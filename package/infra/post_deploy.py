"""Apply migrations and check the deployed HTTP API with read-only requests."""

import argparse
import json
import re
from pathlib import Path
from time import sleep

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.httpsession import URLLib3Session
from pydantic import ValidationError

from package.app.http import Problem
from package.app.schemas import RepairPage
from package.infra.smoke_report import Check, CheckFailed, SmokeReport


def apply_migrations(client, function_name: str, check: Check) -> None:
    for attempt in range(4):
        check.attempts += 1
        try:
            result = client.invoke(FunctionName=function_name, InvocationType="RequestResponse", Payload=b"{}")
            break
        except ClientError as error:
            check.actual_http = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            # 権限反映待ちの拒否は、Lambda の実行前に発生する。この場合だけ再試行する。
            if error.response["Error"]["Code"] != "AccessDeniedException" or attempt == 3:
                raise CheckFailed("lambda_invoke_failed") from None
            sleep(2 ** (attempt + 1))
    check.actual_http = result["StatusCode"]
    if check.actual_http != check.expected_http or result.get("FunctionError"):
        raise CheckFailed("migration_failed")
    try:
        payload = json.load(result["Payload"])
    except ValueError:
        raise CheckFailed("invalid_migration_response") from None
    if payload != {"migration": "up-to-date"}:
        raise CheckFailed("invalid_migration_response")


def get_page(api_url, region, limit, credentials, http, check: Check):
    # AWS の資格情報を送る先は、デプロイ先リージョンの API Gateway ホストに限る。
    if not re.fullmatch(rf"https://[a-z0-9]+\.execute-api\.{re.escape(region)}\.amazonaws\.com(?:\.cn)?", api_url):
        raise ValueError("Expected an HTTPS API Gateway endpoint in the deployment region.")
    for attempt in range(4):
        check.attempts += 1
        request = AWSRequest(method="GET", url=f"{api_url}/repair-requests?limit={limit}")
        if credentials is not None:
            SigV4Auth(credentials.get_frozen_credentials(), "execute-api", region).add_auth(request)
        response = http.send(request.prepare())
        check.actual_http = response.status_code
        if response.status_code == check.expected_http:
            return response
        if response.status_code not in {403, 429, 500, 502, 503, 504} or attempt == 3:
            raise CheckFailed("unexpected_http_status")
        # 確認に使う GET だけを再送する。待ち時間は順に2秒、4秒、8秒。
        sleep(2 ** (attempt + 1))


def check_api(api_url: str, region: str, credentials, http, check: Check) -> None:
    response = get_page(api_url, region, 1, credentials, http, check)
    if response.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        raise CheckFailed("invalid_media_type")
    try:
        page = RepairPage.model_validate_json(response.content)
    except ValidationError:
        raise CheckFailed("invalid_list_schema") from None
    if len(page.items) > 1:
        raise CheckFailed("page_size_exceeded")


def run_checks(outputs: Path, session, report: SmokeReport, smoke_only: bool) -> None:
    with outputs.open(encoding="utf-8") as file:
        stack = json.load(file)["RepairApi"]
    if not smoke_only:
        with report.checks["migration"].run() as check:
            config = Config(read_timeout=150, retries={"total_max_attempts": 1})
            apply_migrations(session.client("lambda", config=config), stack["MigrateFunction"], check)

    api_url, region = stack["ApiUrl"], session.region_name
    http = URLLib3Session(timeout=35)
    try:
        with report.checks["iam"].run() as check:
            get_page(api_url, region, 1, None, http, check)

        with report.checks["list"].run() as check:
            credentials = session.get_credentials()
            if credentials is None:
                raise CheckFailed("missing_aws_credentials")
            check_api(api_url, region, credentials, http, check)

        with report.checks["invalid_limit"].run() as check:
            response = get_page(api_url, region, 0, credentials, http, check)
            if response.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/problem+json":
                raise CheckFailed("invalid_media_type")
            try:
                problem = Problem.model_validate_json(response.content)
            except ValidationError:
                raise CheckFailed("invalid_problem_schema") from None
            if problem.status != check.expected_http:
                raise CheckFailed("invalid_problem_status")
    finally:
        http.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path, help="JSON file written by cdk deploy --outputs-file")
    parser.add_argument("--report", type=Path, default=Path("aws-smoke.json"))
    parser.add_argument("--smoke-only", action="store_true", help="Skip migration and run only the HTTP checks")
    args = parser.parse_args(argv)
    report = SmokeReport()
    try:
        run_checks(args.outputs, boto3.Session(), report, args.smoke_only)
    except Exception:
        # SDK の例外や応答本文にはリクエスト情報が含まれうる。公開するのは検査名と固定の失敗分類だけ。
        reason = next((case.id for case in report.checks.values() if case.status == "failed"), "setup_failed")
        report.write(args.report, "failed", reason)
        return 1
    report.write(args.report, "passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
