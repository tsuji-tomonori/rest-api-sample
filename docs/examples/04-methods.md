# 実例編 04　登録、照会、完了、削除を選び分ける

[教科書 04　HTTP メソッドの選び方](../textbook/04-methods.md) ｜ [設計シート B2・B8　メソッドと再送](../templates/contract-sheet.md#operation)

## 要望と決めること

社員が翌日に依頼を開いたときは、現在の状態を読みたいだけです。総務が「完了」を押したときは、同じ依頼を開いた社員にも新しい状態が見える必要があります。この違いを、宛先とメソッドの組み合わせで伝えます。

## 選択肢と選んだ理由

| 操作 | 選んだメソッドとパス | この業務で選んだ理由 |
| --- | --- | --- |
| 未完了の依頼を探す | `GET /repair-requests?status=open` | 一覧を繰り返し開いても台帳を変えない |
| 1件の進み具合を見る | `GET /repair-requests/{request_id}` | 受付番号が分かれば同じ依頼を読み直せる |
| 修理を依頼する | `POST /repair-requests` | 新しい依頼を追加する。受付番号は保存時にサーバーが発行する |
| 修理を完了にする | `PATCH /repair-requests/{request_id}` | 件名と場所を保ち、状態だけを指定した値に変える |
| 誤登録を取り除く | `DELETE /repair-requests/{request_id}` | その番号の依頼を台帳から取り除き、一覧と個別の照会からも消す |

完了を `GET /complete/42` とする案では、リンクを開いたときにも状態が変わります。完了ボタンを押したときにだけ `PATCH` を送り、本文には `{"status":"completed"}` を入れます。この指示を2回送っても、最終状態は完了です。

登録中に通信が切れた場合は事情が異なります。台帳には保存済みで、返事だけが届かなかったかもしれません。この契約で同じ `POST` を送り直すと別の番号が発行され得るので、自動再送を避けます。[再送の原則](../textbook/04-methods.md)

## 条件が変わったら

- **利用者側で番号を決める場合**　番号と全項目がそろった修理依頼を外部台帳から同期するなら、`PUT /repair-requests/57` に完成形を送り、57番の内容を置き換える設計が候補です。今回の受付番号はサーバーが決めます。
- **削除後も監査資料を残す場合**　通常の画面から消す契約を保ちながら、内部には削除日時と行を残せます。取り消した依頼も利用者がそのまま開く必要があれば、「取消済み」を状態に追加する案もあります。

## 設計シートの記入結果

**目的**は「総務が修理の完了を記録する」。**操作**は `PATCH /repair-requests/{request_id}`。**成功**は `200` と更新後の依頼。**完成の確かめ方**は、同じ番号をもう一度開き、件名と場所が元のままで `status` が `completed` になっていることです。

<details>
<summary>手元で確かめる（任意）　完了と削除を確かめる</summary>


[実例 01](01-http.md)で手元の台帳に作った依頼を使います。次の1行を UTF-8 で `completed.json` に保存し、そのフォルダーでコマンドを実行してください。各 `NUMBER` は自分が作った依頼の番号に替えます。Windows の PowerShell では `curl.exe` を使います。

```json
{"status":"completed"}
```

```console
curl -i -X PATCH -H "Content-Type: application/json" --data-binary "@completed.json" "http://127.0.0.1:8000/repair-requests/NUMBER"
curl -i "http://127.0.0.1:8000/repair-requests/NUMBER"
```

両方で `200` が返り、同じ番号と完了状態を読めます。次の2行は、誤登録を取り除いた後どう見えるかを確かめる手順です。練習用に作った依頼を取り除くときに実行します。

```console
curl -i -X DELETE "http://127.0.0.1:8000/repair-requests/NUMBER"
curl -i "http://127.0.0.1:8000/repair-requests/NUMBER"
```

1行目は `204` で本文は空、2行目は `404` です。次は[実例 05](05-responses.md)で、結果を受け取った画面が何をすればよいかを決めます。

</details>

[前へ　第3章](03-inputs.md) ｜ [教科書 04](../textbook/04-methods.md) ｜ [実装 04](../implementation/04-methods.md) ｜ [シート B2](../templates/contract-sheet.md#b2) ｜ [次へ　第5章](05-responses.md) ｜ [目次](../../README.md)
