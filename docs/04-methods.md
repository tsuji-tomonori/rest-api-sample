# 第4章　操作に合うメソッドを選ぶ

「注文を表示する」と「注文を登録する」では、利用者が期待する結果が違います。前者なら同じ画面を何度開いても注文数は変わりません。後者なら新しい注文が1件増えます。**HTTP メソッド**は、対象にどのような操作を求めるかを伝えます。まず、成功したときに何が変わるかを一文で書いてみましょう。[RFC 9110 §9.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.1)

## 注文 API で五つのメソッドを選ぶ

下の表は注文 API の設計例です。個別の注文は番号で開けます。注文ごとに一つ持つ配送指示には、受取場所と備考を登録できます。

| どんなとき | メソッドとパス | 送る値 | 主な成功応答 |
| --- | --- | --- | --- |
| 注文を1件開く | `GET /orders/42` | パスに注文番号 `42`。本文は使わない | `200 OK` と注文内容 |
| 新しい注文を登録し、番号を振ってもらう | `POST /orders` | 本文に `{"product_id":"P7","quantity":2}` | `201 Created`。新しい宛先を `Location` で知らせる |
| 配送指示の完成形を保存する | `PUT /orders/42/delivery-instructions` | パスに注文番号。本文に全項目 `{"place":"受付","note":"平日のみ"}` | 初めて作れば `201`。置き換えたら、結果を返す場合は `200`、本文を省く場合は `204` |
| 配送指示の備考だけを変える | `PATCH /orders/42/delivery-instructions` | パスに注文番号。本文に `{"note":"午前中"}` | この例では `200` と変更後の配送指示。受取場所は「受付」のまま |
| 誤登録した下書きの注文を削除する | `DELETE /orders/42` | パスに削除する注文番号。本文は使わない | 削除を終え、本文を返さなければ `204 No Content` |

選ぶ手掛かりの一つは、**新しく作るものの宛先を誰が決めるか**です。注文番号はサーバーが決めるので、登録先は集合の `/orders` です。一方、注文42の配送指示の宛先は最初から分かっています。そこに完成形を置くなら、初回も更新時も `PUT` を使えます。[RFC 9110 §9.3.3 POST](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.3)・[§9.3.4 PUT](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.4)

`PATCH` の本文は変更の指示です。「指定した項目をこの値にし、他の項目は保つ」というのは上の API が定めた約束です。JSON を採用するだけでは、省略された項目の扱いも、変更できる項目も決まりません。使う形式と操作の意味を契約に書きます。一度の `PATCH` が複数の変更を含む場合は、全部をまとめて適用し、一部だけ成功した状態を残しません。[RFC 5789 §2](https://www.rfc-editor.org/rfc/rfc5789.html#section-2)

### 「完了」と「項目を空にする」をどう伝えるか

修理依頼サンプルの「完了」ボタンは、`PATCH /repair-requests/42` に `Content-Type: application/json` を付けて `{"status":"completed"}` を送ります。42番があれば、件名と場所を保ったまま状態が変わり、`200` と更新後の依頼が返ります。ここで `status` は必須で、選べる値は `open` と `completed` です。本文が `{}`、`{"status":null}`、または `null` なら、サンプルは `422` を返します。[更新時の入力定義](../package/app/schemas.py)・[更新処理](../package/app/main.py)・[入力エラーの応答](../package/app/http.py)

次に、修理依頼に「担当者を外す」ボタンを加えるとします。この設計例では担当者を `assignee_id` で表し、状態と担当者をそれぞれ変更できるようにします。担当者欄に触れずに保存したときと、意図して担当者を外したときは、異なる JSON を送ります。

| 利用者がしたいこと | 送る JSON の例 | この設計での結果 |
| --- | --- | --- |
| 担当者を保ったまま完了にする | `{"status":"completed"}` | `assignee_id` は省略。状態だけを更新する |
| 担当者を外す | `{"assignee_id":null}` | 割り当てを解除し、状態は保つ |
| 担当者の欄から空文字が届く | `{"assignee_id":""}` | 空文字は有効な社員番号ではないので `422` を返す |

JSON の `null` は値の一つです。項目の省略や空の文字列とは区別します。`application/json` で「担当者の `null` は割り当て解除」とするのは、この業務で選んだ約束です。[JSON Schema「null」](https://json-schema.org/understanding-json-schema/reference/null)

### 削除、アーカイブ、注文の取り消しを分ける

「削除したい」と言われたら、まず**その後に同じ番号を開くと、何が見えるべきか**を確かめます。誤登録した下書きを台帳から取り除く例では、`DELETE /orders/42` に成功したら通常の一覧から42番が消え、個別に `GET /orders/42` しても `404` が返る、と決められます。HTTP の `DELETE` が求めるのは、その宛先と現在の機能との結び付きを取り除くことです。[RFC 9110 §9.3.5 DELETE](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.5)

この約束は、データベースの行を消す**物理削除**でも、削除日時を残して通常の照会から除く**論理削除**でも実現できます。`204` は依頼した削除の完了を知らせます。監査履歴やバックアップまで消したことを保証する応答ではありません。復元を求める業務なら、削除した記録をいつまで保ち、誰がどう復元できるかも決めます。[RFC 9110 §9.3.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.5)・[Google AIP-164「Soft delete」](https://google.aip.dev/164)

目的が「普段の一覧を片づけたい。過去の注文としては同じ番号で開きたい」なら、アーカイブという状態を設けられます。たとえば `PATCH /orders/42` に `{"archived":true}` を送り、通常の一覧に戻すときは `false` にします。また、成立した注文を**取り消す**場合は、注文自体を残して処理の経過を追いたいことがあります。第3章の `POST /orders/42/cancellation-requests` は、そのために取消申請を登録する例です。[第3章　パスとパラメータ](03-addresses.md)

### 注文を読むときと、ログインするときの違い

`GET /orders/42` は、すでにある注文を読みたいという要求です。これに対してパスワードでのログインは、本人確認を行い、その後も同じ利用者として操作できる状態（セッション）を始める手続きです。たとえば、注文サービスは次のように設計できます。

| 利用者の操作 | 要求と入力 | 成功したあと |
| --- | --- | --- |
| ログイン画面を開く | `GET /login`。入力フォームのページを取得する | 画面にログイン ID とパスワードの入力欄が表示される |
| 入力して「ログイン」を押す | `POST /sessions`。HTTPS で、本文に `{"login_id":"user42","password":"<入力値>"}` を送る | この例ではサーバーが本人を確認し、以後の要求で使うトークンを返す |
| 自分の登録情報を開く | `GET /me`。要求ヘッダーに `Authorization: Bearer <トークン>` を添える | サーバーがトークンを確認し、その利用者の登録情報を返す |

ページを開く段階ではフォームを読むだけです。「ログイン」を押すと本人確認とセッションの開始を依頼するので、ここで `POST` を選びます。パスワードを URL に入れると、履歴やアクセスログに残るおそれがあります。`GET` の本文には共通の意味がないため、パスワードを渡す場所にも使いません。ログイン後に `GET /me` を使えるのは、自分の情報を読みたいからです。このときは発行済みのトークンが「誰の情報か」を判断する材料になります。[RFC 9110 §9.3.1 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1)・[§17.9 URI と機密情報](https://www.rfc-editor.org/rfc/rfc9110.html#section-17.9)・[RFC 6750 §2.1 Bearer](https://www.rfc-editor.org/rfc/rfc6750.html#section-2.1)

ブラウザーでセッション Cookie を使う設計もあります。その方式では、ログイン応答の `Set-Cookie` でセッションを識別する値を渡し、ブラウザーが以後の要求の `Cookie` ヘッダーにその値を添えます。上の表は Bearer 方式を選んだ例です。後半で実装する修理依頼 API の AWS 構成では、API Gateway が IAM の署名を確認します。[RFC 6265 §3.1 Cookie の例](https://www.rfc-editor.org/rfc/rfc6265.html#section-3.1)・[第9章　AWS に配置する](09-aws.md)

### 検索する場合と、計算を依頼する場合

同じ注文サービスでも、未発送の注文を探すなら `GET /orders?status=unshipped` で一覧を読めます。サーバーがその場で集計する場合も、注文42の合計額を読む目的なら `GET /orders/42/summary` が使えます。一方、送り先と荷物の一覧を渡して送料を試算したいなら、`POST /shipping-estimates` の本文に条件を送り、`200` と計算結果を返す設計ができます。試算結果を保存する必要はありません。[RFC 9110 §9.3.1 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1)・[§9.3.3 POST](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.3)

## リクエストとレスポンスを1往復読む

表の `POST /orders` を、通信で見るとどうなるでしょうか。下は HTTP/1.1 の読み方を示す抜粋です。最初の行に続いてヘッダーが並び、空行の後に本文が来ます。例の `Content-Length` は本文のバイト数です。[RFC 9112 §2.1 メッセージの形式](https://www.rfc-editor.org/rfc/rfc9112.html#section-2.1)

**クライアントからの要求（リクエスト）**。最初の行では `POST` が操作、`/orders` が宛先です。`Host` は送信先のホスト名を伝えます。本文で「商品 P7 を2個」と指定しています。

```http
POST /orders HTTP/1.1
Host: example.com
Content-Type: application/json
Accept: application/json
Content-Length: 32

{"product_id":"P7","quantity":2}
```

**サーバーからの応答（レスポンス）**。最初の行の `201` は登録成功を示します。サーバーが付けた注文番号は `42` です。次にこの注文を開くときは、`Location` の宛先に `GET` を送れます。[RFC 9110 §15.3.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.2)

```http
HTTP/1.1 201 Created
Location: /orders/42
Content-Type: application/json
Content-Length: 40

{"id":42,"product_id":"P7","quantity":2}
```

### ヘッダーは誰が、何を伝えるものか

| ヘッダー | この用途での方向 | 伝えること |
| --- | --- | --- |
| `Content-Type` | 要求・応答の両方 | 今送る本文の形式。上の例では両方向とも JSON |
| `Accept` | 要求 | クライアントが受け取りたい応答の形式。実際に返った形式は応答の `Content-Type` で確かめる |
| `Authorization` | 要求 | 認証が必要なときに、採用した認証方式に従って資格情報を渡す |
| `Location` | 応答 | `201` では、新しく作成した主なリソースの宛先を知らせる |

`Content-Type` と `Accept` は役割が違います。注文を JSON で送って結果を CSV で受け取りたいなら、要求の `Content-Type` は `application/json`、`Accept` は `text/csv` です。`Accept` は希望を伝える項目です。この教材の修理依頼 API は、成功時に本文を返す操作では JSON を使います。[RFC 9110 §8.3 Content-Type](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.3)・[§12.5.1 Accept](https://www.rfc-editor.org/rfc/rfc9110.html#section-12.5.1)・[§11.6.2 Authorization](https://www.rfc-editor.org/rfc/rfc9110.html#section-11.6.2)・[§10.2.2 Location](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.2)

`GET` なら検索条件はクエリに、`DELETE` なら削除したい対象は宛先に置きます。この二つの要求の本文には HTTP で共通に定めた意味がなく、受け取ったサーバーなどが要求を拒む場合もあるためです。本文を受け取らず更新日時などのヘッダーを確かめる用途には `HEAD`、対象で使える通信上の選択肢を問い合わせる用途には `OPTIONS` もあります。[RFC 9110 §9.3.1 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1)・[§9.3.5 DELETE](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.5)・[§9.3.2 HEAD](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.2)・[§9.3.7 OPTIONS](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.7)

## 返事が来なければ、もう一度送ってよいか

注文を送った直後に通信が切れました。画面から見えるのは「応答が届かなかった」ことだけです。サーバーの側では、最初の要求がどこまで進んだかによって結果が分かれます。

```mermaid
flowchart TD
    A["注文登録の応答が届かない"] --> B{"最初の要求はどうなったか"}
    B --> C["届く前に切断した"]
    B --> D["保存後に応答が途切れた"]
    C --> E["再送に成功すると注文は1件"]
    D --> F["再送に成功すると注文は2件"]
```

**安全（safe）** は、利用者が状態の変更を求めないことです。`GET` で閲覧ログが増えても、利用者が求めたのは読み取りです。**冪等（べきとう、idempotent）** は、同じ要求を繰り返しても意図した効果が1回分と同じことです。`GET`、`PUT`、`DELETE` は冪等です。同じ注文を2回削除したとき、2回目に「すでに見つからない」と `404` を返す設計も、「対象は削除済み」と `204` を返す設計もあります。応答が同じかどうかにかかわらず、1回分の削除で目的は達成されています。[RFC 9110 §9.2.1–2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.1)

`POST` や `PATCH` の再送は、その操作の契約から判断します。「数量を2にする」なら続けて同じ要求を送っても2です。「数量を1増やす」なら送るたびに増えます。注文登録の自動再送が必要なら、クライアントが登録操作ごとに一意のキーを作り、再送でも同じキーを渡す方法があります。サーバーは利用者・キー・結果を注文と一緒に保存し、同じ操作には前回の注文番号を返します。キーを保つ期間と、同じキーに異なる内容が届いた場合の扱いも契約に含めます。[RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)・[Amazon Builders’ Library「Making retries safe with idempotent APIs」](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

ここまでで、何を、どのメソッドで送るかが決まりました。次の章では、結果を見た利用者が入力を直す、完成したデータを開く、処理を待つといった行動を選べるように、応答を設計します。

[前へ　パスとパラメータ](03-addresses.md) · [目次](../README.md) · [次へ　応答とエラー](05-responses.md)
