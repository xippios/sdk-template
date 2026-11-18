"""The capture skeleton, ``scripts/refresh_upstream.py``, and the files it writes: the
command that fills it, and the script run against pages served on the loopback interface."""

import ast
import functools
import http.server
import importlib.util
import re
import shutil
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from helpers import TABLE_HEADER


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves a directory on the loopback interface, without a log line per request."""

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def site(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    """A local directory served over HTTP on 127.0.0.1: the pages, and their base URL."""
    root = tmp_path / "site"
    root.mkdir()
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield root, f"http://127.0.0.1:{server.server_port}"
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


def test_refresh_upstream_command_follows_the_skeleton(keyless_flat: Path) -> None:
    """The command names what the skeleton defines: the hooks a source fills, --check, the
    shell and excerpt rows, the spec URL convention (row 67 b) and the one converter a
    capture script may declare (row 70); the skeleton itself declares no dependency."""
    command = " ".join((keyless_flat / ".claude/commands/refresh-upstream.md").read_text().split())
    script = (keyless_flat / "scripts/refresh_upstream.py").read_text()
    tree = ast.parse(script)
    defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    defined |= {
        target.id
        for node in tree.body
        if isinstance(node, ast.AnnAssign | ast.Assign)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    for name in ["PAGES", "SPEC_URL", "SPEC_FILE", "ATTRIBUTION", "CAPTURE"]:
        assert f"`{name}`" in command, name
        assert name in defined, name
    for name in ["reduce", "load_json", "dump_json"]:
        assert f"`{name}`" in command, name
        assert name in defined, name
    for field in ["status=403", "stable=False", "excerpt=True"]:
        assert field in command, field
    assert "uv run scripts/refresh_upstream.py --check" in command
    assert '`dependencies = ["markdownify==X.Y.Z"]`' in command
    assert "the same pin in the dev group of `pyproject.toml`" in command, "row 37 c"
    assert "`git add docs/upstream scripts`" in command, "row 35 a"
    assert script.startswith('# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n')
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)


def test_refresh_upstream_skeleton_checks_offline(
    keyless_flat: Path, tmp_path: Path, site: tuple[Path, str]
) -> None:
    """Rows 35 c and 67 c: the skeleton fetches through its one fetch function, writes a
    file row and a shell row, and ``--check`` compares without writing (here against pages
    served on the loopback interface)."""
    root, base = site
    (root / "openapi.json").write_text('{"openapi": "3.1.0"}\n')
    module = refresh_upstream(keyless_flat, tmp_path / "repo")
    out = tmp_path / "repo/docs/upstream"
    with pytest.raises(SystemExit, match="Nothing to fetch: fill PAGES"):
        module.main(["--out", str(out)])
    module.SPEC_URL = f"{base}/openapi.json"
    module.PAGES = (module.Page(f"{base}/legal", status=404, note="404 Not Found"),)
    assert module.main(["--out", str(out), "--check"]) == 1, "the stub records nothing"
    assert module.main(["--out", str(out)]) == 0
    assert (out / "openapi/openapi.json").read_text() == '{"openapi": "3.1.0"}\n'
    fetched = (out / "FETCHED.md").read_text()
    file_row = r"\| \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \| 200 \| 21 \| [0-9a-f]{64} \| "
    assert re.search(file_row, fetched), "the UTC time with Z, the status, size and sha256"
    assert f"| (no file) | {base}/legal | " in fetched
    assert "| 404 |" in fetched
    assert f"{TABLE_HEADER}\n" in fetched
    assert "None stated: no page this script reads states" in " ".join(fetched.split())
    assert module.main(["--out", str(out), "--check"]) == 0, "Fetched aside, all the same"
    (root / "openapi.json").write_text('{"openapi": "3.1.1"}\n')
    assert module.main(["--out", str(out), "--check"]) == 1
    assert (out / "openapi/openapi.json").read_text() == '{"openapi": "3.1.0"}\n', "unwritten"


def test_refresh_upstream_skeleton_stops_on_an_unrecorded_statement(
    keyless_flat: Path, tmp_path: Path, site: tuple[Path, str]
) -> None:
    """Row 35 b: every run checks the attribution, and stops before writing on a copyright,
    licence or terms that ATTRIBUTION does not record; a recorded one passes."""
    root, base = site
    (root / "guide.html").write_text("<p>Guide</p><footer>&copy; 2026 Example Ltd.</footer>\n")
    module = refresh_upstream(keyless_flat, tmp_path / "repo")
    out = tmp_path / "repo/docs/upstream"
    stub = (out / "FETCHED.md").read_bytes()
    module.PAGES = (module.Page(f"{base}/guide.html", "pages/guide.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        module.main(["--out", str(out)])
    assert (out / "FETCHED.md").read_bytes() == stub, "nothing written"
    module.ATTRIBUTION = ("\N{COPYRIGHT SIGN} 2026 Example Ltd.",)
    assert module.main(["--out", str(out)]) == 0
    assert "The documentation states `\N{COPYRIGHT SIGN} 2026" in (out / "FETCHED.md").read_text()
