# 修理依頼 API の実装とテスト

社員が件名と場所を送ると、API は依頼を保存して受付番号を返します。このアプリは依頼の登録、一覧、詳細、状態の更新、削除の5操作を提供します。初めて使うときは、下の手順で1件を登録し、別の要求で同じ依頼を開いてみてください。[全操作の OpenAPI 定義（YAML）](../../docs/openapi.yaml)・[第8章の実装解説](../../docs/08-fastapi.md)

## ローカルで API と PostgreSQL を起動する

Docker と Docker Compose v2 を用意し、以下のコマンドはすべて**リポジトリのルート**で実行します。Compose が PostgreSQL を起動し、テーブルを用意してから API を起動します。`--wait` はサービスが使える状態になるまで待つ指定です。[Compose の設定](../../compose.yaml)・[Docker「起動順を制御する」](https://docs.docker.com/compose/how-tos/startup-order/)

```console
docker compose up --build --wait api
```

ブラウザーで [Swagger UI](http://127.0.0.1:8000/docs) を開きます。入力欄は、起動中の API が公開する [OpenAPI 定義](http://127.0.0.1:8000/openapi.json) から作られます。このサンプルは FastAPI の標準設定を使うため、画面を開くにはブラウザーから Swagger UI の配信元（CDN）への接続も必要です。Python と SQLite で同じ API を試す手順は第8章にあります。[第8章の起動手順](../../docs/08-fastapi.md)・[FastAPI の画面用ファイルと配信元](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/)

### Swagger UI で登録から照会まで確かめる

1. **POST /repair-requests** を開き、**Try it out** を選びます。入力例の「会議室の椅子を修理する」を選び、次の本文で **Execute** を押します。

   ```json
   {"title":"椅子がぐらつく","location":"第2会議室"}
   ```

2. **Server response** を読みます。成功すると `201` が返り、本文に `id` と `"status":"open"` が現れます。応答ヘッダーの `location` は、その依頼を開くためのパスです。たとえば `/repair-requests/42` なら、今回の受付番号は `42` です。
3. **GET /repair-requests/{request_id}** を開き、**Try it out** で実際の受付番号を入力して **Execute** を押します。`200` と先ほどの件名・場所・状態が返れば、登録した依頼を読み出せました。
4. 入力エラーも試せます。登録の本文の `title` を空文字列にして送ると `422` が返ります。応答の `Content-Type` は `application/problem+json` で、`detail` が入力のどこを直すかを示します。[エラー応答の読み方](../../docs/05-responses.md)

## 操作を追加・変更するときの方針

最初に「何を送ると、何が保存され、次にどの宛先を開けるか」を決めます。たとえば登録の成功条件は、`201` が返ることと、返された `Location` で同じ依頼を読めることです。一つの操作の契約を、次の順でコードに反映します。[第6章の設計シート](../../docs/06-contract.md)

| 決めること | このアプリで変更する場所 |
| --- | --- |
| 利用者が入力する項目と、サーバーが返す項目 | [schemas.py](schemas.py) の入力モデルと応答モデル。登録では件名と場所だけを受け取り、番号と初期状態はサーバーで決める。件名などに上限を設けたら、その上限と前後の値をテストする |
| メソッド、宛先、成功後の応答 | [main.py](main.py) のルートに、メソッド・パス・応答モデル・ステータスを書く。登録では DB への保存を確定してから、採番された ID で `Location` を組み立てる |
| 失敗をどう伝えるか | [http.py](http.py) が共通のエラー形式を定める。JSON の構文エラーは `400`、対象なしは `404`、未対応の本文形式は `415`、項目の制約違反は `422`。各ルートの `responses` に、その操作で起こる応答を記載する |
| 保存する列や制約 | [database.py](database.py) の SQLAlchemy モデルと [DB マイグレーション](../db/migrations) を対応させる。状態の候補を増やすなら、API の入力条件と、DB が許す値の両方を見直す |

入力モデルの制約と `response_model` は OpenAPI に反映されます。一方、「失敗時に行が増えない」「最後のページの `next_after` は `null`」といった約束は、処理後のデータや実際の応答をテストで確かめます。[FastAPI「Response Model」](https://fastapi.tiangolo.com/tutorial/response-model/)・[SQLAlchemy「Session Basics」](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

## 変更後にどのテストを実行するか

Python のテストは uv と Python 3.12 を使います。初回は `uv sync --locked` を実行してください。コードを変更したら、まず Ruff で未使用の import などを、mypy で関数の引数や戻り値の型を点検します。型検査には CDK を扱うコードが含まれるため、`infra` の依存関係も使います。[プロジェクト設定](../../pyproject.toml)・[Ruff](https://docs.astral.sh/ruff/linter/)・[mypy](https://mypy.readthedocs.io/en/stable/running_mypy.html)・[uv の依存関係の同期](https://docs.astral.sh/uv/concepts/projects/sync/)

```console
uv run --locked ruff check package scripts tests
uv run --locked --group infra mypy
```

| 確かめたいこと | テストが観察するもの | 実行コマンド |
| --- | --- | --- |
| 入力や共通エラーを正しく扱えるか | モデルや関数を直接呼び、前後の空白、文字数の境界、余分な項目、エラー本文とヘッダーを確認する | `uv run --locked python -m pytest -q tests/unit` |
| FastAPI と保存処理が連動するか | テストごとに一時 SQLite を作り、マイグレーション後に TestClient から登録・照会・更新・削除を呼ぶ。失敗後の状態やページの続きも確かめる | `uv run --locked python -m pytest -q tests/test_api.py` |
| 起動した API と PostgreSQL を一緒に使えるか | Compose の別コンテナから実際に HTTP を送り、登録・照会・更新・削除と再送を試す。別の接続から SQL で読み、DB に反映された結果も照合する | `docker compose run --rm integration` |
| 実際の応答が OpenAPI の約束に合うか | 保存した YAML の入力例を API に送り、期待したステータス・応答項目と照合する。5操作の応答がスキーマに合うかも検証する | `uv run --locked --group contract python tests/contract/check.py` |

上の2行は API を起動せずに実行できます。下の2行は、最初の手順で起動したローカルの API を使います。テストが作成した依頼の番号をその場で取得するので、先に Swagger UI で登録した依頼と区別できます。[単体テスト](../../tests/unit)・[SQLite との結合テスト](../../tests/test_api.py)・[FastAPI「Testing」](https://fastapi.tiangolo.com/tutorial/testing/)

新しいケースを足すときも、変更の効果が見える場所を選びます。たとえば状態の更新なら、不正な値を拒んだ後も元の状態を読めることを HTTP で確かめ、正しい更新を保存した後は別の DB 接続からも新しい値が見えることを確かめます。テーブルの権限は、API 用の DB ユーザーで読み書きでき、テーブル定義の変更は拒まれることを別のテストで検査します。[PostgreSQL との結合テスト](../../tests/integration/test_repair_workflow.py)・[DB 権限のテスト](../../tests/test_postgres.py)

### 入力例を追加して契約を検証する

登録の例 `trim-spaces` を見ると、送る件名には「照明が消える」の前後に空白があり、応答に期待する件名は空白を除いた「照明が消える」です。例を増やすときは [schemas.py](schemas.py) の該当する例の集まりに加えます。[main.py](main.py) は正常例を `Body(openapi_examples=...)` に、入力を拒む例を操作の `x-negative-examples` に渡します。各例の `value` に送る値、`x-expected-status` に期待するステータスを書きます。特定の応答項目も確かめたい例には `x-expected-fields` を指定します。`x-` の項目はこの教材のテストで使う拡張です。[FastAPI の入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)・[OpenAPI の拡張項目](https://spec.openapis.org/oas/v3.1.1.html#specification-extensions)

仕様や例を変更したら、次の1行目で YAML と JSON を再生成し、差分を読みます。2行目は保存済みの両ファイルがコードからの生成結果と一致するかを確認します。[OpenAPI 出力コマンド](export_openapi.py)・[第7章の仕様書の読み方](../../docs/07-openapi.md)

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml docs/openapi.json
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml docs/openapi.json
```

起動中の API に対して表の契約テストを実行します。テストは YAML の登録・更新の正常例と異常例を一つずつ送り、実際のステータスと本文を期待値に照らします。さらに Schemathesis で応答のスキーマを検査し、更新後の依頼を読み直して保存結果も確かめます。完了時には `POST`・`PATCH` それぞれで通った例の数と、成功を確認した操作の数が表示されます。[契約テストの実装](../../tests/contract/check.py)・[Schemathesis 公式ドキュメント](https://schemathesis.readthedocs.io/en/stable/)

Compose の PostgreSQL はテスト用で、停止すると登録した修理依頼も消えます。確認を終えたら `docker compose down --volumes` でコンテナと、この環境で生成した資格情報を保存するボリュームを片づけます。[Docker Compose down](https://docs.docker.com/reference/cli/docker/compose/down/)

## GitHub で検証し、AWS に反映する

GitHub Actions の **Verify sample** は、プルリクエストと push で自動テストを実行します。API と DB の動作や OpenAPI を確認し、CDK で AWS 構成を生成して Lambda イメージをビルドします。失敗したら、Actions の実行結果で該当するステップを開き、同じテストを手元で実行できます。[検証ワークフロー](../../.github/workflows/verify.yml)

AWS への自動デプロイを使うときは、GitHub の環境 `aws` と AWS 側の権限を用意し、リポジトリ変数に `AWS_ROLE_ARN` と `AWS_REGION` を設定します。`main` への push が検証に通り、そのコミットが引き続き `main` の先頭であれば、**Deploy to AWS** がその版をデプロイします。[デプロイワークフロー](../../.github/workflows/deploy.yml)・[AWS へのデプロイ手順](../infra/README.md)

デプロイ後は **Deploy to AWS** の実行概要で「AWS 実環境の疎通確認」を開きます。署名なしの一覧取得は `403`、署名付きで `limit=1` なら `200`、同じ署名方式でも `limit=0` なら `422` が期待値です。どの段階で失敗したかは、各検査の結果と実際の HTTP ステータスで追えます。記録は実行結果の **Artifacts → aws-smoke-report** にある `aws-smoke.json` からも読めます。`not_run` は、たとえばデプロイ先のロールが未設定で、AWS での検証を実施していないことを表します。[AWS へのデプロイ手順](../infra/README.md)・[GitHub Actions の成果物](https://docs.github.com/en/actions/tutorials/store-and-share-data)
