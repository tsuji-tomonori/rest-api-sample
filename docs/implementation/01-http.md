# 実装編 01　リクエストを受ける入口を作る

修理依頼の一覧を開くと、画面は「台帳にある依頼を見せてほしい」とリクエストを送ります。これが `GET /repair-requests` です。複数の人が同じ台帳を見られるように、どこでこのリクエストを受け、どこから依頼を読み出すのでしょうか。

サンプルの公開先は **Amazon Web Services（AWS）** です。アプリを動かすコンピューターやデータの保存先を、必要に応じてネットワーク越しに使う仕組みをクラウドと呼びます。AWS はこうしたサービスを提供しており、このサンプルでは次の順に使います。

1. **Amazon API Gateway が受け付ける。** 画面が呼ぶ URL の入口です。このサンプルでは「HTTP API」という種類の入口を作り、呼び出す権限を確かめてからリクエストを渡します。
2. **AWS Lambda がアプリを動かす。** Lambda は、呼び出しを受けてコードを実行するサービスです。その中で動く Python アプリが、メソッドとパスを見て一覧取得の関数を選びます。この振り分けを書くために使うのが FastAPI です。
3. **Amazon Aurora から台帳を読む。** Aurora はデータを表に保存するデータベースです。一覧取得の関数が保存済みの依頼を読み出します。結果が API Gateway を通って画面に返ると、一覧を表示できます。

公開後にリクエストが通る経路は、[修理依頼 API の構成図](architecture.md)でたどれます。

## 手元で動かすと何が変わるか

手元でも同じ FastAPI アプリを使います。入口を Uvicorn というプログラムで起動し、台帳にはデータを一つのファイルに保存できる SQLite を使います。

| 設計した役割 | 手元で動かすとき | AWS に配置したとき |
| --- | --- | --- |
| HTTP リクエストを受ける | Uvicorn が端末のポート 8000 で受信する | API Gateway が公開 URL で受信する |
| メソッドとパスから処理を選ぶ | Uvicorn が渡したリクエストを FastAPI が振り分ける | Lambda の中で同じ FastAPI が振り分ける |
| 依頼を保存して読み直す | SQLite の `repairs.db` を使う | Aurora の PostgreSQL 互換データベースを使う |

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

`main.py` の末尾で、Lambda から呼び出す関数 `handler` を用意します。Mangum は API Gateway から届いたデータを FastAPI の `app` に渡し、その結果を API Gateway に返せる形式に変換します。

```python
handler = Mangum(app, lifespan="off")
```

AWS の構成を Python で定義するツールが AWS CDK です。次の設定で、API Gateway の入口と、そこから呼ぶ Lambda を結びます。`api_handler` は、上の `package.app.main.handler` を実行する Lambda です。

```python
gateway = apigw.HttpApi(
    self, "Gateway",
    default_authorizer=authorizers.HttpIamAuthorizer(),
    default_integration=integrations.HttpLambdaIntegration("FastAPI", api_handler),
)
```

`default_authorizer` は、AWS の権限管理の仕組み（IAM）で署名と呼び出し権限を確かめる設定です。`default_integration` は既定の送り先を決めます。FastAPI に業務用のパスを追加すると、そのパスのリクエストも同じ Lambda に届きます。DB への通信経路と権限は [AWS の構築ガイド](../build/aws.md)で確認できます。

[FastAPI の入口](../../package/app/main.py)・[CDK の接続設定](../../package/infra/app.py)・[AWS 公式の HTTP API と Lambda の統合](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html)

[教科書 01](../textbook/01-http.md) ｜ [実例 01](../examples/01-http.md) ｜ [シート A1](../templates/contract-sheet.md#a1) ｜ [次へ　実装 02](02-resources.md) ｜ [実装編の目次](README.md)
