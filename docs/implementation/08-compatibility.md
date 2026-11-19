# 実装編 08　既存の呼び方を保って API を変更する

公開中の一覧を使う画面には、受付番号順にすべての場所の依頼が並びます。ここに「第2会議室だけ見たい」という要望が加わりました。新版でも、場所を送らない画面には同じ依頼を同じ順序で返す、というのが今回守る約束です。

## 既存のテストに、新しい呼び方を足す

現在のサンプルでは、状態・件数・続きの番号で一覧を取得できます。場所の指定は、[場所フィルターを加える手順](first-operation.md)で手元のコピーに実装します。変更後は次の三つを確かめます。

| 確かめること | リクエストと期待結果 | 使うテスト |
| --- | --- | --- |
| 旧画面のページ送り | `?status=open&limit=2` で先頭2件を読み、返された番号を `after` に渡すと続きが読める | [既存の API テスト](../../tests/test_api.py)の `test_filtered_pages_continue_after_deleted_cursor` |
| 新しい条件を省略した場合 | A・B・A の順に3件登録して `GET /repair-requests` を呼ぶと、同じ3件が同じ順序で返る | 手順で足す `test_location_filter` の最初の一覧取得 |
| 新しい条件を指定した場合 | `?location=A&limit=1` で最初の A が返り、次のページでは B を飛ばして最後の A が返る。該当がなければ空の一覧、空白だけの指定なら `422` | 同じテストの場所を指定した一覧取得 |

この変更を試すときは以前のテストも一緒に実行します。場所の条件を加える前から使われていた、状態の絞り込みやページ送りも確かめるためです。

## 公開する版に反映する

この追加を公開すると決めたら、[アプリの作成箇所](../../package/app/main.py)にある `RepairAPI(..., version="1.0.0")` の版を `1.1.0` に変えます。この教材で採用するセマンティックバージョニングでは、互換性を保つ機能追加にマイナー版を使います。[実装編07](07-openapi.md)のコマンドで YAML を再生成し、`info.version` と一覧の任意パラメータを確認します。[実例編07の YAML 抜粋](../examples/07-openapi.md)にも同じ版を書けば、[抜粋と仕様書を照合するテスト](../../tests/unit/test_book_openapi.py)で一致を確かめられます。公開パスは引き続き `/repair-requests` です。

AWS では、既存の HTTP API の `$default` ステージが同じ Lambda につながります。追加した絞り込みは FastAPI が処理し、既存の DB 列を使うので、この変更には Gateway のルート追加や DB の移行は要りません。反対に、`title` を廃止して `summary` を必須にする変更では旧画面の登録が壊れます。旧・新の二つの契約を提供するときの URL、ステージ、DB の移行順は[並行稼働の構成例](../build/version-rollout.md)で確認できます。

根拠　[セマンティックバージョニング](https://semver.org/lang/ja/)・[AWS　HTTP API のステージ](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-stages.html)

[前へ　実装 07](07-openapi.md) ｜ [教科書 08](../textbook/08-compatibility.md) ｜ [実例 08](../examples/08-compatibility.md) ｜ [シート C3](../templates/contract-sheet.md#c3) ｜ [実装編の目次](README.md)
