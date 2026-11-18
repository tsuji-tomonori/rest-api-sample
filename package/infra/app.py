from pathlib import Path

from aws_cdk import App, CfnOutput, Duration, IgnoreMode, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class RepairApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        vpc = ec2.Vpc(
            self, "Vpc", max_azs=2, nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(
                name="Isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            )],
        )
        functions_sg = ec2.SecurityGroup(self, "FunctionsSG", vpc=vpc)
        endpoint_sg = ec2.SecurityGroup(self, "EndpointSG", vpc=vpc)
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
        cluster.connections.allow_default_port_from(functions_sg)
        api_secret = rds.DatabaseSecret(self, "ApiSecret", username="repair_api")

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

        api_handler = function("Api", "package.app.main.handler", api_secret, 28)
        migrate = function(
            "Migrate", "package.db.migrate.handler", cluster.secret, 120,
        )
        migrate.add_environment("DB_APP_SECRET_ARN", api_secret.secret_arn)
        api_secret.grant_read(migrate)

        gateway = apigw.HttpApi(
            self, "Gateway",
            default_authorizer=authorizers.HttpIamAuthorizer(),
            default_integration=integrations.HttpLambdaIntegration("FastAPI", api_handler),
        )
        CfnOutput(self, "ApiUrl", value=gateway.api_endpoint)
        CfnOutput(self, "MigrateFunction", value=migrate.function_name)
        CfnOutput(
            self, "InvokeArn",
            value=f"arn:{self.partition}:execute-api:{self.region}:{self.account}:"
                  f"{gateway.api_id}/*/$default",
        )


app = App()
RepairApiStack(app, "RepairApi")
app.synth()
