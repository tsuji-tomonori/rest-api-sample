# 実装編 06　変更を確定し、別のリクエストで確かめる

実例編の設計シートには、登録が終わったら別のリクエストで同じ依頼を開けると書きました。状態変更にも同じ考え方を使えます。総務が完了にした依頼を社員があとで開いても、状態は完了のままです。この約束を実装するには、対象の1行を更新し、DB が変更を確定してから結果を返します。

## 入力、更新、確定の順に書く

更新関数の引数は `data: StatusChange` に入力例の指定を添えたものです。`StatusChange` が受け取る値は `status` 一つで、型は `Literal["open", "completed"]` です。FastAPI はこの条件を検証してから関数を呼びます。このため `{"status":"done"}` を送ると、保存処理に進む前に `422` が返ります。[入力モデル](../../package/app/schemas.py)

条件を満たす入力が届いたら、更新関数で次の処理を行います。[状態を変更する `update_status`](../../package/app/main.py)

```python
statement = update(RepairRequest).where(RepairRequest.id == request_id).values(status=data.status)
# RETURNING は同じ更新命令で変更後の行を返す。対象があれば変更を確定してから応答する。
repair = db.scalar(statement.returning(RepairRequest))
if repair is None:
    raise HTTPException(404, NOT_FOUND)
db.commit()
return repair
```

`where` は受付番号で対象を絞り、`values` は状態だけを書き換えます。`returning` を使うと、同じ更新命令で変更後の行を受け取れます。該当する行があれば `db.commit()` で更新を確定します。引数 `db: DB` に渡すセッションは、FastAPI の `Depends(session)` がリクエストごとに用意します。[セッションの定義](../../package/app/database.py)

同じ番号に再び `{"status":"completed"}` を送っても、状態は完了のままです。一方、登録の `POST` は毎回新しい行を追加します。保存に成功した直後に通信が切れた場合、DB の変更は残るため、画面から登録を自動でやり直すと依頼が重複することがあります。

## 権限を確かめる場所を決める

| 確かめたいこと | このサンプルの実装 |
| --- | --- |
| 誰が AWS 上の API を呼べるか | API Gateway の `HttpIamAuthorizer()` が署名と呼び出し権限を確認する。[CDK の入口設定](../../package/infra/app.py) |
| API が DB に何をしてよいか | API 用 DB ユーザー `repair_api` に、修理依頼テーブルの読取・登録・更新・削除を許可する。テーブル構造の変更は移行用ユーザーが担当する。[DB 権限の設定](../../package/db/app_role.py) |

このサンプルは共有台帳です。利用を許可された人は同じ依頼を変更できます。本人だけが変更できる仕様にするなら、登録時に認証済みの依頼者を保存し、更新時にもその人の行かを調べる処理を追加します。手元の SQLite テストでは、AWS の IAM 認可を通さずにアプリを呼びます。

## 拒否した更新が残っていないことを確かめる

リポジトリのルートで次を実行します。

```console
uv run --locked python -m pytest -q tests/test_api.py::test_body_format_and_failed_update
```

テストは未完了の依頼を1件作り、許可していない状態などを送って `422` を確認します。次に、別の `GET` で同じ番号を読み、元の `open` が残っていることを調べます。存在しない番号に正しい状態を送ったときの期待結果は `404` です。CI ではさらに別の接続から PostgreSQL の保存値を確認しています。[SQLite の API テスト](../../tests/test_api.py)・[HTTP と PostgreSQL を通すテスト](../../tests/integration/test_repair_workflow.py)

**公式資料**　[SQLAlchemy のセッションとコミット](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)・[AWS の HTTP API の IAM 認可](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html)

[前へ　実装 05](05-responses.md) ｜ [教科書 06](../textbook/06-contract.md) ｜ [実例 06](../examples/06-contract.md) ｜ [シート B9](../templates/contract-sheet.md#b9) ｜ [次へ　実装 07](07-openapi.md) ｜ [実装編の目次](README.md)
