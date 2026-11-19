# 修理依頼 API のデプロイ

各サービスの役割と、接続に必要な設定は[第9章](../../docs/09-aws.md)で説明しています。ここでは Python CDK の操作だけを示します。コマンドは Bash 用です。デプロイには AWS CLI の認証情報、CDK CLI、Docker を使います。

## スタックを作成する

リポジトリのルートから実行します。最初に表示された AWS アカウントとロール、`cdk diff` の変更内容を確認してください。対象リージョンへの初回デプロイには [CDK のブートストラップ](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)が必要です。

```bash
export AWS_REGION=ap-northeast-1
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
aws sts get-caller-identity
uv sync --locked --group infra
cd package/infra
cdk diff RepairApi
cdk deploy RepairApi
```

Aurora のバージョンは [cdk.json](cdk.json) の `auroraVersion` で指定します。デプロイ先で作成できる PostgreSQL 17 系のバージョンを選んでください。[Aurora Serverless v2 の対応状況](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.requirements.html)

## テーブルを用意し、API を呼ぶ

出力された `MigrateFunction` の関数名を使います。初回とテーブル定義を変更したときに実行します。

```bash
MIGRATE='MigrateFunction の値'
aws lambda invoke --function-name "$MIGRATE" --cli-read-timeout 150 \
  --payload '{}' --cli-binary-format raw-in-base64-out cdk.out/migration.json
cat cdk.out/migration.json
```

`FunctionError` がなく、ファイルに `{"migration":"up-to-date"}` が返ればテーブルの準備は完了です。API を利用するロールには、出力された `InvokeArn` に対する `execute-api:Invoke` を許可します。次は一時認証情報を設定した AWS CLI プロファイルで、最初の一覧を読む例です。[API Gateway の IAM 認可](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html)

```bash
API='ApiUrl の値'
(
  source <(aws configure export-credentials --format env)
  curl --silent --show-error --include --config - "$API/repair-requests" <<SIGN
aws-sigv4 = "aws:amz:$AWS_REGION:execute-api"
user = "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY"
header = "x-amz-security-token: $AWS_SESSION_TOKEN"
SIGN
)
```

新しい台帳では `200` と `{"items":[],"next_after":null}` が返ります。デプロイ後は、Aurora の自動停止中もストレージ、VPC エンドポイント、シークレットなどに料金が発生します。環境が不要になったら `package/infra` で `cdk destroy RepairApi` を実行します。**スタックを削除すると修理依頼のデータも削除されます。** ブートストラップ用のスタックとイメージは別に管理されます。[Aurora の自動停止](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)・[PrivateLink の料金](https://aws.amazon.com/privatelink/pricing/)・[Secrets Manager の料金](https://aws.amazon.com/secrets-manager/pricing/)
