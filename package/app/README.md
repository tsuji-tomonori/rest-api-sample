# 修理依頼 API の実装とテスト

社員が件名と場所を送ると、API は依頼を保存して受付番号を返します。このアプリは依頼の登録、一覧、詳細、状態の更新、削除の5操作を提供します。初めて使うときは、下の手順で1件を登録し、別の要求で同じ依頼を開いてみてください。[全操作の OpenAPI 定義](../../docs/openapi.json)・[第8章の実装解説](../../docs/08-fastapi.md)

## ローカルで API と PostgreSQL を起動する

Docker と Docker Compose v2 を用意し、以下のコマンドはすべて**リポジトリのルート**で実行します。Compose が PostgreSQL を起動し、テーブルを用意してから API を起動します。`--wait` はサービスが使える状態になるまで待つ指定です。[Compose の設定](../../compose.yaml)・[Docker「起動順を制御する」](https://docs.docker.com/compose/how-tos/startup-order/)

```console
docker compose up --build --wait api
```

ブラウザーで [Swagger UI](http://127.0.0.1:8000/docs) を開きます。入力欄は、起動中の API が公開する [OpenAPI 定義](http://127.0.0.1:8000/openapi.json) から作られます。このサンプルは FastAPI の標準設定を使うため、画面を開くにはブラウザーから Swagger UI の配信元（CDN）への接続も必要です。Python と SQLite で同じ API を試す手順は第8章にあります。[第8章の起動手順](../../docs/08-fastapi.md)・[FastAPI の画面用ファイルと配信元](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/)

### Swagger UI で登録から照会まで確かめる

1. **POST /repair-requests** を開き、**Try it out** を選びます。本文に次の JSON を入れ、**Execute** を押します。

   ```json
   {"title":"椅子の脚がぐらつく","location":"第1会議室"}
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

Python のテストは uv と Python 3.12 を使います。依存関係は `uv.lock` で固定しています。初回は `uv sync --locked` を実行してください。[プロジェクト設定](../../pyproject.toml)・[uv の依存関係の同期](https://docs.astral.sh/uv/concepts/projects/sync/)

| 確かめたいこと | テストが観察するもの | 実行コマンド |
| --- | --- | --- |
| 入力や共通エラーを正しく扱えるか | モデルや関数を直接呼び、前後の空白、文字数の境界、余分な項目、エラー本文とヘッダーを確認する | `uv run --locked python -m pytest -q tests/unit` |
| FastAPI と保存処理が連動するか | テストごとに一時 SQLite を作り、マイグレーション後に TestClient から登録・照会・更新・削除を呼ぶ。失敗後の状態やページの続きも確かめる | `uv run --locked python -m pytest -q tests/test_api.py` |
| 起動した API と PostgreSQL を一緒に使えるか | Compose の別コンテナから実際に HTTP を送り、登録・照会・更新・削除と再送を試す。別の接続から SQL で読み、DB に反映された結果も照合する | `docker compose run --rm integration` |
| 実際の応答が OpenAPI の約束に合うか | Swagger UI が参照する定義を取得し、保存版の仕様と照合する。5操作の HTTP 応答を Schemathesis で検証する | `uv run --locked --group contract python tests/contract/check.py` |

上の2行は API を起動せずに実行できます。下の2行は、最初の手順で起動したローカルの API を使います。テストが作成した依頼の番号をその場で取得するので、先に Swagger UI で登録した依頼と区別できます。[単体テスト](../../tests/unit)・[SQLite との結合テスト](../../tests/test_api.py)・[FastAPI「Testing」](https://fastapi.tiangolo.com/tutorial/testing/)

新しいケースを足すときも、変更の効果が見える場所を選びます。たとえば状態の更新なら、不正な値を拒んだ後も元の状態を読めることを HTTP で確かめ、正しい更新を保存した後は別の DB 接続からも新しい値が見えることを確かめます。テーブルの権限は、API 用の DB ユーザーで読み書きでき、テーブル定義の変更は拒まれることを別のテストで検査します。[PostgreSQL との結合テスト](../../tests/integration/test_repair_workflow.py)・[DB 権限のテスト](../../tests/test_postgres.py)

契約テストの例を一つ見ると、状態を更新する `PATCH` では、OpenAPI に列挙した値から入力を作り、応答をスキーマと照合します。その後に `GET` で読み直し、変更した状態が保存されたことも確かめます。操作を増やしたら、このテストにその操作の成功例を加えてください。公開した操作の一覧と、実際に成功を確認した操作を照合しているため、確認漏れを検出できます。[契約テストの実装](../../tests/contract/check.py)・[Schemathesis 公式ドキュメント](https://schemathesis.readthedocs.io/en/stable/)

Swagger UI の操作も自動で確かめられます。ローカル API の起動中に次の2行を実行すると、Playwright が Chromium で一覧取得の **Try it out → Execute** を操作し、画面上の `200` と JSON が実際の応答と一致するかを確認します。1行目のブラウザーのインストールは初回に行います。Swagger UI を表示するブラウザーは、FastAPI が既定で使う配信元から JavaScript と CSS を読み込みます。[ブラウザーテスト](../../tests/contract/swagger_ui.py)・[Playwright のブラウザーの準備](https://playwright.dev/python/docs/browsers)・[FastAPI の画面用ファイル](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/)

```console
uv run --locked --group contract python -m playwright install chromium
uv run --locked --group contract python tests/contract/swagger_ui.py
```

CI ではランナーに入っている Google Chrome を `--channel chrome` で選び、同じ操作を確かめます。[Playwright が対応するブラウザー](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge)・[GitHub ランナーの搭載ブラウザー](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md#browsers-and-drivers)

仕様を変更したら、次の1行目で配布用の JSON を再生成し、差分を読みます。2行目はファイルを書き換えず、コードから生成した内容と一致するかを検査します。実際に送受信した値やヘッダーは、上の契約テストで確かめます。[OpenAPI 出力コマンド](export_openapi.py)・[第7章の仕様書の読み方](../../docs/07-openapi.md)

```console
uv run --locked python -m package.app.export_openapi docs/openapi.json
uv run --locked python -m package.app.export_openapi --check docs/openapi.json
```

Compose の PostgreSQL はテスト用で、停止すると登録した修理依頼も消えます。確認を終えたら `docker compose down --volumes` でコンテナと、この環境で生成した資格情報を保存するボリュームを片づけます。[Docker Compose down](https://docs.docker.com/reference/cli/docker/compose/down/)

## GitHub で検証し、AWS に反映する

GitHub Actions の **Verify sample** は、プルリクエストと push で自動テストを実行します。API と DB の動作や OpenAPI を確認し、CDK で AWS 構成を生成して Lambda イメージをビルドします。失敗したら、Actions の実行結果で該当するステップを開き、同じテストを手元で実行できます。[検証ワークフロー](../../.github/workflows/verify.yml)

AWS への自動デプロイを使うときは、GitHub の環境 `aws` と AWS 側の権限を用意し、リポジトリ変数に `AWS_ROLE_ARN` と `AWS_REGION` を設定します。設定後は、`main` への push が検証に通り、そのコミットが引き続き `main` の先頭であれば、**Deploy to AWS** がその版をデプロイします。続いて DB マイグレーションを実行し、署名付きの要求で一覧を取得できることを確認します。初回設定と失敗時の確認手順はインフラの README にあります。[デプロイワークフロー](../../.github/workflows/deploy.yml)・[AWS へのデプロイ手順](../infra/README.md)
