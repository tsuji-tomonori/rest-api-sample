# 実装編 01　リクエストを受ける入口を作る

修理依頼の一覧を開くと、画面は `GET /repair-requests` を送ります。どの環境でも、このリクエストを受け取って一覧を返すのは同じ FastAPI アプリです。環境ごとに用意するのは、HTTP の入口と台帳の接続先です。

| 設計した役割 | 手元で動かすとき | AWS に配置したとき |
| --- | --- | --- |
| HTTP リクエストを受ける | Uvicorn が端末のポート 8000 で受信する | API Gateway の HTTP API が受信し、IAM で署名と呼び出し権限を確かめる |
| メソッドとパスから処理を選ぶ | Uvicorn がリクエストを渡し、FastAPI がメソッドとパスに対応する関数を選ぶ | Lambda が `handler` を実行する。Mangum がイベントを渡し、手元と同じ FastAPI が関数を選ぶ。戻り値は Mangum が Gateway 用のレスポンスに変換する |
| 依頼を保存して読み直す | SQLite の `repairs.db` を使う | 同じ Python の保存処理が Aurora PostgreSQL に接続する |

## 手元で一覧を開く

Python 3.12 と uv を用意し、取得したリポジトリのルートで次を実行します。DB の接続先に AWS や外部 DB の環境変数を設定していない状態では、2行目が手元の SQLite にテーブルを作ります。

```console
uv sync --locked
uv run --locked python -m package.db.migrate
uv run --locked uvicorn package.app.main:app
```

`package.app.main:app` は「`package/app/main.py` にある `app` を起動する」という指定です。起動した端末をそのままにして、別の端末で次の1行を実行します。Windows PowerShell では `curl.exe` と書きます。

```console
curl -i "http://127.0.0.1:8000/repair-requests?limit=1"
```

新しい台帳なら `200 OK` と `{"items":[],"next_after":null}` が返ります。これで HTTP の受付から DB の読み取りまで通ったと分かります。後の章でもこのサーバーを使えます。終了するときは起動した端末で Ctrl+C を押します。

## AWS では同じアプリをどう呼ぶか

`main.py` の末尾で、同じ `app` を使って Lambda の入口を一つ作ります。

```python
handler = Mangum(app, lifespan="off")
```

CDK の次の箇所で、API Gateway から API 用 Lambda に処理を渡します。`api_handler` は、上の `package.app.main.handler` を起動するよう設定した Lambda です。

```python
gateway = apigw.HttpApi(
    self, "Gateway",
    default_authorizer=authorizers.HttpIamAuthorizer(),
    default_integration=integrations.HttpLambdaIntegration("FastAPI", api_handler),
)
```

この構成では、FastAPI に業務用のパスを追加すると、Gateway の既定ルートから同じ Lambda に届きます。AWS の公開 URL に送るときは署名が必要です。DB への通信経路と権限は [AWS の構築ガイド](../build/aws.md)で確認できます。

[FastAPI の入口](../../package/app/main.py)・[CDK の接続設定](../../package/infra/app.py)・[AWS 公式の HTTP API と Lambda の統合](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html)

[教科書 01](../textbook/01-http.md) ｜ [実例 01](../examples/01-http.md) ｜ [シート A1](../templates/contract-sheet.md#a1) ｜ [次へ　実装 02](02-resources.md) ｜ [実装編の目次](README.md)
