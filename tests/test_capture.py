"""The capture skeleton, ``scripts/refresh_upstream.py``, and the files it writes: the
command that fills it, and the script run against pages served on the loopback interface.

The tests of #123 fill the skeleton as a source would, setting its constants and hooks on
the imported module, and serve the pages from a temporary directory, so nothing leaves
the machine.
"""

import ast
import functools
import hashlib
import http.server
import importlib.util
import json
import os
import re
import shutil
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from helpers import TABLE_HEADER, detect_secrets_hook

NOT_FETCHED_HEADER = "| URL | HTTP | Redirects to | Reason |"
ALLOWLIST = "<!-- pragma: allowlist secret (an ETag, not a key) -->"


@dataclass
class Site:
    """Pages served on 127.0.0.1: files under ``root``, and ``routes``, a path's answer as
    ``(status, headers, body)``, for what a file cannot answer (a redirect, an ETag)."""

    root: Path
    base: str
    port: int
    routes: dict[str, tuple[int, dict[str, str], bytes]] = field(default_factory=dict)

    def page(self, name: str, text: str | bytes) -> str:
        """Write a page under the root and return its URL."""
        body = text.encode() if isinstance(text, str) else text
        (self.root / name).write_bytes(body)
        return f"{self.base}/{name}"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the site's routes, else its directory, without a log line per request."""

    def do_GET(self) -> None:
        route = self.server.routes.get(self.path)  # type: ignore[attr-defined]
        if route is None:
            super().do_GET()
            return
        status, headers, body = route
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Site]:
    """A local directory served over HTTP on 127.0.0.1, with routes of its own."""
    root = tmp_path / "site"
    root.mkdir()
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    served = Site(root, f"http://127.0.0.1:{server.server_port}", server.server_port)
    server.routes = served.routes  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield served
    server.shutdown()
    server.server_close()
    thread.join()


def refresh_upstream(rendered: Path, repo: Path) -> ModuleType:
    """A copy of a render's scripts/refresh_upstream.py and docs/upstream/ in ``repo``, the
    script imported, no pause between requests."""
    shutil.copytree(rendered / "docs/upstream", repo / "docs/upstream")
    (repo / "scripts").mkdir()
    path = Path(shutil.copy(rendered / "scripts/refresh_upstream.py", repo / "scripts"))
    spec = importlib.util.spec_from_file_location("refresh_upstream", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PAUSE = 0.0
    return module


@pytest.fixture
def capture(keyless_flat: Path, tmp_path: Path) -> tuple[ModuleType, Path]:
    """The skeleton of a render, imported, and the snapshot directory it writes to."""
    return refresh_upstream(keyless_flat, tmp_path / "repo"), tmp_path / "repo/docs/upstream"


def run(module: ModuleType, out: Path, *args: str) -> int:
    code: int = module.main(["--out", str(out), *args])
    return code


def snapshot(out: Path) -> str:
    return (out / "FETCHED.md").read_text()


def flat(text: str) -> str:
    return " ".join(text.split())


def test_refresh_upstream_command_follows_the_skeleton(keyless_flat: Path) -> None:
    """The command names what the skeleton defines: the constants and hooks a source fills,
    the records it fills them with, the page kinds, --check, the spec URL convention (row 67
    b), the one converter a capture script may declare (row 70), how its environment is
    pinned and its hooks typed, and the hand-written file (#123); the skeleton itself
    declares no dependency."""
    command = flat((keyless_flat / ".claude/commands/refresh-upstream.md").read_text())
    script = (keyless_flat / "scripts/refresh_upstream.py").read_text()
    tree = ast.parse(script)
    defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.ClassDef)}
    defined |= {
        target.id
        for node in tree.body
        if isinstance(node, ast.AnnAssign | ast.Assign)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    constants = ["PAGES", "SPEC_URL", "SPEC_FILE", "SPEC_PAGE", "ATTRIBUTION", "CAPTURE"]
    constants += ["NOT_FETCHED", "VOCABULARY"]
    for name in constants:
        assert f"`{name}`" in command, name
        assert name in defined, name
    for name in ["reduce", "canonical", "linked", "load_json", "dump_json"]:
        assert f"`{name}`" in command, name
        assert name in defined, name
    for name in ["Page", "Statement", "NotFetched"]:
        assert f"`{name}(" in command, name
        assert name in defined, name
    for keyword in ["status=403", "status=302", "stable=False", "excerpt=True", "terms=True"]:
        assert keyword in command, keyword
    for keyword in ["sample=True", "names="]:
        assert keyword in command, keyword
    assert "uv run scripts/refresh_upstream.py --check" in command
    assert '`dependencies = ["markdownify==X.Y.Z"]`' in command
    assert "the same pin in the dev group of `pyproject.toml`" in command, "row 37 c"
    for name in ["`exclude-newer`", "`uv.lock`", "`html.parser`", "`MarkdownConverter`"]:
        assert name in command, name
    for name in ["`docs/upstream/OBSERVED.md`", "`Not fetched`", "`docs/upstream/samples/`"]:
        assert name in command, name
    assert "`git add docs/upstream scripts`" in command, "row 35 a"
    assert script.startswith('# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n')
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)


def test_the_stub_lays_out_every_kind_of_row(keyless_flat: Path) -> None:
    """FETCHED.md's stub names each row the script writes, the hand-written file's and the
    samples' among them, and the table of the pages it leaves out (conventions §3)."""
    stub = (keyless_flat / "docs/upstream/FETCHED.md").read_text()
    assert f"{TABLE_HEADER}\n" in stub
    assert "## Not fetched" in stub
    assert f"{NOT_FETCHED_HEADER}\n" in stub
    assert "| OBSERVED.md |" in stub
    assert "| samples/" in stub


def test_the_rule_on_the_snapshot_leaves_the_notes_to_the_hand(keyless_flat: Path) -> None:
    """Conventions §3: the render's CLAUDE.md forbids a hand edit of ``docs/upstream/`` but
    for OBSERVED.md, which the command and the script name as the one file so written."""
    claude = flat((keyless_flat / "CLAUDE.md").read_text())
    (rule,) = [
        line for line in claude.split("- Never ") if line.startswith("edit `docs/upstream/`")
    ]
    assert "`docs/upstream/OBSERVED.md`" in rule


def test_refresh_upstream_skeleton_checks_offline(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Rows 35 c and 67 c: the skeleton fetches through its one fetch function, writes a
    file row and a shell row, and ``--check`` compares without writing (here against pages
    served on the loopback interface)."""
    module, out = capture
    spec_url = site.page("openapi.json", '{"openapi": "3.1.0"}\n')
    with pytest.raises(SystemExit, match="Nothing to fetch: fill PAGES"):
        run(module, out)
    module.SPEC_URL = spec_url
    module.PAGES = (module.Page(f"{site.base}/legal", status=404, note="404 Not Found"),)
    assert run(module, out, "--check") == 1, "the stub records nothing"
    assert run(module, out) == 0
    assert (out / "openapi/openapi.json").read_text() == '{"openapi": "3.1.0"}\n'
    fetched = snapshot(out)
    file_row = r"\| \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \| 200 \| 21 \| [0-9a-f]{64} \| "
    assert re.search(file_row, fetched), "the UTC time with Z, the status, size and sha256"
    assert f"| (no file) | {site.base}/legal | " in fetched
    assert "| 404 |" in fetched
    assert f"{TABLE_HEADER}\n" in fetched
    assert "None stated: no page this script reads states" in flat(fetched)
    assert "## Not fetched" not in fetched, "no page is left out"
    assert run(module, out, "--check") == 0, "Fetched aside, all the same"
    site.page("openapi.json", '{"openapi": "3.1.1"}\n')
    assert run(module, out, "--check") == 1
    assert (out / "openapi/openapi.json").read_text() == '{"openapi": "3.1.0"}\n', "unwritten"


def test_refresh_upstream_skeleton_stops_on_an_unrecorded_statement(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Row 35 b: every run checks the attribution, and stops before writing on a copyright,
    licence or terms that ATTRIBUTION does not record; a recorded one passes, quoted under
    Attribution with no second period after its own (#123)."""
    module, out = capture
    url = site.page("guide.html", "<p>Guide</p><footer>&copy; 2026 Example Ltd.</footer>\n")
    stub = (out / "FETCHED.md").read_bytes()
    module.PAGES = (module.Page(url, "pages/guide.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        run(module, out)
    assert (out / "FETCHED.md").read_bytes() == stub, "nothing written"
    statement = module.Statement("\N{COPYRIGHT SIGN} 2026 Example Ltd.", url, "the footer")
    module.ATTRIBUTION = (statement,)
    assert run(module, out) == 0
    fetched = flat(snapshot(out))
    assert f"`\N{COPYRIGHT SIGN} 2026 Example Ltd.`, printed at {url}: the footer" in fetched
    assert "Ltd.`." not in fetched, "a statement's own period takes no second one"


def test_the_rows_proof_a_comment_a_pdf_and_a_moving_last_modified(
    capture: tuple[ModuleType, Path], site: Site, capsys: pytest.CaptureFixture[str]
) -> None:
    """#123's proof: a page with a copyright line inside an HTML comment, a PDF, and a page
    whose Last-Modified moves between two fetches pass ``--check`` twice in a row and report
    no change, the moved Last-Modified an information line."""
    module, out = capture
    commented = "<html><body><!-- <div>&copy; 2019 Old Owner</div> --><p>Guide</p></body></html>"
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Producer (\xa9 2026 Example) >>\n%%EOF\n"
    module.PAGES = (
        module.Page(site.page("guide.html", commented), "pages/guide.html"),
        module.Page(site.page("layout.pdf", pdf), "files/layout.pdf"),
        module.Page(site.page("moving.html", "<p>Moving</p>"), "pages/moving.html"),
    )
    assert run(module, out) == 0
    moving = site.root / "moving.html"
    for step in [1, 2]:
        later = moving.stat().st_mtime + 3600 * step
        os.utime(moving, (later, later))
        capsys.readouterr()
        assert run(module, out, "--check") == 0, f"check {step}"
        output = capsys.readouterr().out
        assert "differs" not in output
        assert re.search(r"moved, no change: pages/moving\.html .*Last-Modified", output)


@pytest.mark.parametrize(
    "text",
    [
        "Read the Terms\nof Use first.",
        "Read the Terms&nbsp;of&nbsp;Use first.",
        "All rights reserved.",
        "See the Terms and Conditions.",
        "Licensed under Creative Commons.",
        "Shared under CC BY 4.0.",
    ],
)
def test_the_check_reads_the_visible_text_and_knows_the_statements(
    capture: tuple[ModuleType, Path], site: Site, text: str
) -> None:
    """#123: the search crosses a line break and a no-break space and knows each phrase the
    sources met; a script's strings and a style's names state nothing."""
    module, out = capture
    quiet = "<script>var license = 'MIT';</script><style>.copyright { color: red }</style>"
    module.PAGES = (module.Page(site.page("quiet.html", f"<p>Guide</p>{quiet}"), "pages/q.html"),)
    assert run(module, out) == 0
    module.PAGES = (module.Page(site.page("page.html", f"<p>{text}</p>"), "pages/page.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        run(module, out)


def test_each_statement_is_required_on_its_page_and_a_link_where_it_links(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: a statement is recorded with its page and checked there, a link by its target;
    a page that no longer prints or links it stops the run."""
    module, out = capture
    footer = "<footer>&copy; 2026 Example Ltd. <a href='{}'>Terms of Service</a></footer>"
    url = site.page("index.html", footer.format("https://example.org/tos"))
    module.PAGES = (module.Page(url, "pages/index.html"),)
    module.ATTRIBUTION = (
        module.Statement("\N{COPYRIGHT SIGN} 2026 Example Ltd.", url, "the footer"),
        module.Statement("Terms of Service", url, "the footer", "https://example.org/tos"),
    )
    assert run(module, out) == 0
    assert "`Terms of Service`, a link to https://example.org/tos" in flat(snapshot(out))
    site.page("index.html", footer.format("https://example.org/terms"))
    with pytest.raises(SystemExit, match="no longer links 'Terms of Service'"):
        run(module, out)
    site.page("index.html", "<footer><a href='https://example.org/tos'>Terms of Service</a>")
    with pytest.raises(SystemExit, match="no longer prints"):
        run(module, out)


def test_a_terms_page_must_print_its_lines_and_is_searched_no_further(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: a page that is itself the terms requires its quoted lines and nothing else on it
    stops the run; a terms page with no line recorded is refused."""
    module, out = capture
    terms = "<h1>License Agreement</h1><p>We grant you a license to distribute the data.</p>"
    url = site.page("terms.html", terms)
    module.PAGES = (module.Page(url, "terms/terms.html", terms=True),)
    with pytest.raises(SystemExit, match="records no statement from it"):
        run(module, out)
    module.ATTRIBUTION = (module.Statement("License Agreement", url, "the title"),)
    assert run(module, out) == 0
    site.page("terms.html", "<h1>Data Agreement</h1><p>A license to distribute.</p>")
    with pytest.raises(SystemExit, match="no longer prints 'License Agreement'"):
        run(module, out)


def test_the_check_narrows_by_a_vocabulary_that_fetched_md_lists(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: the stop names the second way out, words that state nothing, which the search
    then reads past and FETCHED.md lists."""
    module, out = capture
    module.PAGES = (
        module.Page(site.page("trade.html", "<p>An import license is required.</p>"), "p/t.html"),
    )
    with pytest.raises(SystemExit, match="VOCABULARY") as stop:
        run(module, out)
    assert "CAPTURE" in str(stop.value)
    module.VOCABULARY = ("import license",)
    assert run(module, out) == 0
    assert "`import license`" in snapshot(out)


def test_a_page_in_its_declared_charset_is_read(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Finding 1 of #188: a text page is decoded by the charset its Content-Type declares,
    and one that declares none and is not UTF-8 is read with replacement; only a binary
    body goes unread, a PDF sent without a type among them."""
    module, out = capture
    footer = "<p>Guide</p><footer>\N{COPYRIGHT SIGN} 2026 Example Ltd.</footer>"
    latin = {"Content-Type": "text/html; charset=iso-8859-1"}
    site.routes["/latin.html"] = (200, latin, footer.encode("latin-1"))
    url = f"{site.base}/latin.html"
    module.PAGES = (module.Page(url, "pages/latin.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        run(module, out)
    module.ATTRIBUTION = (module.Statement("\N{COPYRIGHT SIGN} 2026 Example Ltd.", url),)
    assert run(module, out) == 0
    module.ATTRIBUTION = ()
    site.routes["/untyped.html"] = (200, {}, b"<p>All rights reserved \xa9 2026</p>")
    module.PAGES = (module.Page(f"{site.base}/untyped.html", "pages/untyped.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        run(module, out)
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n<< /Producer (Copyright 2026 Example) >>\n%%EOF\n"
    site.routes["/layout.pdf"] = (200, {}, pdf)
    module.PAGES = (module.Page(f"{site.base}/layout.pdf", "files/layout.pdf"),)
    assert run(module, out) == 0


def test_a_statement_names_a_page_the_run_captures(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Finding 2 of #188: a statement whose page is no page of the run, such as its URL
    without the trailing slash, would never be checked, so the run stops and names it."""
    module, out = capture
    site.routes["/docs/"] = (200, {"Content-Type": "text/html"}, b"<footer>&copy; 2026 Ex</footer>")
    module.PAGES = (module.Page(f"{site.base}/docs/", "pages/docs.html"),)
    statement = module.Statement("\N{COPYRIGHT SIGN} 2026 Ex", f"{site.base}/docs", "the footer")
    module.ATTRIBUTION = (statement,)
    stub = (out / "FETCHED.md").read_bytes()
    with pytest.raises(SystemExit, match=f"from {re.escape(site.base)}/docs, a page this run"):
        run(module, out)
    assert (out / "FETCHED.md").read_bytes() == stub, "nothing written"
    module.ATTRIBUTION = (module.Statement(statement.text, f"{site.base}/docs/", "the footer"),)
    assert run(module, out) == 0


def test_a_statement_on_a_page_the_check_does_not_read_is_quoted_as_unchecked(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """The second review of #188: a statement recorded from a page whose text the check does
    not read, a PDF here, is quoted with its page as one no run checks; one on a page it
    reads is quoted as printed there."""
    module, out = capture
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n<< /Producer (Copyright 2026 Example) >>\n%%EOF\n"
    pdf_url = site.page("layout.pdf", pdf)
    html_url = site.page("guide.html", "<footer>&copy; 2026 Example Ltd.</footer>")
    module.PAGES = (module.Page(html_url, "pages/guide.html"), module.Page(pdf_url, "f/l.pdf"))
    module.ATTRIBUTION = (
        module.Statement("\N{COPYRIGHT SIGN} 2026 Example Ltd.", html_url, "the footer"),
        module.Statement("Copyright 2026 Example", pdf_url, "the PDF's producer"),
    )
    assert run(module, out) == 0
    fetched = flat(snapshot(out))
    unchecked = "a page this script does not read, so no run checks it"
    assert f"printed at {pdf_url}, {unchecked}: the PDF's producer" in fetched
    assert f"printed at {html_url}: the footer" in fetched


def test_a_line_only_a_browser_shows_is_quoted_and_never_checked(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: a copyright line that a script assembles in the browser is recorded without a
    page, quoted under Attribution as such, and no run looks for it."""
    module, out = capture
    module.PAGES = (module.Page(site.page("app.html", "<div id='app'></div>"), "pages/app.html"),)
    module.ATTRIBUTION = (
        module.Statement("Copyright (c) United Nations", "", "the footer, read on 2026-11-18"),
    )
    assert run(module, out) == 0
    assert "`Copyright (c) United Nations`, which only a browser shows" in flat(snapshot(out))


@pytest.mark.parametrize(
    ("name", "value", "quoted"),
    [
        ("license", {"name": "CC BY 4.0", "url": "https://example.org/by"}, "CC BY 4.0"),
        ("termsOfService", "https://example.org/terms", "https://example.org/terms"),
        ("contact", {"email": "data@example.org"}, "data@example.org"),
    ],
)
def test_an_api_documents_info_states_only_what_attribution_records(
    capture: tuple[ModuleType, Path], site: Site, name: str, value: Any, quoted: str
) -> None:
    """#123 and two sources' own check: an API document's ``info`` that names a licence,
    terms or a contact stops the run until ATTRIBUTION records it from that document."""
    module, out = capture
    document = {"openapi": "3.1.0", "info": {"title": "Example", name: value}, "paths": {}}
    module.SPEC_URL = site.page("openapi.json", json.dumps(document))
    with pytest.raises(SystemExit, match=f"info.{name} names"):
        run(module, out)
    module.ATTRIBUTION = (module.Statement(quoted, module.SPEC_URL, f"info.{name}"),)
    assert run(module, out) == 0


def test_check_compares_content_after_canonical(
    capture: tuple[ModuleType, Path], site: Site, capsys: pytest.CaptureFixture[str]
) -> None:
    """#123: a document served in a new order is a change by its bytes, and none once the
    source's ``canonical`` fixes the order; its row's moved sha256 is an information line."""
    module, out = capture
    module.SPEC_URL = site.page("openapi.json", '{"openapi": "3.1.0", "paths": {}}')
    assert run(module, out) == 0
    site.page("openapi.json", '{"paths": {}, "openapi": "3.1.0"}')
    assert run(module, out, "--check") == 1
    module.canonical = lambda page, body: json.dumps(json.loads(body), sort_keys=True).encode()
    capsys.readouterr()
    assert run(module, out, "--check") == 0
    assert "moved, no change: openapi/openapi.json" in capsys.readouterr().out


def test_a_page_rendered_again_with_the_same_text_is_no_change(
    capture: tuple[ModuleType, Path], site: Site, capsys: pytest.CaptureFixture[str]
) -> None:
    """#123: a converted page whose HTML moves, a nonce in a script, while its converted text
    stays, is no change to ``--check``, only its row's measures move."""
    module, out = capture
    url = site.page("guide.html", "<p>Guide</p><script>nonce='a1'</script>")
    module.PAGES = (module.Page(url, "pages/guide.md", note="converted"),)
    module.reduce = lambda page, response: re.sub(rb"<script>.*</script>", b"", response.body)
    assert run(module, out) == 0
    site.page("guide.html", "<p>Guide</p><script>nonce='b2c3'</script>")
    capsys.readouterr()
    assert run(module, out, "--check") == 0
    assert re.search(r"moved, no change: pages/guide\.md .*Bytes .*sha256", capsys.readouterr().out)


def test_a_volatile_body_keeps_last_modified_and_its_own_note(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: ``stable=False`` drops what names the bytes, size, sha256 and ETag, keeps the
    Last-Modified, and the row's note is the page's own."""
    module, out = capture
    url = site.page("missing.html", "<p>Not here</p>")
    module.PAGES = (module.Page(url, stable=False, note="a status page with a nonce"),)
    assert run(module, out) == 0
    (row,) = [line for line in snapshot(out).splitlines() if line.startswith("| (no file) |")]
    cells = [cell.strip() for cell in row.split("|")[1:-1]]
    assert cells[4:7] == ["-", "-", "-"]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", cells[7]), cells[7]
    assert cells[8] == "a status page with a nonce"


def test_a_page_read_from_another_follows_it(capture: tuple[ModuleType, Path], site: Site) -> None:
    """#123: ``linked`` names the pages a page gives the URL of, captured right after it."""
    module, out = capture
    newest = site.page("release-7.html", "<p>Release 7</p>")
    index = site.page("releases.html", f"<a href='{newest}'>Release 7</a>")
    module.PAGES = (
        module.Page(index, "pages/releases.html"),
        module.Page(site.page("about.html", "<p>About</p>"), "pages/about.html"),
    )

    def linked(row: Any) -> tuple[Any, ...]:
        if row.page.url != index:
            return ()
        href = re.search(rb"href='([^']+)'", row.response.body)
        assert href is not None
        return (module.Page(href[1].decode(), "pages/release.html", note="the newest"),)

    module.linked = linked
    assert run(module, out) == 0
    files = re.findall(r"^\| (pages/\S+) \|", snapshot(out), re.M)
    assert files == ["pages/releases.html", "pages/release.html", "pages/about.html"]


def test_spec_page_sets_the_api_documents_row(capture: tuple[ModuleType, Path], site: Site) -> None:
    """#123: ``SPEC_PAGE`` replaces the API document's default row, so a document served in a
    new order on each request needs no change of ``main``."""
    module, out = capture
    module.SPEC_URL = site.page("openapi.json", '{"openapi": "3.1.0"}')
    module.SPEC_PAGE = module.Page(
        module.SPEC_URL, module.SPEC_FILE, stable=False, note="served in a new order"
    )
    assert run(module, out) == 0
    (row,) = [line for line in snapshot(out).splitlines() if "| openapi/openapi.json |" in line]
    assert row.endswith("| served in a new order |")
    assert "| - | - | - |" in row


def test_the_page_that_names_the_api_document_must_go_on_naming_it(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """#123: a row with no file for the page that names the API document stops the run once
    the page no longer holds its URL."""
    module, out = capture
    spec = f"{site.base}/openapi.json"
    url = site.page("swagger.html", f"<script>ui({{url: '{spec}'}})</script>")
    module.PAGES = (module.Page(url, names=spec, stable=False, note="names the API document"),)
    assert run(module, out) == 0
    assert f"| (no file) | {url} |" in snapshot(out)
    site.page("swagger.html", "<script>ui({url: '/v2.json'})</script>")
    with pytest.raises(SystemExit, match="no longer holds"):
        run(module, out)


def test_observed_md_is_listed_and_left_as_written(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Conventions §3: OBSERVED.md, written by hand, has a row of its own in FETCHED.md, and
    the script neither writes nor checks it."""
    module, out = capture
    module.PAGES = (module.Page(site.page("guide.html", "<p>Guide</p>"), "pages/guide.html"),)
    assert run(module, out) == 0
    assert "| OBSERVED.md |" not in snapshot(out), "listed where it exists"
    notes = "# Observed\n\nThe API answers 200 with an empty list where it documents a 404.\n"
    (out / "OBSERVED.md").write_text(notes)
    assert run(module, out, "--check") == 1, "FETCHED.md does not list it yet"
    assert run(module, out) == 0
    assert "| OBSERVED.md |" in snapshot(out)
    assert (out / "OBSERVED.md").read_text() == notes
    assert run(module, out, "--check") == 0
    module.PAGES = (module.Page(site.page("o.html", "<p>O</p>"), "OBSERVED.md"),)
    with pytest.raises(SystemExit, match="written by hand"):
        run(module, out)


def test_not_fetched_lists_the_pages_left_out_and_those_no_anonymous_client_reads(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Conventions §3 and #41: a page left out has a row with its reason; a page behind a
    login is requested once, its redirect to another host not followed, and its row gives
    the status and that host; a redirect on the page's host is followed and noted."""
    module, out = capture
    site.routes["/admin"] = (302, {"Location": f"http://localhost:{site.port}/sso"}, b"")
    site.routes["/old.html"] = (301, {"Location": f"{site.base}/guide.html"}, b"")
    site.routes["/members"] = (403, {"Content-Type": "text/html"}, b"<p>Forbidden</p>")
    site.page("guide.html", "<p>Guide</p>")
    module.PAGES = (module.Page(f"{site.base}/admin", note="a login"),)
    with pytest.raises(SystemExit, match="to another host"):
        run(module, out)
    feed = "https://example.org/feed.xml"
    module.NOT_FETCHED = (module.NotFetched(feed, "a feed"),)
    module.PAGES = (
        module.Page(f"{site.base}/old.html", "pages/guide.html"),
        module.Page(f"{site.base}/admin", status=302, note="a login on another host"),
        module.Page(f"{site.base}/members", status=403, note="members only"),
    )
    assert run(module, out) == 0
    fetched = snapshot(out)
    assert f"redirected (301) to {site.base}/guide.html" in fetched
    assert f"## Not fetched\n\n{NOT_FETCHED_HEADER}\n" in fetched
    assert f"| {site.base}/admin | 302 | localhost:{site.port} | a login on another host |" in (
        fetched
    )
    assert f"| {site.base}/members | 403 | - | members only |" in fetched
    assert f"| {feed} | (not requested) | - | a feed |" in fetched
    assert f"| (no file) | {site.base}/admin |" not in fetched


def test_a_sample_is_kept_under_samples_and_says_so(
    capture: tuple[ModuleType, Path], site: Site
) -> None:
    """Conventions §3: an answer sample lives under ``samples/``, its row says it is one, and
    it is not searched, being an answer and no documentation."""
    module, out = capture
    url = site.page("items.json", '{"items": [{"license": "L-1"}]}')
    module.PAGES = (module.Page(url, "pages/items.json", sample=True),)
    with pytest.raises(SystemExit, match="under samples/"):
        run(module, out)
    module.PAGES = (module.Page(url, "samples/items.json", sample=True),)
    assert run(module, out) == 0
    (row,) = [line for line in snapshot(out).splitlines() if "| samples/items.json |" in line]
    assert f"| {url} |" in row
    assert "a sample" in row


def test_a_row_with_an_etag_passes_the_secret_scan(
    capture: tuple[ModuleType, Path], keyless_flat: Path, site: Site, tmp_path: Path
) -> None:
    """#42 carrying #47: the row the script writes for a quoted ETag of hex digits ends in the
    scan's allowlist mark, so the render's hook passes FETCHED.md against its unchanged
    baseline; without the mark the same row is flagged."""
    module, out = capture
    etag = '"' + hashlib.md5(b"an object store's ETag", usedforsecurity=False).hexdigest() + '"'
    headers = {"Content-Type": "application/json", "ETag": etag}
    site.routes["/openapi.json"] = (200, headers, b'{"openapi": "3.1.0"}')
    module.SPEC_URL = f"{site.base}/openapi.json"
    assert run(module, out) == 0
    fetched = snapshot(out)
    (row,) = [line for line in fetched.splitlines() if etag in line]
    assert row.endswith(f" | {ALLOWLIST}")
    scan = tmp_path / "scan"
    scan.mkdir()
    shutil.copy(keyless_flat / ".secrets.baseline", scan / ".secrets.baseline")
    (scan / "FETCHED.md").write_text(fetched)
    (scan / "unmarked.md").write_text(fetched.replace(f" {ALLOWLIST}", ""))
    hook = detect_secrets_hook(scan, "FETCHED.md")
    assert hook.returncode == 0, hook.stdout + hook.stderr
    control = detect_secrets_hook(scan, "unmarked.md")
    assert control.returncode == 1, "without the mark the ETag must be flagged"
    assert "Hex High Entropy String" in control.stdout, control.stdout
