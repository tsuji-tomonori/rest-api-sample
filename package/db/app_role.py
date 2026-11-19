"""移行用の接続を使い、Aurora に API 専用の利用者と権限を用意する。"""

import json

import boto3
from psycopg import sql
from sqlalchemy.engine import Connection


def grant_api_access(connection: Connection, secret_arn: str) -> None:
    response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    if secret["username"] != "repair_api":
        raise ValueError("The runtime secret must belong to repair_api")

    dbapi_connection = connection.connection.driver_connection
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'repair_api'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE ROLE repair_api LOGIN")
        # 平文のパスワードを SQL に含めず、接続ライブラリが計算した認証用の値を登録する。
        verifier = dbapi_connection.pgconn.encrypt_password(
            secret["password"].encode("utf-8"), b"repair_api", b"scram-sha-256"
        )
        cursor.execute(
            sql.SQL("ALTER ROLE repair_api PASSWORD {}").format(sql.Literal(verifier.decode("ascii")))
        )
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO repair_api").format(
                sql.Identifier(connection.engine.url.database)
            )
        )
        # API は依頼の読み書きと受付番号の採番を担い、テーブル構造の変更は移行用の利用者が担う。
        cursor.execute("GRANT USAGE ON SCHEMA public TO repair_api")
        cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.repair_requests TO repair_api")
        cursor.execute("GRANT USAGE ON SEQUENCE public.repair_requests_id_seq TO repair_api")
