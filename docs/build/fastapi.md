# 仕様書の約束を FastAPI で実装する

開発に取りかかるときは、設計シートと公開する仕様書を並べます。修理依頼の設計シートにあるのは「登録した社員が、後から同じ依頼を開ける」という約束です。仕様書で登録操作の `createRepair` を探すと、その約束を確かめる手がかりが見つかります。件名と場所を送ると `201` が返り、レスポンスヘッダーの `Location` に取得先が入ります。ここまでを、登録機能の完成条件にしましょう。[修理依頼の操作をまとめた実例](../examples/06-contract.md)・[修理依頼の仕様書への転記](../examples/07-openapi.md)・[公開仕様書（YAML）](../openapi.yaml)

このページでは登録を1件通して実装を読みます。メソッドごとの書き分けを調べるときは[実装編 04](../implementation/04-methods.md)、リクエストが AWS と手元の環境でどこを通るかは[実装編 01](../implementation/01-http.md)を参照してください。

## 登録の条件を関数に書く

登録を担当するのは `create_repair` 関数です。関数の手前にある `@app.post(...)` は、「このパスに `POST` が届いたら、この関数を呼ぶ」という指定です。Python ではこうした書き方をデコレーターと呼びます。

| 仕様書に書いた約束 | Python で対応する部分 |
| --- | --- |
| `POST /repair-requests` で登録する | `@app.post("/repair-requests", ...)`。`operation_id="createRepair"` が仕様書の操作名になる |
| リクエスト本文に件名と場所を送る | 引数 `data` の型を `NewRepair` とする。`Body(openapi_examples=...)` に、利用者が Swagger UI で選べる入力例を渡す |
| 成功時は受付番号と状態を含む JSON を返す | `status_code=201` と `response_model=Repair` で成功時のステータスと本文の型を指定する |
| 登録した依頼を `Location` で開ける | `responses` にヘッダーの意味と形式を書き、保存後の番号から実際の値を組み立てる |

`NewRepair` に受付番号はありません。番号を決めるのはサーバーだからです。返す側の `Repair` には、利用者が送った件名と場所に加えて、番号と状態も入ります。入力用と出力用の型を分けると、それぞれが何を受け持つかをコードから読み取れます。

## 保存してから、取得先を返す

登録関数の本体を抜き出すと、次の5行です。

```python
repair = RepairRequest(**data.model_dump(), status="open")
db.add(repair)
db.commit()
response.headers["Location"] = f"/repair-requests/{repair.id}"
return repair
```

FastAPI が検証した件名と場所に、初期状態 `open` を加えます。`db.add` で保存する依頼を登録し、`db.commit` で変更を確定します。受付番号が `42` なら、次の行で `Location` に `/repair-requests/42` を設定します。最後に返した依頼から、FastAPI が `Repair` に定めた項目を取り出して JSON のレスポンスを作ります。

## パス、クエリ、本文の値を受け取る

同じように関数の引数に見えても、値の届く場所は操作ごとに異なります。

| 利用者が送る値 | FastAPI が値を受け取るしくみ |
| --- | --- |
| `GET /repair-requests/42` の `42` | パスの `{request_id}` と同じ名前の引数 `request_id: RepairId` で、指定範囲の整数として受け取る |
| `GET /repair-requests?limit=10` の `10` | 引数 `limit` の `Query(ge=1, le=100, ...)` で、件数を1〜100に制限する。引数の既定値は20 |
| `POST /repair-requests` の件名と場所 | `data: Annotated[NewRepair, Body(...)]` で、JSON 本文を `NewRepair` の条件に沿って検証する |

こうして入力の条件を宣言すると、FastAPI が値を読み、条件を満たしたリクエストを関数へ渡します。たとえば本文に含めた件名が空白だけなら、このサンプルは `422` を返し、登録処理には進みません。

## 変更したら、仕様書と動作を確かめる

このサンプルは、ルートとモデルの宣言から公開用の YAML を生成します。たとえば登録のレスポンスを変えたら、YAML を生成し直します。差分を読むと、登録のどの項目が変わったかを設計シートと照合できます。uv と Python 3.12 を用意し、リポジトリのルートで実行してください。

```console
uv sync --locked
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
git diff -- docs/openapi.yaml
uv run --locked python -m pytest -q tests/unit tests/test_api.py
```

たとえば件名の入力条件を直したら、単体テストで空白や文字数の境界を確かめます。結合テストでは、実際に FastAPI が入力を拒んだとき、テスト用 SQLite に依頼が増えないことまで調べます。どちらも API サーバーを起動せず、変更のたびに手元で実行できます。GitHub に変更を送ると、CI（継続的インテグレーション）が同じ検証を繰り返し、PostgreSQL を使う業務フローも確かめます。[API のテスト](testing.md)・[CI の実行内容](../../.github/workflows/verify.yml)

## 1件登録し、仕様書に書いた宛先を開く

今度は利用者と同じ手順で確かめます。リポジトリのルートで次の2行を実行すると、SQLite の台帳（`repairs.db`）にテーブルを作り、API を起動します。

```console
uv run --locked python -m package.db.migrate
uv run --locked uvicorn package.app.main:app
```

ブラウザーで `http://127.0.0.1:8000/docs` を開きます。Swagger UI が起動中の API から `/openapi.json` を読み込み、操作一覧を表示します。`POST /repair-requests` の **Try it out** で「会議室の椅子を修理する」を選び、次の JSON 本文を **Execute** で送ります。

```json
{"title":"椅子がぐらつく","location":"第2会議室"}
```

**Server response** に `201` が表示されたら、本文の `id` とレスポンスヘッダーの `location` を読みます。番号が `42` なら取得先は `/repair-requests/42` です。詳細取得の `request_id` 欄に実際の番号を入れて送ると、`200` と同じ依頼が返ります。これで「登録した社員が、後から同じ依頼を開ける」という完成条件を確認できました。手元のサーバーは、起動した端末で Ctrl+C を押すと停止します。

## AWS の構築へ引き継ぐ

構築担当者に渡すのは、テストが通ったコードと、そのコードから生成した仕様書です。修理依頼を保存するには、実行環境の DB にテーブルも必要です。AWS では同じアプリを Lambda で動かし、マイグレーションで Aurora にテーブルを用意します。手元で確かめた登録と照会は、AWS に配置した後も同じメソッドとパスで呼び出せます。[Lambda の入口](../../package/app/main.py)・[DB のマイグレーション](../../package/db/migrate.py)・[AWS での構築](aws.md)

## 根拠と参考

- FastAPI の本文、パスとクエリの扱い、レスポンスの組み立て方。[Request Body](https://fastapi.tiangolo.com/tutorial/body/)・[Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)・[Response Headers](https://fastapi.tiangolo.com/advanced/response-headers/)
- DB への保存と確定、実行環境の準備。[SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)・[uv の環境同期](https://docs.astral.sh/uv/concepts/projects/sync/)
- このサンプルのコードと検証手順。[ルートと保存処理](../../package/app/main.py)・[入出力の型](../../package/app/schemas.py)・[登録後に取得するテスト](../../tests/test_api.py)・[PostgreSQL での起動とテスト](../../package/app/README.md)

[修理依頼の設計](../examples/06-contract.md) ｜ [API のテスト](testing.md) ｜ [教材の目次](../../README.md)
