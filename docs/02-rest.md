# 第2章　REST とリソース

社員は修理を頼み、総務は完了を記録します。操作は別々でも、どちらも同じ修理依頼を見ています。そこで最初に「何を扱うか」を決めてみましょう。

## 依頼と、画面に届くデータを分ける

この API が扱う対象は **修理依頼** です。椅子そのものを管理する台帳なら、一脚ずつ識別するでしょう。今回は一脚に対して何度も修理を頼めるため、番号を付ける単位は依頼1件です。

REST では、こうして名前を付けて扱う対象を **リソース** と呼びます。番号が42の依頼には `/repair-requests/42` という宛先を割り当てます。修理が終わって状態が変わっても、同じ宛先でその依頼を参照できます。[Fielding 博士論文 第5章 §5.2.1.1 Resources and Resource Identifiers](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_2_1_1)

画面に届くのは、依頼のその時点の状態を表したデータです。これを **表現** といいます。以下は JSON という形式を使った、受付直後の表現です。項目名の右に値が並びます。`open` は未完了という意味です。[RFC 9110 §3.2 表現](https://www.rfc-editor.org/rfc/rfc9110.html#section-3.2)・[RFC 8259 §4 JSON のオブジェクト](https://www.rfc-editor.org/rfc/rfc8259.html#section-4)

```json
{
  "id": 42,
  "title": "椅子の脚がぐらつく",
  "location": "第1会議室",
  "status": "open"
}
```

修理後に同じ宛先を読むと、`id` は42のまま、`status` が `completed` に変わります。この約束があれば、総務がデータをどの表に保存したかを社員の画面が知る必要はありません。

## やり取りに共通のルールを持たせる

**REST（Representational State Transfer）** は、Web のようなシステムで、構成要素の役割とやり取りを定める設計様式です。提唱者 Roy Fielding は、その中心に「統一インターフェース」を置きました。HTTP を使うときは、対象を示す宛先、操作を表すメソッド、結果を表すステータスコードなどが共通の手掛かりになります。[Fielding 第5章 §5.1.5 Uniform Interface](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_5)・[RFC 9110 §1.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-1.3)

たとえば、`GET /repair-requests/42` は「42番の依頼を読みたい」という要求です。サーバーはこれだけで取得対象を特定できます。直前にどの依頼を画面で開いたかをサーバーが覚えている必要はありません。このように、各要求に処理に必要な情報を含める制約を **ステートレス** と呼びます。修理依頼の状態そのものは、サーバーのデータベースに保存できます。[Fielding 第5章 §5.1.3 Stateless](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_3)

REST のほかの制約も、二つの画面をつなぐ仕組みとして読めます。[Fielding 第5章 §5.1](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1)

| 制約 | 修理依頼の例で考えると |
| --- | --- |
| クライアントとサーバーの役割を分ける | 画面が入力と表示を担い、受付側が依頼を管理する |
| 応答を再利用できる条件を示す（キャッシュ） | 利用者が最新の状況を見る場面では、古い応答を使わせるかが設計の論点になる |
| 処理を階層に分ける | 画面は受付の宛先に要求を送り、その先で働くプログラムの配置は受付側が決める |
| 必要に応じてクライアントにコードを配る | たとえば、ブラウザーにスクリプトを配って機能を追加する。これは任意の制約 |

統一インターフェースには、受け取った表現の中のリンクなどを手掛かりに、次の操作を選べるようにする考え方もあります。これが **ハイパーメディア** です。今回のサンプルでは、登録した依頼の宛先を応答で伝えます。更新などの操作は、あらかじめ API の仕様書を読んで組み込みます。REST の原典が示す制約のうち、この教材では、リソースの識別と HTTP の共通の意味を設計に生かします。[Fielding 第5章 §5.1.5、§5.3.3](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_5)

[前へ　API とは何か](01-api.md) ・ [目次](../README.md) ・ [次へ　パスとパラメータ](03-addresses.md)
