"""For the verification branch only: run chapter 4's actual Bash fences against Compose."""

import json
import re
import subprocess
import tempfile
from email.parser import BytesHeaderParser
from pathlib import Path
from urllib.request import Request, urlopen


API = "http://127.0.0.1:8000"
BOOK = Path("docs/04-methods.md")  # CI runs from the repository root.


def read_response(raw):
    head, body = raw.replace(b"\r\n", b"\n").split(b"\n\n", 1)
    status_line, headers = head.split(b"\n", 1)
    return int(status_line.split()[1]), BytesHeaderParser().parsebytes(headers), json.loads(body)


def bash_steps(blocks):
    create, detail, rejected = blocks
    # One Bash session preserves the chapter's api variable. Supply exactly what a reader
    # would paste at the read prompt: the Location returned by THIS invocation of POST.
    return (
        "set -eu\n{\n" + create + '\n} > "$1/create"\n'
        + r"""location=$(awk 'tolower($1)=="location:" {gsub(/\r/, "", $2); print $2; exit}' "$1/create")"""
        + '\ntest -n "$location"\n{\n' + detail + '\n} > "$1/detail" <<< "$location"\n'
        + "{\n" + rejected + '\n} > "$1/rejected"\n'
    )


def main():
    book = BOOK.read_text(encoding="utf-8")
    blocks = re.findall(r"^```bash\n(.*?)\n```$", book, re.M | re.S)
    assert len(blocks) == 3 and all("curl " in block for block in blocks), "Check all chapter Bash fences"
    [http_example] = re.findall(r"^```http\n(HTTP/[^\n]+201 Created\n.*?)\n```$", book, re.M | re.S)
    _, _, sample = read_response(http_example.encode())
    [expected_error] = re.findall(r"^```json\n(.*?)\n```$", book, re.M | re.S)

    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp)
        owned_location = None
        try:
            ran = subprocess.run(
                ["bash", "-c", bash_steps(blocks), "book-curl", temp],
                capture_output=True, timeout=30, check=False,
            )
            if (output / "create").is_file():
                code, headers, created = read_response((output / "create").read_bytes())
                assert code == 201 and headers.get_content_type() == "application/json", (code, created)
                actual_id = created["id"]
                assert type(actual_id) is int and actual_id > 0
                assert headers["Location"] == f"/repair-requests/{actual_id}"
                owned_location = headers["Location"]
                assert created == {**sample, "id": actual_id}, created
            assert ran.returncode == 0, ran.stderr.decode(errors="replace")
            assert owned_location is not None

            code, headers, retrieved = read_response((output / "detail").read_bytes())
            assert code == 200 and headers.get_content_type() == "application/json" and retrieved == created
            code, headers, rejected = read_response((output / "rejected").read_bytes())
            assert code == 422 and headers.get_content_type() == "application/problem+json"
            assert rejected == json.loads(expected_error), rejected
            print(f"Book Bash fences passed: POST 201 {owned_location}, GET 200, GET limit=0 422")
        finally:
            if owned_location:
                with urlopen(Request(API + owned_location, method="DELETE"), timeout=10) as cleanup:
                    assert cleanup.status == 204


if __name__ == "__main__":
    main()
