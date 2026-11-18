# 第7章　FastAPI で修理依頼を受け付ける

第6章で決めた約束を、手元のパソコンで確かめましょう。社員の代わりに修理依頼を送り、総務の代わりに状態を変えます。使うのは、API の操作をブラウザーから試せる画面です。

## データベースを用意して起動する

必要なのは Python 3.12、Git、ブラウザー、初回にパッケージを取得するためのインターネット接続です。保存先には Python から使える SQLite を選びました。以下のコマンドはリポジトリのルートで実行します。すでにコードを取得した方は、仮想環境を作る手順から進めてください。

```console
git clone https://github.com/tsuji-tomonori/rest-api-sample.git
cd rest-api-sample
```

Python の仮想環境を作ります。ここでは仮想環境の Python を直接指定するので、端末ごとの有効化操作を省けます。

**Windows（PowerShell）**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m package.db.migrate
.\.venv\Scripts\python.exe -m uvicorn package.app.main:app --reload
```

**macOS・Linux**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m package.db.migrate
.venv/bin/python -m uvicorn package.app.main:app --reload
```

3行目の **マイグレーション** は、データを入れるテーブルを用意する処理です。Alembic が適用済みの変更を記録します。同じコマンドをもう一度実行しても、登録した依頼は残ります。初回は現在のフォルダーにデータベースファイルができます。[最初のテーブル定義](../package/db/migrations/versions/0001_repair_requests.py)・[Alembic のチュートリアル](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

4行目のサーバーを起動したまま、ブラウザーで [操作画面](http://127.0.0.1:8000/docs) を開きます。この画面は Swagger UI といい、FastAPI が生成した仕様書を使って、実際の要求を送れます。同じ仕様をデータとして読みたいときは [OpenAPI の定義](http://127.0.0.1:8000/openapi.json) を開きます。[FastAPI の公式チュートリアル](https://fastapi.tiangolo.com/tutorial/first-steps/)

## 1件登録して、受付番号で追いかける

1. 「POST /repair-requests」を開き、**Try it out** を押します。
2. 本文を次の JSON に置き換え、**Execute** を押します。件名の両端には、わざと空白を入れています。

```json
{"title":"  椅子の脚がぐらつく  ","location":"第1会議室"}
```

**Server response** に出た結果を見ます。**Code** が `201`、**Response body** の `status` が `open` なら受付完了です。件名の両端の空白が消えていることも確かめましょう。本文の `id` を控えてください。以下では、手元で返った番号を使います。

| 次にしたいこと | 操作画面で入力するもの | Server response で確かめること |
| --- | --- | --- |
| 依頼を1件開く | GET の個別取得を選び、`request_id` に控えた番号を入れる | `200`。登録した件名と場所が返る |
| 未完了の一覧に出るか見る | GET の一覧で `status` に `open` を指定する | `items` に今の依頼が含まれる。空の台帳から始めた場合は1件 |
| 総務が完了を記録する | PATCH で同じ番号を指定し、本文に `{"status":"completed"}` を送る | `200`。同じ番号のまま状態が変わる |
| 絞り込みの結果を見る | 先ほどの未完了一覧をもう一度実行する | 完了にした番号が一覧から外れる |
| 練習用の依頼を削除する | DELETE に今の番号を入れる | `204` で本文が空。同じ番号を GET すると `404` になる |

最後に、POST の件名を空白だけにして送ってみましょう。今度は `422` と `application/problem+json` の本文が返ります。未完了の一覧を開いても、この入力から新しい依頼は増えていません。操作画面下部の **Responses** は仕様上の例も表示するので、実際の結果は **Server response** で確かめます。

## どのコードが受付番号を返したのか

登録を1件だけコードで追ってみましょう。入口は [main.py](../package/app/main.py) の `create_repair` です。

```python
repair = RepairRequest(**data.model_dump(), status="open")
db.add(repair)
db.commit()
response.headers["Location"] = f"/repair-requests/{repair.id}"
return repair
```

ここに届く時点で、件名と場所は [schemas.py](../package/app/schemas.py) の `NewRepair` が検証しています。最初の行は、その二つの値に初期状態 `open` を加え、保存する依頼を作ります。`db.add` で保存の対象に加え、`db.commit` が成功すると登録が確定します。そこで、データベースが採番した番号から `Location` を組み立てます。[FastAPI のリクエスト本文](https://fastapi.tiangolo.com/tutorial/body/)・[SQLAlchemy のセッション](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

章の前半で見た `201` は、同じ関数の上にある `@app.post(..., status_code=201, ...)` で決まります。応答に含める項目も、そこで `response_model=Repair` と指定しています。登録時に利用者が渡す項目と、登録後に見える項目が違う理由をコードでたどれます。

一覧の処理は同じファイルの `list_repairs` です。要求より1件多く読んで、続きがあれば返した最後の番号を `next_after` に入れます。たとえば3件ある台帳で `limit=2` とすると、1ページ目には2件と続きの番号が返ります。同じ条件に `after` を加えて続きを読むと、残りの1件と `null` が返ります。

## 手元で契約をもう一度確かめる

サーバーを <kbd>Ctrl</kbd> + <kbd>C</kbd> で止め、同じフォルダーでテストを実行します。Windows では次のコマンドを使います。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

macOS・Linux では `.venv/bin/python -m pytest -q` です。[テスト](../tests/test_api.py)は練習用の台帳と別のデータベースを用意して、受付番号、状態の変化、エラー時の応答を確認します。次の章では、同じ FastAPI を AWS で動かし、保存先を Aurora PostgreSQL に切り替えます。

[前へ　業務の言葉を API の契約にする](06-contract.md) ・ [目次](../README.md) ・ [次へ　AWS に配置する](08-aws.md)
