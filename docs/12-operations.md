# 第12章　API の運用と監視を始める

朝の受付で「修理依頼を送ったのに、受付番号が出ない」と連絡がありました。当番が最初に知りたいのは、登録だけが止まっているのか、すでに登録した依頼も開けないのかです。監視を設計するときも、利用者が済ませたい操作から考えます。

## 何ができれば正常か

修理依頼なら、登録の成功は `POST` が `201` を返し、`Location` でその依頼を開けることです。一覧の成功は、権限のある社員に `200` と一覧が返ることです。1件も登録されていなければ、空の一覧が正常です。受付時間と、社員が許容できる待ち時間を業務担当者と決めておくと、どの遅延を当番に知らせるか判断できます。

**サンプルで試せる**　デプロイ直後の疎通確認では、署名なしの一覧取得で `403` が返ることを確かめます。次に、同じロールでリクエストごとに署名し、`limit=1` で `200`、`limit=0` で `422` が返ることを確認します。登録から取得までの業務の流れは、CI でテスト用の PostgreSQL に対して別に確認しています。

結果は GitHub Actions の `aws-smoke.json` に残ります。デプロイ先が未設定でもレポートは作られ、その場合、全体の `status` は `not_run` です。実環境で成功したかは、`checks` 内で該当する検査の `status` が `passed` かを読みます。`attempts` で実際の試行回数も分かります。

## 件数と時間を見て、調べる場所を絞る

CloudWatch の**メトリクス**は、リクエスト数や処理時間を期間ごとに集計した値です。**ログ**には、ある時刻に起きた個別の出来事が残ります。まず利用者の入口で影響が始まった時間を見つけ、同じ環境、同じ時間帯の関数と DB を調べます。

| 見る場所 | CloudWatch で選ぶ値 | 読み方 |
| --- | --- | --- |
| API Gateway の HTTP API（`AWS/ApiGateway`） | `ApiId` と `Stage` を選び、`Count`、`4xx`、`5xx` を見る | 呼び出し全体の中で失敗がどれくらい増えたかを調べる。正当な入力エラーや、疎通確認が意図して返した `403`、`422` も `4xx` に含まれる |
| 同じ HTTP API の待ち時間 | `Latency` と `IntegrationLatency`（ミリ秒） | 前者は Gateway が受け取って返すまで、後者は Gateway が統合先に渡してレスポンスを受けるまで。両方が延びた時間帯は、Lambda 側も調べる |
| API 用 Lambda（`AWS/Lambda`） | `FunctionName` を指定し、`Invocations`、`Errors`、`Throttles`、`Duration` を見る | `Errors` は例外やタイムアウトなど関数の実行失敗。関数が処理を終えて HTTP `422` を返しても、`Errors` は増えない。実行前に呼び出しが制限された件数は `Throttles` で分かる |
| Aurora PostgreSQL の書き込み用インスタンス（`AWS/RDS`） | `DBInstanceIdentifier` を選び、`DatabaseConnections`、`ServerlessDatabaseCapacity`、`ACUUtilization` を見る | DB への接続数、現在の容量、設定した最大容量に対する割合を同じ時刻で比べる。上限近くで遅延も続くなら、混み合う処理を調べる |

AWS の製品名に注意しましょう。この教材は API Gateway の **HTTP API** を使います。もう一つの製品 **REST API** では失敗件数は `4XXError`、`5XXError`、API を選ぶ次元は `ApiName` です。HTTP API でルート別の詳細メトリクスを有効にすると追加料金がかかります。さらに本サンプルは全操作を Gateway の `$default` ルートから FastAPI に渡すので、そこでの集計だけでは、どの業務操作が遅いかまでは分かりません。

## 当番をいつ呼ぶか

**設計例（未実装）**　サーバーエラーを早く見つけるなら、`5xx` の統計を合計（`Sum`）、集計期間を5分にします。たとえば「3件以上の区間が直近3区間中2区間ある」ときにアラームを上げます。1分間に数百件の API と1日に数件の API では、同じ3件でも影響が違います。実際の件数と問い合わせを見て、条件を調整します。

「受付時間には一覧を開ける」を数値で確かめるなら、直近30日間の受付時間を対象に、予定した定期照会のうち `200` と正しい一覧が返った割合を求めます。この測定値が**サービスレベル指標（SLI）**、「その割合を99%以上に保つ」が**サービスレベル目標（SLO）**の例です。ここで測れるのは監視用ロールからの読み取りです。待ち時間を調べるには、実際の利用者からの呼び出しが十分ある時間帯に、95% のリクエストが収まる時間（p95）を業務上の許容値と比べます。

営業時間外など、利用のない時間があるなら、エラー件数の欠測は通知条件に数えない設定（`notBreaching`）が選べます。入口に届く前に止まれば `5xx` も記録されないため、営業中に使えるかは、別の場所から署名付きの一覧取得を定期実行して確かめます。こちらは実行結果自体が途切れた場合も通知の対象です。教材の Aurora は5分間使われないと自動停止できる設定です。短い間隔で DB まで照会すると稼働が続くので、受付時間と必要な検知時間に合わせて頻度を決めます。

通知先には、たとえば CloudWatch アラームから Amazon SNS を経て API 当番に届く経路を用意します。通知に環境、影響する操作、開始時刻、確認手順を載せます。当番は最初の連絡を引き受け、登録が広く止まっていれば業務窓口に影響と次の報告時刻を伝えます。DB 接続に障害が絞れたら DB 担当へ引き継ぎます。設定後はテスト通知を送り、代理の担当者を含めて実際に受け取れるか確かめます。

## 同じエラーでも、届いた場所から調べる

| 利用者から見える症状 | 当番が次に確かめること |
| --- | --- |
| 昨日まで使えた社員に `403` が続く | 対象のロールで署名した一覧取得と、同じ時間の Lambda 呼び出しを確認する。Gateway の認可で止まった場合は、呼び出し権限、署名のリージョン、一時認証情報の有効期限を調べる |
| 新しい画面からの登録だけ `422` が増えた | 画面から送る項目と値の範囲を、その画面が利用する版の仕様書と照合する。個人情報を含まない入力例で旧版・新版の違いを再現する |
| `5xx` が増え、一覧も遅い | API 用 Lambda の `Errors`、`Throttles`、実行ログを同じ時間帯で見る。DB 接続のタイムアウトなら、DB への経路と接続数を確認する。DB が容量上限に達したときも、先に直前の変更や時間のかかった処理を確かめる |
| 朝の最初の照会だけ遅い | Aurora の容量がゼロから戻った時刻、Lambda の初期化時間、次の照会の待ち時間を比べる。停止中の Aurora は容量など一部の値だけを送り、多くのメトリクスに空白ができる |

サンプルの CDK は API 用とマイグレーション用 Lambda に別々のロググループを作り、各7日間保存します。実行ログの `REPORT` 行にはリクエスト ID と所要時間が載ります。SQL や接続の失敗を調べるときは、Aurora の PostgreSQL ログも参照できます。HTTP API のアクセスログ、DB ログの CloudWatch Logs への転送、定期監視と通知は、利用環境に合わせて追加する設定です。

### アクセスログから失敗した1件を探す

**設計例（未実装）**　CloudWatch Logs に専用のロググループを作り、HTTP API の `$default` ステージの `AccessLogSettings` に設定します。`DestinationArn` には作成したロググループの ARN（AWS 内のリソースを示す名前）、`Format` には、たとえば次の JSON を指定します。

```json
{"time":"$context.requestTime","requestId":"$context.requestId","method":"$context.httpMethod","status":"$context.status","latencyMs":"$context.responseLatency"}
```

障害時は CloudWatch Logs Insights でこのロググループと発生時刻の前後を選び、`filter status like /^5/` で 5xx の記録に絞ります。FastAPI 側にも同じ Gateway のリクエスト ID と `createRepair` などの操作名を記録すれば、どの操作だったか照合できます。Lambda 自身が付ける実行 ID は別の識別子です。

登録本文の件名や場所、署名・トークン、パスワードは記録項目から外します。ログを閲覧できる担当者と保存日数を決め、取り込み・保存・検索の費用や追加メトリクス、アラームの料金も見積もります。

## 復旧を確かめ、次の当番に残す

修正後は、障害を受けた操作を利用者と同じ入口から試します。一覧の障害なら、署名付き `GET` で `200` と仕様どおりの一覧が返るか確認できます。既存の `--smoke-only` はマイグレーションを実行せず、前述の3つの HTTP 検査を繰り返します。登録の障害なら、検証用と識別できる依頼を登録できる条件を用意し、`201` の `Location` から同じ内容を読めることまで確かめます。登録の返事だけが途切れた依頼は処理済みの可能性があるので、重複して送る前に受付状況を照合します。

通常の通信が戻り、影響した操作の成功率と待ち時間が回復したら、業務窓口に結果を伝えます。発生・検知・復旧の時刻、利用者への影響、原因、効果があった対応を短く残します。今回初めて見つけた不具合なら再現例をテストへ、連絡や切り分けで迷った点は担当者と期日を付けて運用手順へ戻します。

誤削除からの復旧は平時に点検します。教材の DB は `RemovalPolicy.DESTROY`、`deletion_protection=False` で、スタックを削除すると DB も削除されます。業務で使う場合は削除保護とバックアップの保持日数を決め、実際に戻せる最古・最新の時刻を確認します。復元テストでは、誤削除前の時刻を指定して別のクラスターを作り、検証用 API から復元先に接続して、必要な依頼が読めることまで確かめます。

## 脆弱性の通知が届いたら

サンプルの CI は変更時と毎週、ロックした Python パッケージを既知の脆弱性と照合します。検知したら、担当者はまずパッケージ名・現在の版・修正版・アドバイザリを確認します。たとえば CDK は構築時、pytest はテスト時、FastAPI はリクエスト処理中に使います。どこで使うかを調べると、どの環境を優先して更新するか判断できます。

直接指定した版は `pyproject.toml` を直して `uv lock` を実行します。間接依存なら `uv lock --upgrade-package パッケージ名` で対象を更新します。ロックファイルを一緒にレビューし、再監査と契約テストを通します。実行用ライブラリを更新したら、新しいイメージを配信して疎通を確認するまでを対応に含めます。修正版がまだない場合は、影響する機能、暫定対策、担当者、再確認日を記録します。[pip-audit](https://github.com/pypa/pip-audit)・[インフラの検査手順](../package/infra/README.md)

配布用 Lambda イメージについても、CI で Trivy が OS とライブラリを検査します。修正版がある高・緊急（HIGH・CRITICAL）の指摘があると配信を止めます。ベースイメージに原因がある場合は修正を含む版からビルドし直し、実際に配信するイメージで再検査します。[Trivy のコンテナイメージ検査](https://trivy.dev/docs/latest/target/container_image/)

## この章で決めたこと

- 業務の成功条件を先に決め、入口の HTTP レスポンスから Lambda、DB の順に同じ時間帯を調べる。
- 通知の条件、欠測時の扱い、受け取る担当者、最初の確認をセットで決める。
- 障害を受けた操作をもう一度確かめて復旧を伝え、テストや運用手順に結果を反映する。

## 根拠と参考

- **利用者の目標と当番の判断**　[Google SRE のサービスレベル目標](https://sre.google/sre-book/service-level-objectives/)・[AWS Well-Architected の運用](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operate.html)
- **入口と関数**　[AWS の HTTP API メトリクス](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-metrics.html)・[REST API のメトリクスと次元](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)・[Lambda のメトリクス](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- **データベース**　[Aurora のメトリクス](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)・[Serverless v2 の自動停止・再開](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)・[PostgreSQL ログの転送](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.CloudWatch.html)
- **バックアップと復元**　[Aurora の自動バックアップと保持期間](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.html)・[指定時刻に別のクラスターへ復元](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-pitr.html)
- **通知**　[CloudWatch アラームの評価](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-evaluation.html)・[欠測の扱い](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html)・[アラームから実行するアクション](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)
- **アクセスログ**　[HTTP API ステージの設定](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-apigatewayv2-stage-accesslogsettings.html)・[指定できるログ項目](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-logging-variables.html)・[Logs Insights の filter](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-Filter.html)
- **記録と対応**　[Python Lambda のログ](https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html)・[CloudWatch 料金](https://aws.amazon.com/cloudwatch/pricing/)・[AWS の障害後レビュー](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel12-bp02.html)
- **サンプルの設定**　[CDK](../package/infra/app.py)・[デプロイ後の疎通確認と再実行方法](../package/infra/README.md)・[第10章の AWS 構成](10-aws.md)・[第11章のテスト](11-testing.md)

[前へ　第11章　API のテストを組み立てる](11-testing.md) ｜ [目次](../README.md) ｜ [次へ　第13章　API のバージョンを上げる](13-versioning.md)
