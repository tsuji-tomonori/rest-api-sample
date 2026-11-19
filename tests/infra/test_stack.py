"""デプロイせずに、実際のスタックから生成した構成を検査する。"""

import csv
import json
import os
import re
from pathlib import Path

import pytest
import yaml
from aws_cdk import App, Aspects, CfnResource, TagManager
from aws_cdk.assertions import Template
from cdk_nag import AwsSolutionsChecks

from package.infra.app import RepairApiStack


HERE = Path(__file__).parent
ROOT = HERE.parents[1]


@pytest.fixture(scope="module")
def deployment(tmp_path_factory):
    output = tmp_path_factory.mktemp("assembly")
    context = json.loads((ROOT / "package/infra/cdk.json").read_text())["context"]
    app = App(outdir=str(output), context=context)
    stack = RepairApiStack(app, "RepairApi")
    Aspects.of(stack).add(AwsSolutionsChecks())
    app.synth()
    return stack, Template.from_stack(stack), output


def test_cost_controls(deployment):
    _, template, _ = deployment
    for resource_type in (
        "AWS::EC2::NatGateway", "AWS::EC2::EIP", "AWS::EC2::Instance",
        "AWS::ElasticLoadBalancing::LoadBalancer", "AWS::ElasticLoadBalancingV2::LoadBalancer",
        "AWS::RDS::DBProxy", "AWS::EC2::InternetGateway",
    ):
        template.resource_count_is(resource_type, 0)
    template.resource_count_is("AWS::EC2::VPCEndpoint", 1)
    endpoint = next(iter(template.find_resources("AWS::EC2::VPCEndpoint").values()))["Properties"]
    assert endpoint["VpcEndpointType"] == "Interface"
    assert "secretsmanager" in json.dumps(endpoint["ServiceName"])
    assert len(endpoint["SubnetIds"]) == 2
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.has_resource_properties("AWS::RDS::DBCluster", {
        "ServerlessV2ScalingConfiguration": {"MinCapacity": 0, "MaxCapacity": 2, "SecondsUntilAutoPause": 300},
        "StorageEncrypted": True,
    })
    template.has_resource_properties("AWS::RDS::DBInstance", {
        "DBInstanceClass": "db.serverless", "PubliclyAccessible": False,
    })


def test_gateway_and_logs(deployment):
    _, template, _ = deployment
    template.resource_count_is("AWS::ApiGatewayV2::Route", 1)
    template.has_resource_properties("AWS::ApiGatewayV2::Route", {"AuthorizationType": "AWS_IAM"})
    logs = template.find_resources("AWS::Logs::LogGroup")
    assert len(logs) == 2
    assert all(group["Properties"]["RetentionInDays"] == 7 for group in logs.values())


def test_all_taggable_resources(deployment):
    stack, template, _ = deployment
    resources = template.to_json()["Resources"]
    required = {"Application": "repair-api", "Environment": "sample", "ManagedBy": "aws-cdk"}
    for node in stack.node.find_all():
        if isinstance(node, CfnResource) and (TagManager.is_taggable(node) or TagManager.is_taggable_v2(node)):
            logical_id = stack.get_logical_id(node)
            tags = resources[logical_id]["Properties"].get("Tags", {})
            if isinstance(tags, list):
                tags = {item["Key"]: item["Value"] for item in tags}
            for key, value in required.items():
                assert tags.get(key) == value, (logical_id, key)


def test_snapshot(deployment):
    _, template, _ = deployment
    document = template.to_json()
    # イメージの内容ハッシュだけを固定する。IAM・経路・削除方針などはそのまま比較する。
    for resource in document["Resources"].values():
        if resource["Type"] == "AWS::Lambda::Function":
            code = resource["Properties"]["Code"]
            encoded = json.dumps(code["ImageUri"])
            code["ImageUri"] = json.loads(re.sub(r"(?<=:)[a-f0-9]{64}\b", "ASSET_HASH", encoded))
    snapshot = HERE / "repair-stack.yaml"
    if os.getenv("UPDATE_CDK_SNAPSHOT") == "1" and not os.getenv("CI"):
        snapshot.write_text(yaml.safe_dump(document, sort_keys=True), encoding="utf-8")
    assert document == yaml.safe_load(snapshot.read_text(encoding="utf-8"))


def test_aws_solutions_findings(deployment):
    _, _, output = deployment
    with (output / "AwsSolutions-RepairApi-NagReport.csv").open(newline="") as report:
        rows = list(csv.DictReader(report))
    assert rows, "cdk-nag did not evaluate the stack"
    findings = {(row["Rule ID"], row["Resource ID"]) for row in rows if row["Compliance"] != "Compliant"}
    accepted = yaml.safe_load((HERE / "nag-exceptions.yaml").read_text(encoding="utf-8"))
    assert findings == {(rule, path) for rule, entry in accepted.items() for path in entry["resources"]}
