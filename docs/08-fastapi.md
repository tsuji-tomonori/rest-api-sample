# 第8章　設計した契約を FastAPI で実現する

ここまでに決めた入力と応答を、Python のコードに移しましょう。修理依頼の登録を例にすると、契約は「件名と場所を受け取り、依頼を保存し、その依頼を開く宛先を返す」です。FastAPI では、要求を受け付ける条件を関数の定義に書き、条件を満たした後の処理を関数の中に書けます。[登録処理のコード](../package/app/main.py)・[FastAPI「Request Body」](https://fastapi.tiangolo.com/tutorial/body/)

## 設計のどの部分が、コードのどこにあるか

`create_repair` 関数の直前にある `@app.post(...)` は、関数と HTTP の操作を結び付ける指定です。Python ではこの書き方をデコレーターと呼びます。登録の契約をたどると、次のように対応します。

| 設計で決めたこと | コードでの表し方 |
| --- | --- |
| 登録先は `POST /repair-requests` | `@app.post` の最初の引数に `"/repair-requests"` を指定する |
| 本文には件名と場所を受け取る | 関数の引数を `data: NewRepair` とする。`NewRepair` が二つの項目と検証条件を定める |
| 登録が済んだら番号と状態を含む JSON を返す | デコレーターに `status_code=201` と `response_model=Repair` を書く。`Repair` が返す項目と型を定める |
| 新しい依頼を開けるようにする | デコレーターの `responses` に `Location` を記載し、関数の中で採番後の宛先をヘッダーに設定する |

型名の `NewRepair` と `Repair` はこのアプリで定義しています。受付番号と初期状態はサーバーが決めるので、返すデータには両方を含めます。入力用と出力用の型を分けると、どの値を利用者が用意するのかもコードから読み取れます。[入出力の型](../package/app/schemas.py)・[FastAPI「Response Model」](https://fastapi.tiangolo.com/tutorial/response-model/)・[「Response Status Code」](https://fastapi.tiangolo.com/tutorial/response-status-code/)

関数の中身は次の5行です。

```python
repair = RepairRequest(**data.model_dump(), status="open")
db.add(repair)
db.commit()
response.headers["Location"] = f"/repair-requests/{repair.id}"
return repair
```

検証済みの件名と場所に初期状態 `open` を加え、依頼を1件作ります。`db.add` で保存対象に加え、`db.commit` で登録を確定します。採番された `repair.id` があるので、ここで初めて `Location` の値を組み立てられます。最後に返した依頼から、FastAPI が `Repair` の項目を使って応答を作ります。[SQLAlchemy「Session Basics」](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)・[FastAPI「Response Headers」](https://fastapi.tiangolo.com/advanced/response-headers/)

## パス、クエリ、本文を読み分ける

同じ Python 関数の引数でも、値が来る場所は異なります。たとえば、パスに `{request_id}` があり、関数にも同じ名前の `request_id: RepairId` があれば、それがパスに埋め込んだ受付番号です。一覧取得の `limit: Annotated[int, Query(ge=1, le=100)] = 20` はクエリから整数を受け取り、範囲は1〜100、省略時は20と伝えます。登録の `data: NewRepair` は、Pydantic という入力検証ライブラリのモデルなので、JSON 本文を読み取ります。パスの名前と型の指定を追えば、一つの要求をコードのどこで受け取るかが分かります。[FastAPI「Request body + path + query parameters」](https://fastapi.tiangolo.com/tutorial/body/#request-body-path-query-parameters)

## 仕様書に載ることと、動作で確かめること

FastAPI は上の宣言から OpenAPI の定義を生成します。仕様書を読めば、登録の成功応答は `201` で、`Location` が返る設計だと分かります。その宛先で本当に登録済みの依頼を読めるかは、実際の要求で確かめます。サンプルのテストは一時的なデータベースに依頼を登録し、返された宛先に `GET` を送り、最初の応答と同じ依頼が返ることを確認しています。[登録から照会までのテスト](../tests/test_api.py)・[FastAPI「Testing」](https://fastapi.tiangolo.com/tutorial/testing/)

手元で1件試すには、uv を用意し、リポジトリのルートで次の3行を実行します。順に、固定したバージョンのライブラリをそろえ、SQLite にテーブルを作り、API を起動します。[uv「Locking and syncing」](https://docs.astral.sh/uv/concepts/projects/sync/)

```console
uv sync --locked
uv run --locked python -m package.db.migrate
uv run --locked uvicorn package.app.main:app
```

ブラウザーの操作画面で `POST /repair-requests` を開き、**Try it out** を選びます。下の本文を入れて **Execute** を押すと、実際の応答が **Server response** に表示されます。[手元の操作画面を開く](http://127.0.0.1:8000/docs)

```json
{"title":"椅子の脚がぐらつく","location":"第1会議室"}
```

`201` と `status: open` が返り、ヘッダーの `Location` の末尾が本文の `id` と一致すれば、依頼の登録に成功しています。

[前へ　OpenAPI で契約を表す](07-openapi.md) ・ [目次](../README.md) ・ [次へ　AWS に配置する](09-aws.md)
