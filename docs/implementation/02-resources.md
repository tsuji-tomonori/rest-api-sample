# 実装編 02　受付番号と台帳の1行を結ぶ

同じ椅子について二度修理を頼めば、受付は2件です。この設計をコードに写すには、台帳の1行を「修理依頼1件」とし、行ごとに受付番号を付けます。利用者が後から同じ依頼を開けるように、その番号を個別のパスに使います。

## モデルで行を表し、マイグレーションでテーブルを作る

Python で行を扱うための型が、SQLAlchemy の `RepairRequest` です。`__tablename__` でテーブル名 `repair_requests` を指定しています。次はクラスの中で列を宣言している部分です。

```python
id: Mapped[int] = mapped_column(primary_key=True)
title: Mapped[str] = mapped_column(String(100))
location: Mapped[str] = mapped_column(String(100))
status: Mapped[str] = mapped_column(String(16), server_default="open")
```

`id` は1行を特定する主キーです。`title` と `location` は利用者が送る値で、受付番号は保存時に DB が決めます。作成した行の状態は `open` です。[モデルの全体](../../package/app/database.py)

実際の DB にテーブルを用意するのは Alembic のマイグレーションです。初版の `upgrade()` にある `op.create_table` が、同じ名前のテーブルと4つの列を作ります。実装編01の `python -m package.db.migrate` は、DB に記録された版を読んで未適用の変更を反映します。将来、保存する項目を増やしたら、モデルの列宣言と、既存の台帳に列を加える新しいマイグレーションを一組で用意します。[テーブルを作る初版](../../package/db/migrations/versions/0001_repair_requests.py)・[マイグレーションの実行処理](../../package/db/migrate.py)

## 個別のパスから同じ行を読む

FastAPI は `GET /repair-requests/{request_id}` に届いた番号を、次の関数の `request_id` に渡します。`db` は DB の操作に使うセッションです。`db.get` の2番目の引数に主キーを渡すと、指定した依頼を1件取り出せます。

```python
def get_repair(request_id: RepairId, db: DB):
    repair = db.get(RepairRequest, request_id)
    if repair is None:
        raise HTTPException(404, NOT_FOUND)
    return repair
```

たとえば `GET /repair-requests/42` は、42番の行があればその内容を、存在しなければ `404` を返します。[ルートの定義](../../package/app/main.py)

## 受付番号と DB の主キーを照合する

1. 実装編01で起動した API の [Swagger UI](http://127.0.0.1:8000/docs) を開きます。`POST /repair-requests` の **Try it out** で本文に `{"title":"読書灯が点かない","location":"資料室"}` を入れ、**Execute** を押します。
2. レスポンスの `Location` を読みます。`/repair-requests/42` と返ったなら受付番号は42です。詳細取得の `request_id` にその番号を入れて実行し、件名・場所・状態を読みます。
3. 別の端末で、API を起動したのと同じディレクトリから次の1行を実行します。`42` は実際に返った番号に替えてください。

```console
uv run --locked python -m sqlite3 repairs.db "SELECT id, title, location, status FROM repair_requests WHERE id = 42"
```

同じ番号の行に「読書灯が点かない」「資料室」「open」が並べば、その受付番号で開いた依頼と、SQLite に保存した1行が対応しています。

[SQLAlchemy のテーブル宣言](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)・[Alembic のマイグレーション](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

[前へ　実装 01](01-http.md) ｜ [教科書 02](../textbook/02-resources.md) ｜ [実例 02](../examples/02-resources.md) ｜ [シート A2](../templates/contract-sheet.md#a2) ｜ [次へ　実装 03](03-inputs.md) ｜ [実装編の目次](README.md)
