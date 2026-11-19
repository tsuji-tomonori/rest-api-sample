"""Chromium で Swagger UI を操作し、表示された依頼一覧を実際の応答と比べる。"""

import json

from playwright.sync_api import expect, sync_playwright


BASE_URL = "http://127.0.0.1:8000"


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(45_000)
        page.goto(f"{BASE_URL}/docs", wait_until="domcontentloaded")

        # Swagger UI がタグと OpenAPI の operationId から作る ID で、一覧取得の操作欄を選ぶ。
        operation = page.locator("#operations-default-list_repairs_repair_requests_get")
        operation.locator("button.opblock-summary-control").click()
        operation.get_by_role("button", name="Try it out", exact=True).click()
        with page.expect_response(
            lambda response: response.request.method == "GET"
            and response.url.split("?", 1)[0] == f"{BASE_URL}/repair-requests"
        ) as received:
            operation.get_by_role("button", name="Execute", exact=True).click()

        response = received.value
        assert response.status == 200, f"{response.status} from {response.url}"
        payload = response.json()
        assert isinstance(payload["items"], list) and "next_after" in payload

        result = operation.locator("table.live-responses-table tbody")
        expect(result.locator(".response-col_status")).to_have_text("200")
        body = result.get_by_role("heading", name="Response body", exact=True).locator("..").locator("pre")
        expect(body).to_be_visible()
        assert json.loads(body.inner_text()) == payload, "Displayed JSON differs from the API response"
        browser.close()
    print("Swagger UI executed GET /repair-requests and displayed the HTTP 200 response body.")


if __name__ == "__main__":
    main()
