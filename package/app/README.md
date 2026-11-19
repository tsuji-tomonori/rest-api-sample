# 修理依頼 API を起動してテストする

件名と場所を送って修理を依頼すると、API が受付番号と取得先を返します。番号を使って依頼を読み、修理が済んだら状態を `completed` に変更できます。5操作すべての入力とレスポンスは [OpenAPI 仕様書（YAML）](../../docs/openapi.yaml) で確認できます。

## PostgreSQL を使って1件登録する

**サンプルで試せる**　Docker と Docker Compose v2 を用意します。以下のコマンドはすべてリポジトリのルートで実行します。Compose は PostgreSQL を起動し、マイグレーションでテーブルを作ってから API を起動します。

```console
docker compose up --build --wait api
```

1. ブラウザーで [Swagger UI](http://127.0.0.1:8000/docs) を開きます。`POST /repair-requests` の **Try it out** を押し、入力例「会議室の椅子を修理する」を選びます。送る JSON 本文は `{"title":"椅子がぐらつく","location":"第2会議室"}` です。
2. **Execute** で送信します。**Server response** に `201`、本文に `id` と `"status":"open"` が表示されます。レスポンスヘッダー `location` が `/repair-requests/42` なら、新しい依頼の受付番号は `42` です。
3. `GET /repair-requests/{request_id}` の **Try it out** で実際の番号を入力し、**Execute** を押します。`200` と先ほどの内容が返れば、登録した依頼を読み出せました。

Swagger UI は、起動中の API の `/openapi.json` から操作や入力欄を読み込みます。リポジトリで配布する仕様書は `docs/openapi.yaml` です。画面の表示に必要なファイルは、FastAPI の既定の配信元（CDN）からブラウザーが取得します。Docker を使わずに始める場合は、SQLite を使う [FastAPI の起動手順](../../docs/09-fastapi.md) があります。

## 設計した操作を実装する

たとえば登録の仕様を変えるなら、設計シートで「保存後に利用者ができること」を決め、公開 YAML の `createRepair` で現在の入力とレスポンスを確認します。変更内容に合わせて、次のファイルを編集します。[設計シートの記入例](../../docs/06-contract.md)・[仕様書から登録処理を読む](../../docs/09-fastapi.md)

| 変更内容 | 対応する場所 |
| --- | --- |
| 利用者が送る項目、返す項目や入力例 | [schemas.py](schemas.py) の入力モデル、レスポンスモデル、正常例と異常例 |
| メソッド、パス、成功時のステータスやヘッダー | [main.py](main.py) のルート。登録では保存を確定してから `Location` を組み立てる |
| エラー時の本文とメディアタイプ | [http.py](http.py) の `Problem` と共通処理。ルートごとの `responses` には該当するステータスを書く |
| 保存する列と DB の制約 | [database.py](database.py) のテーブル定義と [DB マイグレーション](../db/migrations) |

## 仕様書を更新し、変更を確かめる

ホストに uv と Python 3.12 を用意します。リポジトリのルートで依存関係をそろえ、実装から YAML を生成してください。差分を読み、意図した変更が設計シートと一致するかを確認します。

```console
uv sync --locked
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
git diff -- docs/openapi.yaml
```

手元では、変更のたびに次のコマンドで単体テストと SQLite を使う結合テストを実行できます。API サーバーの起動は不要です。

```console
uv run --locked python -m pytest -q tests/unit tests/test_api.py
```

レビュー前にコードと型を調べるには、次の2行を実行します。mypy は CDK のコードも読むため、`infra` グループを指定します。

```console
uv run --locked ruff check package scripts tests
uv run --locked --group infra mypy
```

HTTP と PostgreSQL まで通して確認するときは、冒頭の Compose コマンドをもう一度実行し、変更後の API を起動します。次の1行目は業務フローを、2行目は公開 YAML に載せた例と実際のレスポンスを確かめます。検証項目の選び方と各テストの範囲は第11章にまとめています。[第11章　API のテストを組み立てる](../../docs/11-testing.md)

```console
docker compose run --rm integration
uv run --locked --group contract python tests/contract/check.py
```

検証用 PostgreSQL のデータは DB コンテナを停止すると消えます。作業を終えてローカル用の資格情報も片づけるときは、`docker compose down --volumes` を実行します。[Compose の設定](../../compose.yaml)

## 構築・運用へ引き継ぐ

GitHub の **Verify sample** は、push とプルリクエストでテストを繰り返し、公開 YAML が現在のコードから生成できることも調べます。コードと仕様書の変更を一緒にレビューすると、利用者への影響を確認できます。[検証ワークフロー](../../.github/workflows/verify.yml)・[第13章　API のバージョンを上げる](../../docs/13-versioning.md)

AWS の構成と配置手順は第10章、デプロイ後の疎通結果や障害時の確認は第12章で扱います。[第10章　AWS での構築](../../docs/10-aws.md)・[インフラの README](../infra/README.md)・[第12章　API の運用と監視を始める](../../docs/12-operations.md)

## 実装時の参照先

- 仕様を読み、入力例を追加する。[OpenAPI の書き方](../../docs/07-openapi.md)・[仕様書の生成コード](export_openapi.py)・[FastAPI の名前付き入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)
- 入力と保存結果をテストする。[単体テスト](../../tests/unit)・[FastAPI と SQLite](../../tests/test_api.py)・[HTTP と PostgreSQL](../../tests/integration/test_repair_workflow.py)・[公開 YAML の契約テスト](../../tests/contract/check.py)
- Swagger UI の画面を表示するためのファイルを確認する。[FastAPI の画面用ファイル](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/)
