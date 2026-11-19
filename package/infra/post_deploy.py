"""Apply migrations, then read one page from the deployed API using SigV4."""

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

from package.app.schemas import RepairPage


def apply_migrations(client, function_name: str) -> None:
    for attempt in range(4):
        try:
            result = client.invoke(FunctionName=function_name, InvocationType="RequestResponse", Payload=b"{}")
            break
        except ClientError as error:
            # 付与した権限が反映されるまでの拒否だけを再試行する。実行後の例外はそのまま報告する。
            if error.response["Error"]["Code"] != "AccessDeniedException" or attempt == 3:
                raise
            sleep(2 ** (attempt + 1))
    # 同期呼び出しは、関数が例外で終了しても Lambda サービス自体のステータスが 200 になる。
    if result["StatusCode"] != 200 or result.get("FunctionError"):
        raise RuntimeError(f"Migration failed. Check the CloudWatch logs for {function_name}.")
    if json.load(result["Payload"]) != {"migration": "up-to-date"}:
        raise RuntimeError("Migration did not confirm that the database is up to date.")


def check_api(api_url: str, region: str, credentials, http) -> None:
    # 署名には一時認証情報が含まれる。送信先を CDK の API Gateway URL に限定する。
    if not re.fullmatch(rf"https://[a-z0-9]+\.execute-api\.{re.escape(region)}\.amazonaws\.com(?:\.cn)?", api_url):
        raise ValueError("Expected an HTTPS API Gateway endpoint in the deployment region.")
    for attempt in range(4):
        request = AWSRequest(method="GET", url=f"{api_url}/repair-requests?limit=1")
        SigV4Auth(credentials.get_frozen_credentials(), "execute-api", region).add_auth(request)
        response = http.send(request.prepare())
        if response.status_code == 200:
            break
        if response.status_code not in {403, 429, 500, 502, 503, 504} or attempt == 3:
            raise RuntimeError(f"The signed list request returned HTTP {response.status_code}.")
        # 新しい IAM 権限の反映や一時的なタイムアウトを待つ。再送するのは一覧の GET だけ。
        sleep(2 ** (attempt + 1))
    try:
        page = RepairPage.model_validate_json(response.content)
    except ValidationError:
        # 応答に含まれる実データを CI のログへ出さない。
        raise RuntimeError("The response did not match the repair-list schema.") from None
    if len(page.items) > 1:
        raise RuntimeError("The response exceeded the requested page size.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path, help="JSON file written by cdk deploy --outputs-file")
    args = parser.parse_args()
    with args.outputs.open(encoding="utf-8") as file:
        outputs = json.load(file)["RepairApi"]
    session = boto3.Session()
    config = Config(read_timeout=150, retries={"total_max_attempts": 1})
    apply_migrations(session.client("lambda", config=config), outputs["MigrateFunction"])
    print("Database migrations are up to date.")
    http = URLLib3Session(timeout=35)
    try:
        check_api(outputs["ApiUrl"], session.region_name, session.get_credentials(), http)
    finally:
        http.close()
    print("The signed GET returned HTTP 200 and a valid repair-list page.")


if __name__ == "__main__":
    main()
