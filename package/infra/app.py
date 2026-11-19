from pathlib import Path

from aws_cdk import App, CfnCondition, CfnOutput, CfnParameter, Duration, Fn, IgnoreMode, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class RepairApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        # 利用者の入口は API Gateway。Lambda と DB の通信には、インターネットへの経路を持たないサブネットを使う。
        vpc = ec2.Vpc(
            self, "Vpc", max_azs=2, nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(
                name="Isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            )],
        )
        functions_sg = ec2.SecurityGroup(self, "FunctionsSG", vpc=vpc)
        endpoint_sg = ec2.SecurityGroup(self, "EndpointSG", vpc=vpc)
        # Secrets Manager の接続口で、Lambda から届く HTTPS 通信（TCP 443）を許可する。
        # プライベート DNS を有効にすると、SDK は通常のサービス名のまま、この接続口を使える。
        endpoint_sg.add_ingress_rule(functions_sg, ec2.Port.tcp(443))
        vpc.add_interface_endpoint(
            "SecretsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            open=False, security_groups=[endpoint_sg], private_dns_enabled=True,
        )

        version = self.node.try_get_context("auroraVersion")
        db_name = "repairs"
        cluster = rds.DatabaseCluster(
            self, "Database",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.of(version, version.split(".")[0]),
            ),
            credentials=rds.Credentials.from_generated_secret("repair_admin"),
            default_database_name=db_name,
            writer=rds.ClusterInstance.serverless_v2("Writer", publicly_accessible=False),
            serverless_v2_min_capacity=0, serverless_v2_max_capacity=2,
            serverless_v2_auto_pause_duration=Duration.minutes(5),
            storage_encrypted=True, vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False,
        )
        # DB 側では Lambda からの PostgreSQL 接続（TCP 5432）を許可する。実行できる SQL は DB ユーザーの権限で決まる。
        cluster.connections.allow_default_port_from(functions_sg)
        api_secret = rds.DatabaseSecret(self, "ApiSecret", username="repair_api")

        # 2つの Lambda は同じイメージを使う。handler が起動する関数を、secret が接続時に使う DB ユーザーを決める。
        def function(
            name: str, handler: str, secret: secretsmanager.ISecret, timeout: int,
        ) -> lambda_.DockerImageFunction:
            group = logs.LogGroup(
                self, name + "Logs", retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            )
            fn = lambda_.DockerImageFunction(
                self, name, vpc=vpc, security_groups=[functions_sg], log_group=group,
                code=lambda_.DockerImageCode.from_image_asset(
                    str(Path(__file__).resolve().parents[2]),
                    cmd=[handler], platform=ecr_assets.Platform.LINUX_AMD64,
                    ignore_mode=IgnoreMode.DOCKER,
                ),
                architecture=lambda_.Architecture.X86_64,
                timeout=Duration.seconds(timeout), memory_size=512,
                environment={
                    "DB_HOST": cluster.cluster_endpoint.hostname,
                    "DB_NAME": db_name,
                    "DB_SECRET_ARN": secret.secret_arn,
                },
            )
            secret.grant_read(fn)
            return fn

        # API は repair_api で依頼を読み書きする。マイグレーションは管理用ユーザーでテーブルと利用権限を用意する。
        api_handler = function("Api", "package.app.main.handler", api_secret, 28)
        admin_secret = cluster.secret
        if admin_secret is None:
            raise ValueError("The migration function requires generated database credentials.")
        migrate = function(
            "Migrate", "package.db.migrate.handler", admin_secret, 120,
        )
        # マイグレーションは repair_api のログインを設定するため、API 用の認証情報も読む。
        migrate.add_environment("DB_APP_SECRET_ARN", api_secret.secret_arn)
        api_secret.grant_read(migrate)

        # 入口では IAM が利用者の署名と呼び出し権限を確認する。
        # 次の区間で必要な「API Gateway が Lambda を呼ぶ権限」は HttpLambdaIntegration が設定する。
        gateway = apigw.HttpApi(
            self, "Gateway",
            default_authorizer=authorizers.HttpIamAuthorizer(),
            default_integration=integrations.HttpLambdaIntegration("FastAPI", api_handler),
        )
        invoke_arn = f"arn:{self.partition}:execute-api:{self.region}:{self.account}:{gateway.api_id}/*/$default"
        # 自動配信時は、作成した関数と API に限ってデプロイ後の確認を許可する。
        deploy_role = CfnParameter(
            self, "DeploymentRoleName", type="String", default="",
            allowed_pattern=r"^$|^[a-zA-Z0-9+=,.@_-]{1,64}$",
        )
        post_deploy_policy = iam.CfnPolicy(
            self, "PostDeployPolicy",
            roles=[deploy_role.value_as_string],
            policy_name="RepairApiPostDeploy",
            policy_document=iam.PolicyDocument(statements=[
                iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=[migrate.function_arn]),
                iam.PolicyStatement(actions=["execute-api:Invoke"], resources=[invoke_arn]),
            ]).to_json(),
        )
        post_deploy_policy.cfn_options.condition = CfnCondition(
            self, "UseDeploymentRole", expression=Fn.condition_not(Fn.condition_equals(deploy_role.value_as_string, "")),
        )
        # デプロイ後に使う URL と関数名、利用者の IAM ポリシーで許可するルートの ARN を出力する。
        CfnOutput(self, "ApiUrl", value=gateway.api_endpoint)
        CfnOutput(self, "MigrateFunction", value=migrate.function_name)
        CfnOutput(self, "InvokeArn", value=invoke_arn)


app = App()
RepairApiStack(app, "RepairApi")
app.synth()
