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

## 操作を変更する

たとえば登録の仕様を変えるなら、「何を送れるか」「保存後に何が返るか」「依頼を再び開けるか」を設計シートに書きます。仕様を変えた箇所に合わせて、次のファイルを編集します。

| 変更内容 | 対応する場所 |
| --- | --- |
| 利用者が送る項目、返す項目や入力例 | [schemas.py](schemas.py) の入力モデル、レスポンスモデル、正常例と異常例 |
| メソッド、パス、成功時のステータスやヘッダー | [main.py](main.py) のルート。登録では保存を確定してから `Location` を組み立てる |
| エラー時の本文とメディアタイプ | [http.py](http.py) の `Problem` と共通処理。ルートごとの `responses` には該当するステータスを書く |
| 保存する列と DB の制約 | [database.py](database.py) のテーブル定義と [DB マイグレーション](../db/migrations) |

仕様書に載せる受理例は `Body(openapi_examples=...)`、拒否する例は `x-negative-examples` に登録します。どちらにも `value` に送る本文、`x-expected-status` に期待するステータスを書きます。`x-expected-fields` を指定すると、テストがレスポンスの項目の値も照合します。

コードや例を変えたら、1行目で YAML を更新し、差分を読みます。2行目で、保存した仕様書と FastAPI が生成する内容が一致するか確認できます。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

## 変更をテストする

ホストで Python のコマンドを使うときは uv と Python 3.12 を用意し、初回に `uv sync --locked` を実行します。コードの静的検査には次の2行を使います。Ruff は未使用の名前などを、mypy は関数に渡す値の型などを調べます。mypy は CDK のコードも調べるので `infra` グループを指定します。

```console
uv run --locked ruff check package scripts tests
uv run --locked --group infra mypy
```

| 確かめたいこと | テストが調べるもの | 実行コマンド |
| --- | --- | --- |
| 入力条件やエラーの共通処理 | モデルや関数を直接呼び、空白、文字数の境界、余分な項目、エラー本文とヘッダーを確認する | `uv run --locked python -m pytest -q tests/unit` |
| ルートと保存処理の連携 | テスト用 SQLite に登録し、FastAPI の TestClient で取得・更新・削除する。失敗後の状態や一覧の続きも読む | `uv run --locked python -m pytest -q tests/test_api.py` |
| HTTP と PostgreSQL を通した業務の流れ | Compose の別コンテナから実際に HTTP リクエストを送り、DB を別の接続から読んで保存結果を照合する | `docker compose run --rm integration` |
| 実際のレスポンスと公開仕様書の一致 | YAML の登録例4件、状態変更例4件を送り、期待値と照合する。5操作の成功レスポンスとエラーの形式も確認する | `uv run --locked --group contract python tests/contract/check.py` |

表の最初の2件は API を起動せずに実行できます。後ろの2件は、最初の手順で起動した API と PostgreSQL を使います。たとえば状態変更のテストでは、受付番号を指定して `PATCH` を送り、その番号を別の `GET` で読み直します。実行後の状態を確認すると、レスポンスを返したあとも変更が保存されているか分かります。

検証用 PostgreSQL のデータは一時領域にあり、DB コンテナを停止すると消えます。後片付けの `docker compose down --volumes` は、コンテナとローカル用の資格情報を置いたボリュームも削除します。

## GitHub で検証結果を読む

**Verify sample** は push とプルリクエストでテストを実行し、仕様書との一致、CDK の構成、Lambda イメージを検査します。AWS のデプロイ先を設定すると、`main` の検証に通ったコミットが引き続き最新版であることを確認して、**Deploy to AWS** がデプロイします。設定手順は [インフラの README](../infra/README.md) にあります。

デプロイ後の疎通結果は、Actions の実行概要「AWS 実環境の疎通確認」で確認できます。署名なしの一覧取得は `403`、署名付きで `limit=1` なら `200`、`limit=0` なら `422` が期待値です。詳細は **Artifacts → aws-smoke-report** の `aws-smoke.json` に記録されます。`not_run` の場合は、同じレポートにデプロイ先が未設定などの理由が載ります。

## 出典と関連ファイル

- 仕様を決めてから実装までをたどる。[設計シート](../../docs/06-contract.md)・[OpenAPI 仕様書の書き方](../../docs/07-openapi.md)・[入出力の型と保存処理](../../docs/09-fastapi.md)
- 起動と仕様書の生成。[Compose の設定](../../compose.yaml)・[出力コマンド](export_openapi.py)・[FastAPI の画面用ファイル](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/)・[FastAPI の名前付き入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)
- テストの実装。[単体テスト](../../tests/unit)・[SQLite と FastAPI](../../tests/test_api.py)・[PostgreSQL との連携](../../tests/integration/test_repair_workflow.py)・[契約テスト](../../tests/contract/check.py)・[DB 権限の検査](../../tests/test_postgres.py)
- 自動検証とデプロイの条件。[検証ワークフロー](../../.github/workflows/verify.yml)・[デプロイワークフロー](../../.github/workflows/deploy.yml)
