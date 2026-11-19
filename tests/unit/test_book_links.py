"""教材内の参照先と、教科書・実例・シートの対応が保たれているか調べる。"""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SHEET = DOCS / "templates/contract-sheet.md"


def test_book_links_resolve():
    pages = [ROOT / "README.md", *DOCS.rglob("*.md"), *ROOT.glob("package/*/README.md")]
    missing = []
    for page in pages:
        markdown = page.read_text(encoding="utf-8")
        prose = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", markdown, flags=re.MULTILINE | re.DOTALL)
        for href in re.findall(r"\]\(([^()\s]+)\)", prose):
            link = urlsplit(href)
            if link.scheme or link.netloc:
                continue
            target = (page.parent / unquote(link.path)).resolve() if link.path else page
            if not target.exists():
                missing.append(f"{page.relative_to(ROOT)} -> {href}")
            elif target == SHEET and link.fragment:
                if f'id="{link.fragment}"' not in SHEET.read_text(encoding="utf-8"):
                    missing.append(f"{page.relative_to(ROOT)} -> {href}")
    assert not missing, "\n".join(missing)


def test_textbook_examples_and_sheet_cover_the_same_topics():
    chapters = sorted(path.name for path in (DOCS / "textbook").glob("[0-9][0-9]-*.md"))
    examples = sorted(path.name for path in (DOCS / "examples").glob("[0-9][0-9]-*.md"))
    assert chapters == examples
    assert [name[:2] for name in chapters] == [f"{number:02}" for number in range(1, 9)]
    sheet = SHEET.read_text(encoding="utf-8")
    for chapter in chapters:
        assert f"../textbook/{chapter}" in sheet
        assert f"../examples/{chapter}" in sheet
