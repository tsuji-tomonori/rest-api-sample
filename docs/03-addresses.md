# 第3章　パスとパラメータ

「注文42を開く」の **42** と、「未発送の注文を10件見る」の **10** は、どちらも数値です。42を替えると、別の注文を開きます。10を替えると、一度に表示する件数が変わります。API の入力を設計するときは、それぞれの値を替えると何が変わるかを考えます。

## 業務の言葉からパスを組み立てる

HTTP では、**URI（Uniform Resource Identifier）** で対象を識別します。図の `https` は通信方式を示すスキーム、`example.com` は接続先のホスト名です。その後の `/orders/42` を **パス** と呼びます。[RFC 3986 §3 URI の構成](https://www.rfc-editor.org/rfc/rfc3986.html#section-3)

![注文42の URI の内訳。https がスキーム、example.com がホスト名、/orders/42 がパス。仕様書の /orders/{order_id} に注文番号 42 を当てはめると /orders/42 になる。](assets/order-uri.svg)

パスを決めるときは、利用者の言葉を次の順に読み解きます。

1. **扱う対象に名前を付ける。** 「注文を開く」なら、対象は「注文」です。取得という操作は HTTP メソッドの `GET` で表せるので、パスの名前には名詞の `orders` を使います。同じ注文を更新するときも、この名前が使えます。
2. **集合と1件を分ける。** `/orders` は注文の集まりです。1件を指すときは番号を足し、仕様書には `/orders/{order_id}` と書きます。波かっこの中は実際の値に置き換える部分で、これが **パスパラメータ** です。送るパスは注文42なら `/orders/42`、注文57なら `/orders/57` になります。
3. **親の番号が必要なときに階層を足す。** 同じ「明細3」が注文ごとにあるなら、`/orders/42/lines/3` で特定できます。一方、荷物を配送番号だけで特定できるなら、`/shipments/S7` を直接開けます。注文からその荷物を探せるようにするには、注文の応答に荷物のリンクを載せる方法があります。

集合を複数形にすると、名前から「注文の集まり」と分かります。修理依頼の `/repair-requests` のように、固定の英単語は小文字でそろえ、単語の境目をハイフンで示すと、読み手が綴りを予測しやすくなります。これは教材で選ぶ**命名規約**です。RFC 3986 は URI の構文を定めます。集合名の単数・複数や英単語の区切り方は、API ごとに決められます。[RFC 3986 §3.3](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)・[Zalando のパス命名規約](https://opensource.zalando.com/restful-api-guidelines/#129)・[Microsoft のリソース設計指針](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#define-restful-web-api-resource-uris)・[OpenAPI のパスの書き方](https://spec.openapis.org/oas/v3.1.1.html#path-templating)

**動詞を付けたくなったら、操作後に何をたどりたいか**を考えてみてください。「注文を取り消す」だけなら、注文の状態を変更する方法があります。取消理由や承認結果を後から読むなら、`/orders/42/cancellation-requests` に取消申請を登録するほうが、経過を追いやすくなります。標準の操作では固有の手続きを表しにくい場合に、独自の操作名を許す設計指針もあります。たとえば Google は、その場合の表記として `:archive` のような接尾辞を定めています。[Google AIP-136 Custom methods](https://google.aip.dev/136#guidance)

階層は、利用者が知っている番号で目的の対象を指せるところまでにします。HTTP には「3階層まで」といった決まりも、URI の長さの一律の上限もありません。RFC 9110 の **8,000オクテット（バイト）** は、送受信する側が少なくともその長さの URI を扱えるようにするための推奨値です。実際に通せる長さはサーバーや中継機器の制限によります。対象の URI が受け付けられる長さを超えた場合の応答は `414 URI Too Long` です。[RFC 9110 §4.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.1)・[§15.5.15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.15)

## 入力は、その値を使う目的で分ける

宛先を決めたら、残りの入力を置く場所を考えます。**クエリ**は URI の `?` に続く部分、**ヘッダー**は本文の形式などを知らせる項目、**リクエスト本文**は相手に届けるデータです。[RFC 3986 §3.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.4)・[RFC 9110 §6.3–6.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-6.3)

| 置き場所 | 何を伝えるか | 例 | どこに現れるか |
| --- | --- | --- | --- |
| パス | 操作の対象 | `/orders/42` の `42` | URL の一部。ページを開くとアドレス欄に表示される |
| クエリ | 一覧の絞り込みや返す件数 | `?status=unshipped&limit=10` | URL の一部。URL をコピーすると条件も含まれる |
| ヘッダー | 受け取りたい形式、送る本文の形式、認証情報など | `Accept: application/json`、`Authorization` | URL の外。送受信するプログラムや、設定に応じて通信の記録に現れる |
| リクエスト本文 | 登録する内容、対象に加える変更 | `{"status":"shipped"}` | URL の外。受付側のアプリが読み取る。本文を記録する設定ならログにも残る |

同じ `status` でも、未発送の注文を**探す**ならクエリに、特定の注文を発送済みに**変える**なら本文に置きます。たとえば最初の要求は次のように読めます。1行目は「未発送の注文を最大10件」、最後の行は「応答は JSON 形式を希望」です。[RFC 9110 §9.3.1 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1)・[§12.5.1 Accept](https://www.rfc-editor.org/rfc/rfc9110.html#section-12.5.1)

```http
GET /orders?status=unshipped&limit=10 HTTP/1.1
Host: example.com
Accept: application/json
```

JSON の本文を送るときは、送り手が `Content-Type: application/json` と記します。`Accept` は欲しい応答の形式、`Content-Type` は実際に付けた本文の形式です。GET の本文には HTTP で一般に定義された意味がないため、この例では絞り込み条件をクエリで渡します。[RFC 9110 §8.3 Content-Type](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.3)・[第4章　操作に合うメソッドを選ぶ](04-methods.md)

### URL に残す情報を選ぶ

HTTPS は、暗号化された接続を通る間の要求を保護します。受信したサーバーや、HTTPS の接続をいったん受けて次へ渡す中継機器は、その区間の内容を読めます。URL はアクセスログの設定によって記録され、ブラウザーでページとして開けば閲覧履歴にも残り得ます。画面の裏で呼んだ API の URL が、毎回アドレス欄に出るわけではありません。[RFC 9110 §4.2.2 HTTPS](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.2.2)・[§17.9 URI に含まれる機密情報](https://www.rfc-editor.org/rfc/rfc9110.html#section-17.9)

そのため、認証用のトークンは URL に含めず、採用した方式で定める場所に渡します。たとえば Bearer 認証では `Authorization` ヘッダーを使います。ヘッダーや本文に入れた値も、送受信側では読めます。ログに残す項目を決めるときは、トークンやパスワードを記録対象から外します。[RFC 6750 §2.1 Bearer 認証](https://www.rfc-editor.org/rfc/rfc6750.html#section-2.1)・[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude)

## 省略・組み合わせ・続きの意味を決める

値の置き場所が同じでも、API ごとに入力の約束は変わります。注文の例なら、次のように仕様書に書けます。

| 入力 | この例で決めたこと |
| --- | --- |
| `order_id` | 正の整数。個別の注文を指定するときに必須 |
| `status` と `customer_id` | 任意。省略した項目では絞り込まない。両方を指定したら両方に一致する注文を返す |
| `limit` | 1〜100の整数。省略時は20件。範囲外は入力エラー |
| `after` | 注文番号の昇順で続きを読む位置。最初は省略し、次のページでは応答で得た位置と同じ絞り込み条件を指定する |

複数の値を受け付けるなら、記法と意味を対にします。たとえば `status=shipped&status=delivered` を「発送済み**または**配達済み」と定めます。OpenAPI では、パスやクエリの値は `parameters`、複数値の書き方は `style` と `explode`、本文は `requestBody` に記述できます。パスパラメータは必須です。[OpenAPI 3.1.1 Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)・[Style Examples](https://spec.openapis.org/oas/v3.1.1.html#style-examples)・[Request Body Object](https://spec.openapis.org/oas/v3.1.1.html#request-body-object)

値自体に区切り文字が入ることもあります。検索語 `R&D` を渡すなら、`&` を区切りと区別するため、送るクエリは `?q=R%26D` になります。HTTP ライブラリにクエリの値を渡すときは、元の `R&D` を渡し、符号化を一度だけ任せます。[RFC 3986 §2.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-2.4)

[前へ　REST とリソース](02-rest.md) ・ [目次](../README.md) ・ [次へ　メソッドと再送](04-methods.md)
