# 第5章　応答を見て、次の行動を決める

社員が登録ボタンを押したあと、画面には何を表示しましょうか。受付が済んだら依頼の詳細へ進み、入力に誤りがあればフォームへ戻ります。画面がこの分岐に使うのが、応答の **ステータスコード** です。3桁の数字の先頭が `2` なら成功、`4` なら要求に関わる問題、`5` ならサーバー側の問題を表します。[RFC 9110 §15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15)

## 受付番号を渡す

たとえば、椅子の修理を登録して42番が付くと、画面には次の応答が届きます。ここでは読み方に関係するヘッダーだけを示します。

```http
HTTP/1.1 201 Created
Location: /repair-requests/42
Content-Type: application/json
Cache-Control: no-store

{"id":42,"title":"椅子の脚がぐらつく","location":"第1会議室","status":"open"}
```

`201 Created` は新しい依頼ができたことを表します。`Location` はその依頼の URI を示すヘッダーです。画面は本文の `id` を受付番号として表示し、あとで `Location` の宛先に `GET` を送って最新の状態を開けます。[RFC 9110 §15.3.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.2)・[§10.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.2)

この API は、照会と更新に成功すると `200 OK` と結果の JSON を返します。削除に成功すると、返すデータがないので `204 No Content` です。このとき画面は JSON を読み込もうとせず、依頼を一覧から取り除けます。[RFC 9110 §15.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.1)・[§15.3.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.5)

## 「登録できませんでした」の先を用意する

件名が空なら、社員は入力を直せます。依頼がすでに削除されていたら、直すべき項目はありません。サンプルの応答を、利用者の次の行動と一緒に整理しましょう。

| 修理依頼で起きたこと | アプリの応答 | 呼び出した側の行動 |
| --- | --- | --- |
| 登録時の JSON で閉じかっこが抜けていた | `400 Bad Request` | JSON を組み立てる処理を直す |
| 開こうとした番号の依頼が見つからない | `404 Not Found` | 番号を確かめるか、一覧に戻る |
| `Content-Type: text/csv` を指定して CSV を送った | `415 Unsupported Media Type` | JSON に変換し、`Content-Type: application/json` を指定する |
| 正しい JSON だが `title` が空だった | `422 Unprocessable Content` | 件名を入力してから送る |

空の一覧は別の結果です。`GET /repair-requests?status=open` が0件なら、検索は成功しています。この API は `200` と `{"items":[],"next_after":null}` を返します。1件を指定する照会での `404` と区別すると、画面には「未完了の依頼はありません」と表示できます。[RFC 9110 §15.5.1、§15.5.5、§15.5.16、§15.5.21](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5)

エラーの本文にも読み方の約束があります。サンプルの FastAPI は **Problem Details** という標準の形式を使います。登録されていない番号を開いた例を見てみましょう。[RFC 9457 §3](https://www.rfc-editor.org/rfc/rfc9457.html#section-3)

```http
HTTP/1.1 404 Not Found
Content-Type: application/problem+json

{"type":"about:blank","title":"Not Found","status":404,"detail":"修理依頼が見つかりません。"}
```

`type` は問題の種類、`title` はその短い名前、`detail` は今回の状況を人に伝える説明です。ここでの `about:blank` は、HTTP ステータスが示す意味で十分だという指定です。本文の `status` には同じ番号が入ります。画面は実際の HTTP ステータスで分岐し、利用者には `detail` を表示できます。日本語の文言を変更しても分岐には影響しません。[RFC 9457 §3.1](https://www.rfc-editor.org/rfc/rfc9457.html#section-3.1)・[§4.2.1](https://www.rfc-editor.org/rfc/rfc9457.html#section-4.2.1)

AWS では、権限の確認をする API Gateway も応答を返します。FastAPI に届く前に要求を拒んだ場合、本文の形式はアプリが決めた形式と異なることがあります。画面は先にステータスと `Content-Type` を確認してから本文を読みます。また、サーバーが一時的に利用できない `503` では、応答に `Retry-After` があれば再試行の目安になります。再送できる操作かどうかは第4章の考え方で判断します。[AWS「Control access to HTTP APIs with IAM authorization」](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html)・[RFC 9110 §15.6.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.4)

## 以前に見た依頼は、今も同じだろうか

ブラウザーなどには、以前の応答を保存し、同じ問い合わせに再利用する仕組みがあります。これをキャッシュと呼びます。受付時の応答にあった `Cache-Control: no-store` は、キャッシュへの保存を禁じる指定です。この教材では社内の修理情報にこの方針を採り、依頼を開くたびにサーバーに問い合わせます。[RFC 9111 §5.2.2.5](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.5)

一方、最新の内容を読み込んでも、その画面を開いたまま別の人が更新することはあります。**同時編集を扱う場合の設計例**として、サンプルを拡張するなら次のようにできます。

1. 依頼を開いたとき、サーバーは応答に `ETag: "v3"` を添えます。これは取得した内容の版を識別する目印です。
2. 画面は更新時に `If-Match: "v3"` を送ります。「表示した版とまだ一致する場合に更新する」という条件です。
3. 先に別の人が更新し、現在の版が `"v4"` なら、サーバーは変更を適用せず `412 Precondition Failed` を返します。画面は依頼を読み直し、担当者が変更内容を確認できます。

この方式を実装するときは、データベースでも版の一致を条件に更新します。サーバーが版を確かめてから書き込むまでの間に、別の変更が割り込むのを防ぐためです。[RFC 9110 §8.8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3)・[§13.1.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1)

これで「何を送るか」「どの応答なら次に何ができるか」がそろいました。次の章では、この約束を実装者と利用者の双方が読める形にまとめます。

[前へ　メソッドと再送](04-methods.md) · [目次](../README.md) · [次へ　業務を API の契約にする](06-contract.md)
