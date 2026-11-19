# はじめて設計する REST API

## 読み終えるとできること

1. **自分の業務から操作を一つ選び、API を設計する。** 誰が何をしたいかを書き、何を送ると何が返るかを設計シートで決めます。その結果を、プログラムでも読める OpenAPI 仕様書（YAML）に書けます。
2. **自分が書いた設計を、どう確かめるか説明する。** 動く修理受付のサンプルで、設計した入力・応答が Python のコード、テストの期待値、公開後の監視にどうつながるかを追えます。

## 読み始める場所を選ぶ

- **初めての人**は[教科書の第1章](docs/textbook/01-http.md)から。HTTP のやり取りを一枚の図で見てから、同じ番号の実例を読みます。設計にはプログラミング経験も AWS 環境も要りません。
- **API を使ったことがある人**は[修理依頼の実例](docs/examples/01-http.md)から。なぜそのパスやメソッドを選んだかをたどり、迷ったところだけ教科書に戻れます。
- **いま設計したい人**は[設計シート](docs/templates/contract-sheet.md)をコピーしてください。利用者の行動を書き出し、一つの操作を選び、公開前の点検まで進められます。入力の置き場所・メソッド・ステータスの早見表もシートにあります。

## 設計の目次

教科書で選び方を知り、実例で判断を読み、シートに自分の答えを書きます。表は横に読んでも、一つの列を通して読んでも使えます。

| 主題 | 教科書で知る | 修理依頼で判断を見る | シートに書くこと |
| --- | --- | --- | --- |
| 01　API と HTTP | [通信の全体像](docs/textbook/01-http.md) | [受付番号が必要なタイミング](docs/examples/01-http.md) | [A1　誰が、何を、いつ必要とするか](docs/templates/contract-sheet.md#a1) |
| 02　REST とリソース | [何を1件と数えるか](docs/textbook/02-resources.md) | [椅子と修理依頼のどちらに番号を付けるか](docs/examples/02-resources.md) | [A2　対象、識別子、集合と個別の宛先](docs/templates/contract-sheet.md#a2) |
| 03　入力 | [パス・クエリ・ヘッダー・本文の選択](docs/textbook/03-inputs.md) | [受付番号と検索条件の置き場所](docs/examples/03-inputs.md) | [B3・B4　項目ごとの場所・型・必須条件](docs/templates/contract-sheet.md#b3) |
| 04　メソッド | [操作と再送の意味](docs/textbook/04-methods.md) | [登録・照会・完了・削除](docs/examples/04-methods.md) | [B2・B8　メソッド、同じ操作を再送した結果](docs/templates/contract-sheet.md#b2) |
| 05　レスポンス | [ステータスと本文の選び方](docs/textbook/05-responses.md) | [空の一覧と存在しない番号](docs/examples/05-responses.md) | [B6・B7　成功・失敗の伝え方、利用者の次の行動](docs/templates/contract-sheet.md#b6) |
| 06　操作の契約 | [権限・途中失敗・完成条件](docs/textbook/06-contract.md) | [登録操作の記入済みシート](docs/examples/06-contract.md) | [B5・B9　対象を扱える人、保存結果、確認例](docs/templates/contract-sheet.md#b5) |
| 07　OpenAPI | [仕様書を書く順序](docs/textbook/07-openapi.md) | [登録の約束を YAML に写す](docs/examples/07-openapi.md) | [C2　操作定義と入力・応答の例](docs/templates/contract-sheet.md#c2) |
| 08　互換性 | [公開中の API を変える判断](docs/textbook/08-compatibility.md) | [件名を改名すると何が変わるか](docs/examples/08-compatibility.md) | [C3　旧利用者への影響と移行条件](docs/templates/contract-sheet.md#c3) |

修理依頼では、登録・一覧・詳細・状態変更・削除の基本を扱います。[会議室予約の記入例](docs/examples/room-booking.md)では、同じシートに「同時に同じ部屋を予約したらどうするか」「誰が予約を取り消せるか」を書きます。こちらは業務条件によって設計が変わる例です。用語は[用語集](docs/glossary.md)で引けます。

## 設計を動くサンプルで確かめる

設計した一件の修理依頼を、開発から運用まで追えます。[FastAPI と uv で実装する](docs/build/fastapi.md) → [AWS に構築する](docs/build/aws.md) → [API をテストする](docs/build/testing.md) → [運用・監視する](docs/build/operations.md)。版を分けて配信する場合は[旧版と新版の並行稼働](docs/build/version-rollout.md)に進みます。

実装済みの5操作と、その入力・応答は[公開 OpenAPI 仕様書](docs/openapi.yaml)にあります。手元で起動する手順は[アプリの README](package/app/README.md)、AWS へ配置する手順は[インフラの README](package/infra/README.md)にあります。

教材やコードを変更する人は、[リポジトリの保守ガイド](docs/maintenance/README.md)を参照してください。
