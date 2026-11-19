# 第3章　パスとパラメータ

対象が決まったら、利用者がその対象を指せるようにします。「注文42を開く」の **42** と、「未発送の注文を10件見る」の **10** は、どちらも数値ですが役割が違います。42を替えると別の注文になります。10を替えると一覧の表示件数が変わります。値をどこに置くかは、この違いから判断できます。

## 集合と1件に名前を付ける

HTTP では、対象を指定するために **URI（Uniform Resource Identifier）** という識別子を使います。注文42の URI を例に、どこに何を書くかを見てみましょう。

![注文42の URI の内訳。https がスキーム、example.com がホスト名、/orders/42 がパス。仕様書の /orders/{order_id} に注文番号 42 を当てはめると /orders/42 になる。](assets/order-uri.svg)

`https` は **スキーム**で、この例では HTTPS で通信することを示します。`example.com` は接続先の **ホスト名**、`/orders/42` はそのホストで注文42を指す **パス** です。[RFC 3986 §3 URI の構成](https://www.rfc-editor.org/rfc/rfc3986.html#section-3)

注文ごとに変わるのは番号です。そこで仕様書には、番号を入れる位置に名前を付けて `/orders/{order_id}` と書きます。この `order_id` が **パスパラメータ** です。注文42を開くときは、`{order_id}` を波かっこごと `42` に置き換えます。注文57なら、送るパスは `/orders/57` になります。[OpenAPI 3.1.1 Path Templating](https://spec.openapis.org/oas/v3.1.1.html#path-templating)

集合に複数形の名詞を使うのは、「何を扱うか」が伝わる命名規約です。RFC 3986 が定めるのは、パスを `/` で区切るといった構文です。名前には業務で通じる言葉を選び、単数・複数や複合語の綴り方は API 内でそろえます。[RFC 3986 §3.3](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)・[Google AIP-122 Collection identifiers](https://google.aip.dev/122#collection-identifiers)

**親が決まらないと子を特定できないか**は、パスを階層にする判断基準です。明細の行番号が注文ごとに付くなら、`/orders/42/lines/3` で「注文42の3行目」を特定できます。一方、荷物を配送番号だけで追跡する業務なら、`/shipments/S7` が自然です。注文との関係は、注文の表現に荷物へのリンクを載せる方法でも伝わります。利用者が常にそろえられる識別子を考えると、不要な階層を減らせます。[Google AIP-122 Nested collections](https://google.aip.dev/122#nested-collections)・[Microsoft の URI 設計指針](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#define-restful-web-api-resource-uris)

## 値の役割から置き場所を選ぶ

| 利用者が伝えること | 置き場所 | 注文を扱う例 |
| --- | --- | --- |
| どの注文か | パス | `/orders/42` の `42` |
| どの条件・範囲で一覧を読むか | クエリ（URI の `?` に続く部分） | `/orders?status=unshipped&limit=10` |
| 何を登録・変更するか | 本文 | 発送状態を変える `{"status":"shipped"}` |
| メッセージをどう解釈するか | ヘッダー | `Content-Type: application/json` は本文が JSON であることを示す |

クエリもパスとともに対象を識別する URI の一部です。「個別の注文はパス、一覧の絞り込みはクエリ」という振り分けは、多くの設計で使える指針です。同じ `status` でも、未発送の注文を**探す条件**ならクエリ、発送済みに**変更する値**なら本文と使い分けます。GET で一覧の絞り込み条件を渡すなら、クエリを使います。GET の本文には、HTTP で一般に定義された意味がありません。[RFC 3986 §3.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.4)・[RFC 9110 §8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.3)・[§9.3.1 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1)

## 省略・組み合わせ・続きの意味を決める

入力の名前を決めたら、利用者が「何を送ればどの結果になるか」を予測できるようにします。たとえば、注文の詳細と一覧を読むときの入力条件を、次のように書けます。値や上限は、この設計例で選んだものです。番号順で続きを渡す方式なら、仕様書には並び順と続きを求める方法も書きます。

| 入力 | 仕様書に書くこと |
| --- | --- |
| `order_id` | 正の整数。個別の注文を指定するときに必須 |
| `status` と `customer_id` | 任意。省略した項目では絞り込まない。両方を指定したら両方に一致する注文を返す |
| `limit` | 1〜100の整数で、省略時は20件。範囲外は入力エラー |
| `after` | 注文番号の昇順で続きの一覧を読む位置。最初は省略し、次回は応答で受け取った位置と同じ絞り込み条件を指定する |

同じ条件に複数の値を渡せるようにするときは、書き方と意味を対にして示します。たとえば `status=shipped&status=delivered` を受け付けるなら、「発送済みまたは配達済み」を返す、と書きます。OpenAPI ではパスやクエリの値を `parameters`、複数値の書き方を `style` と `explode`、本文の形式と内容を `requestBody` に記述できます。パスパラメータは必須です。[OpenAPI 3.1.1 Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)・[Style Examples](https://spec.openapis.org/oas/v3.1.1.html#style-examples)・[Request Body Object](https://spec.openapis.org/oas/v3.1.1.html#request-body-object)

最後に、実際に送る URI を1本書いてみましょう。検索語が `R&D` なら、`&` が条件の区切りと混同されないよう、値を符号化して `?q=R%26D` と送ります。プログラムでは、HTTP ライブラリのクエリ用の引数に元の値を渡します。符号化を一度だけ行えるので、すでに変換した値を重ねて変換する誤りを防げます。また、URI は履歴やログに残り得ます。認証情報は認証方式が定めるヘッダーなどで渡し、URI に含めないようにします。[RFC 3986 §2.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-2.4)・[RFC 9110 §17.9](https://www.rfc-editor.org/rfc/rfc9110.html#section-17.9)

[前へ　REST とリソース](02-rest.md) ・ [目次](../README.md) ・ [次へ　メソッドと再送](04-methods.md)
