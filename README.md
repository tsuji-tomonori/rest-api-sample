# はじめて設計する REST API

社員が椅子の故障を知らせると、受付番号が返ります。総務が修理を終えると、社員はその番号で進み具合を確認できます。この教材では、両者が同じ台帳を使うための修理依頼 API を題材にします。

## 読み終えるとできること

1. **自分の業務から操作を一つ選び、API を設計する。** 誰が何をしたいかを書き、何を送ると何が返るかを設計シートで決めます。その結果を、プログラムでも読める OpenAPI 仕様書（YAML）に書けます。
2. **設計した操作をコードに書き、返ってくる結果を確かめる。** 修理依頼の詳細を取得する API を Python で作ります。完成版では、複数の端末から届く依頼をどこで受け、どう保存し、どうテストするかも追えます。

## 読み始める場所を選ぶ

- **初めての人**は[教科書の第1章](docs/textbook/01-http.md)から。HTTP のやり取りを一枚の図で見てから、同じ番号の実例を読みます。設計にはプログラミング経験も AWS 環境も要りません。
- **API を使ったことがある人**は[修理依頼の実例](docs/examples/01-http.md)から。なぜそのパスやメソッドを選んだかをたどり、迷ったところだけ教科書に戻れます。
- **いま設計したい人**は[設計シート](docs/templates/contract-sheet.md)をコピーしてください。利用者の行動を書き出し、一つの操作を選び、公開前の点検まで進められます。入力の置き場所・メソッド・ステータスの早見表もシートにあります。
- **コードを書いてみたい人**は[実装編の入口](docs/implementation/README.md)へ。[クラウドの意味と修理依頼アプリの構成図](docs/implementation/architecture.md)を読んでから、手元で詳細取得を作り、[一覧に検索条件を加える](docs/implementation/first-operation.md)ところまで進めます。

## 教科書・実例・実装の目次

同じ番号を横にたどると、選び方、修理依頼での判断、その判断を実現するコードを順に読めます。自分の業務に当てはめるときは、右端の設計シートに記入します。

| 主題 | 教科書編 | 実例編 | 実装編 | 設計シート |
| --- | --- | --- | --- | --- |
| 01　API と HTTP | [通信の全体像](docs/textbook/01-http.md) | [いつ受付番号が要るか](docs/examples/01-http.md) | [手元と AWS の入口](docs/implementation/01-http.md) | [A1　利用者の行動](docs/templates/contract-sheet.md#a1) |
| 02　リソース | [何を1件と数えるか](docs/textbook/02-resources.md) | [何に番号を付けるか](docs/examples/02-resources.md) | [受付番号で DB の1行を読む](docs/implementation/02-resources.md) | [A2　対象と宛先](docs/templates/contract-sheet.md#a2) |
| 03　入力 | [値の置き場所](docs/textbook/03-inputs.md) | [受付番号と検索条件](docs/examples/03-inputs.md) | [引数と本文の型を書く](docs/implementation/03-inputs.md) | [B3・B4　場所と条件](docs/templates/contract-sheet.md#b3) |
| 04　メソッド | [操作と再送](docs/textbook/04-methods.md) | [登録・照会・完了・削除](docs/examples/04-methods.md) | [メソッドを関数に結ぶ](docs/implementation/04-methods.md) | [B2・B8　操作と再送](docs/templates/contract-sheet.md#b2) |
| 05　レスポンス | [ステータスと本文](docs/textbook/05-responses.md) | [空の一覧と存在しない番号](docs/examples/05-responses.md) | [201 と Location を返す](docs/implementation/05-responses.md) | [B6・B7　成功と失敗](docs/templates/contract-sheet.md#b6) |
| 06　操作の契約 | [権限・途中失敗・完成条件](docs/textbook/06-contract.md) | [登録の記入済みシート](docs/examples/06-contract.md) | [保存結果を確かめる](docs/implementation/06-contract.md) | [B5・B9　権限と確認例](docs/templates/contract-sheet.md#b5) |
| 07　OpenAPI | [仕様書を書く順序](docs/textbook/07-openapi.md) | [登録の約束を YAML に写す](docs/examples/07-openapi.md) | [YAML を生成して検査する](docs/implementation/07-openapi.md) | [C2　操作定義と入出力例](docs/templates/contract-sheet.md#c2) |
| 08　互換性 | [公開中の API を変える](docs/textbook/08-compatibility.md) | [件名を改名したら](docs/examples/08-compatibility.md) | [以前の呼び方をテストする](docs/implementation/08-compatibility.md) | [C3　影響と移行条件](docs/templates/contract-sheet.md#c3) |

修理依頼では、登録・一覧・詳細・状態変更・削除の基本を扱います。[会議室予約の記入例](docs/examples/room-booking.md)では、同じシートに「同時に同じ部屋を予約したらどうするか」「誰が予約を取り消せるか」を書きます。こちらは業務条件によって設計が変わる例です。用語は[用語集](docs/glossary.md)で引けます。

## サンプルを構築・テスト・運用する

設計した一件の修理依頼を、開発から運用まで追えます。[FastAPI と uv で実装する](docs/build/fastapi.md) → [AWS に構築する](docs/build/aws.md) → [API をテストする](docs/build/testing.md) → [運用・監視する](docs/build/operations.md)。版を分けて配信する場合は[旧版と新版の並行稼働](docs/build/version-rollout.md)に進みます。

実装済みの5操作と、その入力・応答は[公開 OpenAPI 仕様書](docs/openapi.yaml)にあります。手元で起動する手順は[アプリの README](package/app/README.md)、AWS へ配置する手順は[インフラの README](package/infra/README.md)にあります。

教材やコードを変更する人は、[リポジトリの保守ガイド](docs/maintenance/README.md)を参照してください。
