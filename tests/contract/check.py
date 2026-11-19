"""生成済みの OpenAPI に載せた例を Compose の API へ送り、契約と実際の結果を比べる。"""

import argparse
from contextlib import ExitStack
from pathlib import Path

import requests
import schemathesis
from hypothesis import Phase, given, settings


BASE_URL = "http://127.0.0.1:8000"
CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"
COLLECTION = "/repair-requests"
DETAIL = "/repair-requests/{request_id}"


def check_response(contract, method, template, response, expected_status):
    assert response.status_code == expected_status, (
        f"{method} {template}: expected {expected_status}, got {response.status_code}: {response.text}"
    )
    response_spec = contract.raw_schema["paths"][template][method.lower()]["responses"][str(expected_status)]
    if expected_status == 204:
        assert response.content == b"", "204 must have an empty body"
    else:
        media_type = response.headers["Content-Type"].split(";")[0].strip()
        assert media_type in response_spec["content"], f"Undocumented response media type: {media_type}"
    contract[template][method].validate_response(response)


def request_examples(operation):
    media = operation["requestBody"]["content"]["application/json"]
    for group, examples in (("positive", media["examples"]), ("negative", operation["x-negative-examples"])):
        assert examples, f"No {group} examples for {operation['operationId']}"
        for name, example in examples.items():
            yield group, name, example


def cleanup_repair(session, path):
    response = session.delete(BASE_URL + path, timeout=10, allow_redirects=False)
    if response.status_code != 404:
        response.raise_for_status()


def check_api(session, contract):
    paths = contract.raw_schema["paths"]
    covered = set()

    def call(method, template, path, expected, **kwargs):
        response = session.request(method, BASE_URL + path, timeout=10, allow_redirects=False, **kwargs)
        check_response(contract, method, template, response, expected)
        if 200 <= expected < 300:
            covered.add((method, template))
        return response

    def compare_example(method, name, example, response):
        for field, expected in example.get("x-expected-fields", {}).items():
            actual = response.json()[field]
            assert actual == expected, f"{method} {name}: expected {field}={expected!r}, got {actual!r}"

    counts = {"POST": {"positive": 0, "negative": 0}, "PATCH": {"positive": 0, "negative": 0}}
    created = {}
    sample_location = paths[COLLECTION]["post"]["responses"]["201"]["headers"]["Location"]["example"]
    location_prefix, _, sample_id = sample_location.rpartition("/")
    assert sample_id.isdecimal() and sample_location == DETAIL.format(request_id=int(sample_id))
    with ExitStack() as cleanup:
        def remove_if_present(path):
            if path in created:
                cleanup_repair(session, path)

        for group, name, example in request_examples(paths[COLLECTION]["post"]):
            # 応答の検証に失敗しても、実際に登録された行は後始末できるようにする。
            response = session.post(BASE_URL + COLLECTION, json=example["value"], timeout=10, allow_redirects=False)
            if response.status_code == 201:
                repair = response.json()
                repair_id = repair["id"]
                assert type(repair_id) is int and repair_id > 0
                path = f"{location_prefix}/{repair_id}"
                created[path] = repair
                cleanup.callback(remove_if_present, path)
                assert response.headers["Location"] == path, "Location should identify the new repair"
            check_response(contract, "POST", COLLECTION, response, example["x-expected-status"])
            compare_example("POST", name, example, response)
            counts["POST"][group] += 1
            if response.status_code == 201:
                covered.add(("POST", COLLECTION))
                assert call("GET", DETAIL, response.headers["Location"], 200).json() == repair

        # 手元の台帳に既存の依頼があっても、今作った ID の位置からページを開く。
        path, repair = next(iter(created.items()))
        parameters = paths[COLLECTION]["get"]["parameters"]
        query = {
            parameter["name"]: parameter["examples"]["first-page"]["value"]
            for parameter in parameters if "first-page" in parameter.get("examples", {})
        }
        assert "status" in query and "limit" in query, "Missing first-page query examples"
        if repair["id"] > 1:
            query["after"] = repair["id"] - 1
        page = call("GET", COLLECTION, COLLECTION, 200, params=query).json()
        assert 1 <= len(page["items"]) <= query["limit"]
        assert page["items"][0] == repair
        if page["next_after"] is not None:
            assert page["next_after"] == page["items"][-1]["id"]

        for group, name, example in request_examples(paths[DETAIL]["patch"]):
            response = call("PATCH", DETAIL, path, example["x-expected-status"], json=example["value"])
            compare_example("PATCH", name, example, response)
            counts["PATCH"][group] += 1
            if response.status_code == 200:
                repair = {**repair, "status": example["value"]["status"]}
                assert response.json() == repair
            # 入力を拒んだ場合も含め、保存された状態を別の HTTP 要求で読み直す。
            assert call("GET", DETAIL, path, 200).json() == repair

        # 契約の列挙型からも正常な更新値を作る。対象はいま登録した自分の行だけ。
        changes = contract[DETAIL]["PATCH"].as_strategy(path_parameters={"request_id": repair["id"]})

        @settings(max_examples=4, deadline=None, derandomize=True, phases=(Phase.generate,))
        @given(status=changes.map(lambda case: case.body["status"]))
        def generated_update(status):
            changed = call("PATCH", DETAIL, path, 200, json={"status": status})
            assert changed.json() == {**repair, "status": status}
            assert call("GET", DETAIL, path, 200).json() == changed.json()

        generated_update()
        missing_spec = paths[DETAIL]["get"]["responses"]["404"]["content"]["application/problem+json"]
        for path in list(created):
            call("DELETE", DETAIL, path, 204)
            del created[path]
            assert call("GET", DETAIL, path, 404).json() == missing_spec["examples"]["not-found"]["value"]

    methods = {"get", "post", "patch", "put", "delete", "head", "options", "trace"}
    documented = {(method.upper(), path) for path, item in paths.items() for method in item if method in methods}
    assert covered == documented, f"Operations without a successful response: {documented - covered}"
    for method, result in counts.items():
        print(f"{method}: {result['positive']} positive + {result['negative']} negative explicit examples passed")
    print(f"All {len(covered)} documented operations passed the live lifecycle check.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT, help="OpenAPI YAML to check against the running API")
    args = parser.parse_args()
    with requests.Session() as session:
        check_api(session, schemathesis.openapi.from_path(args.contract))
