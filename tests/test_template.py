"""Generation tests: variants render, pass ruff, and respect skip-if-exists."""

import ast
import functools
import hashlib
import http.server
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import threading
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from copier import run_copy
from pathspec import PathSpec

ROOT = Path(__file__).resolve().parents[1]

BASE_ANSWERS: dict[str, object] = {
    "source_name": "Example Data Service",
    "upstream_url": "https://api.example.org",
    "upstream_docs_url": "https://api.example.org/docs",
    "api_base_url": "https://api.example.org/v1",
    "rate_limit_per_minute": 120,
}


# A stand-in for a 40-character sdk-core commit, never fetched: hex of high entropy, as a
# real SHA is, computed so that no literal in this file looks like a secret.
FAKE_CORE_SHA = hashlib.sha1(b"a fixed stand-in for an sdk-core commit").hexdigest()


def keyed(env: str, location: str = "query", name: str | None = None) -> dict[str, object]:
    """Answers for how the key is sent; values are variables so no line looks like a secret."""
    answers: dict[str, object] = {"api_key_env": env, "api_key_location": location}
    if name is not None:
        answers["api_key_name"] = name
    return answers


VARIANTS: dict[str, dict[str, object]] = {
    "query-key": {"source_slug": "usda-nass", **keyed("NASS_API_KEY", "query", "key")},
    "header-key": {
        "source_slug": "comtrade",
        **keyed("COMTRADE_API_KEY", "header", "Ocp-Apim-Subscription-Key"),
    },
    "bearer": {
        "source_slug": "abc-data",
        "rate_limit_burst": 3,
        "rate_limit_provenance": "self-imposed",
        "core_version": "0.3.0",
        **keyed("ABC_API_KEY", "bearer"),
    },
    "bearer-git-core": {
        "source_slug": "pinned-data",
        "core_git_ref": FAKE_CORE_SHA,
        **keyed("PINNED_API_KEY", "bearer"),
    },
    "open": {"source_slug": "eurostat", **keyed("")},
    "nested": {"source_slug": "usda-nass", **keyed("NASS_API_KEY", "query", "key")},
    "hyphenated-flat": {"source_slug": "world-bank", "import_path": "world_bank", **keyed("")},
    "long-name": {
        "source_slug": "fao-faostat-bulk",
        # sdk-usda-esmis's name, 64 characters, which broke the line length of four
        # docstrings (test_a_long_source_name_passes_ruff)
        "source_name": "USDA ESMIS (Economics, Statistics and Market Information System)",
        **keyed("FAOSTAT_API_KEY", "header", "X-Api-Key"),
    },
}


def package_dir(answers: dict[str, object]) -> str:
    import_path = str(answers.get("import_path") or str(answers["source_slug"]).replace("-", "."))
    return import_path.replace(".", "/")


EXPECTED_FILES = [
    "src/xippios/{pkg}/__init__.py",
    "src/xippios/{pkg}/py.typed",
    "src/xippios/{pkg}/_version.py",
    "src/xippios/{pkg}/_client.py",
    "src/xippios/{pkg}/errors.py",
    "src/xippios/{pkg}/models.py",
    "src/xippios/{pkg}/tasks.py",
    "src/xippios/{pkg}/api/__init__.py",
    "src/xippios/{pkg}/mcp.py",
    "src/xippios/{pkg}/http.py",
    "src/xippios/{pkg}/reference/README.md",
    "src/xippios/{pkg}/params.py",
    "src/xippios/{pkg}/enums.py",
    "scripts/refresh_reference.py",
    "scripts/refresh_upstream.py",
    "tests/conftest.py",
    "tests/test_family.py",
    "tests/test_tasks.py",
    "tests/test_live.py",
    "docs/upstream/FETCHED.md",
    "CLAUDE.md",
    ".claude/family.md",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "pyproject.toml",
    ".pre-commit-config.yaml",
    ".secrets.baseline",
    ".gitattributes",
    ".gitignore",
    ".python-version",
    ".github/workflows/ci.yml",
    ".github/workflows/publish.yml",
    ".github/workflows/gates.yml",
    ".github/workflows/live.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".claude/settings.json",
    ".claude/commands/add-endpoint.md",
    ".claude/commands/record-fixture.md",
    ".claude/commands/refresh-upstream.md",
    ".claude/commands/refresh-reference-data.md",
    ".claude/commands/release-prep.md",
    ".claude/commands/adopt-release.md",
    ".copier-answers.yml",
]

# Template v0.2.1 deleted them: core's family check, which tests/test_family.py collects,
# makes their checks (conventions §10).
REMOVED_FILES = ["tests/test_layout.py", "tests/test_adapters.py"]
FAMILY_TEST = "from xippios.core.testing.family import *  # noqa: F403\n"


@pytest.fixture(scope="session")
def template_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A snapshot of the working tree, so uncommitted template changes are what is tested."""
    src = tmp_path_factory.mktemp("template-src")
    shutil.copy(ROOT / "copier.yml", src / "copier.yml")
    shutil.copytree(ROOT / "template", src / "template")
    return src


def generate(template_src: Path, dst: Path, **answers: object) -> Path:
    run_copy(
        str(template_src),
        str(dst),
        data={**BASE_ANSWERS, **answers},
        defaults=True,
        overwrite=True,
        quiet=True,
    )
    return dst


def ruff(dst: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args], cwd=dst, capture_output=True, text=True, check=False
    )


@pytest.fixture(params=sorted(VARIANTS), scope="session")
def generated(
    request: pytest.FixtureRequest, template_src: Path, tmp_path_factory: pytest.TempPathFactory
) -> tuple[str, Path]:
    name = request.param
    dst = generate(template_src, tmp_path_factory.mktemp(name) / "repo", **VARIANTS[name])
    return name, dst


def test_layout(generated: tuple[str, Path]) -> None:
    name, dst = generated
    answers = VARIANTS[name]
    pkg = package_dir(answers)
    for rel in EXPECTED_FILES:
        assert (dst / rel.format(pkg=pkg)).is_file(), rel
    for rel in REMOVED_FILES:
        assert not (dst / rel).exists(), f"{rel}: the family check makes its checks"
    fixture_rule = "the fixture rule lives in /record-fixture and conventions §10"
    assert not (dst / "tests/fixtures").exists(), fixture_rule
    assert (dst / "tests/test_family.py").read_text() == FAMILY_TEST
    level = (dst / "src/xippios" / pkg).parent
    while level != dst / "src":
        assert not (level / "__init__.py").exists(), level
        level = level.parent
    pyproject = (dst / "pyproject.toml").read_text()
    assert ("[tool.uv.sources]" in pyproject) is bool(answers.get("core_git_ref"))
    tool = tomllib.loads(pyproject)["tool"]
    assert tool["mypy"]["files"] == ["src", "tests", "scripts"], "scripts/ is type-checked"
    assert tool["pytest"]["ini_options"]["junit_family"] == "xunit1", "record_property"
    sdist = tool["hatch"]["build"]["targets"]["sdist"]
    assert sdist == {"include": ["/src", "/docs", "/README.md", "/CHANGELOG.md", "/LICENSE"]}
    assert "tests" not in json.dumps(sdist), "the sdist ships no tests; they live in the repo"


def test_dev_ruff_is_the_pre_commit_hooks(generated: tuple[str, Path]) -> None:
    """A new lock resolves the ruff the pre-commit hook runs, not the newest one."""
    _, dst = generated
    hooks = yaml.safe_load((dst / ".pre-commit-config.yaml").read_text())["repos"]
    (rev,) = [repo["rev"] for repo in hooks if repo["repo"].endswith("/ruff-pre-commit")]
    dev = tomllib.loads((dst / "pyproject.toml").read_text())["dependency-groups"]["dev"]
    assert [spec for spec in dev if spec.startswith("ruff")] == [f"ruff=={rev.removeprefix('v')}"]


def test_generated_code_is_lint_and_format_clean(generated: tuple[str, Path]) -> None:
    _, dst = generated
    check = ruff(dst, "check", ".")
    assert check.returncode == 0, check.stdout + check.stderr
    fmt = ruff(dst, "format", "--check", ".")
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr


def test_generated_python_compiles(generated: tuple[str, Path]) -> None:
    _, dst = generated
    for path in dst.rglob("*.py"):
        compile(path.read_text(), str(path), "exec")


def test_answers_file_round_trips(generated: tuple[str, Path]) -> None:
    name, dst = generated
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["source_slug"] == VARIANTS[name]["source_slug"]
    assert answers["api_key_env"] == VARIANTS[name]["api_key_env"]
    assert answers["import_path"] == package_dir(VARIANTS[name]).replace("/", ".")
    assert "package_dir" not in answers, "computed answers are derived, never recorded"
    assert "live_schedule" not in answers
    for gone in ["source_pkg", "domain_topic", "needs_write_tools"]:
        assert gone not in answers, f"{gone}: no question asks it"


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ([], "--topic DOMAIN is required to create the repository"),
        (["--local-only", "--topic", "Trade_Data"], "--topic Trade_Data: use lowercase letters"),
        (["--topic", "trade--data"], "--topic trade--data: use lowercase letters"),
        (["--topic", "trade-data", "--evidence", "absent.md"], "--evidence absent.md: no such"),
    ],
)
def test_new_source_checks_its_flags_before_it_generates(
    tmp_path: Path, args: list[str], error: str
) -> None:
    """The domain topic is new-source.sh's flag, no copier answer, and the evidence a file;
    a bad one of either costs nothing."""
    dest = tmp_path / "sdk-ex"
    script = [str(ROOT / "scripts/new-source.sh"), "ex", "--dest", str(dest), *args]
    run = subprocess.run(script, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert run.returncode == 2, run.stdout + run.stderr
    assert error in run.stderr
    assert not dest.exists(), "refused before anything is generated"


def test_no_jinja_left_behind(generated: tuple[str, Path]) -> None:
    """Workflow files carry GitHub's own ${{ }}; nothing else may, and nothing else in them."""
    _, dst = generated
    for path in dst.rglob("*"):
        if not path.is_file() or path.suffix not in {
            ".py",
            ".md",
            ".toml",
            ".yml",
            ".yaml",
            ".json",
        }:
            continue
        text = path.read_text()
        assert "{%" not in text, path
        if ".github/workflows" in str(path):
            assert not re.search(r"(?<!\$)\{\{", text), f"{path}: only ${{{{ }}}} may remain"
        else:
            assert "{{" not in text, path


def test_no_dotted_import_path_used_as_a_directory(generated: tuple[str, Path]) -> None:
    """A nested import path (usda.nass) must appear as usda/nass wherever a path is meant."""
    name, dst = generated
    dotted = package_dir(VARIANTS[name]).replace("/", ".")
    if "." not in dotted:
        pytest.skip("flat import path")
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".md", ".toml", ".yml", ".yaml"}:
            assert f"src/xippios/{dotted}" not in path.read_text(), path


def test_key_auth_matches_location(template_src: Path, tmp_path: Path) -> None:
    for location, needle in [
        ("query", 'auth = QueryKeyAuth("key", API_KEY_ENV, source=SOURCE)'),
        ("header", 'auth = HeaderKeyAuth("X-Api-Key", API_KEY_ENV, source=SOURCE)'),
        ("bearer", "auth = BearerAuth(API_KEY_ENV, source=SOURCE)"),
    ]:
        dst = generate(
            template_src, tmp_path / location, source_slug="ex", **keyed("EX_API_KEY", location)
        )
        client = (dst / "src/xippios/ex/_client.py").read_text()
        assert needle in client, location
        assert '    "auth",\n' in client, "auth is exported"
    with pytest.raises(ValueError, match="api_key_location"):
        generate(template_src, tmp_path / "basic", source_slug="ex", **keyed("EX_API_KEY", "basic"))
    dst = generate(template_src, tmp_path / "open", source_slug="ex", **keyed(""))
    client = (dst / "src/xippios/ex/_client.py").read_text()
    assert "Auth" not in client
    assert '"auth"' not in client
    assert "API_KEY_ENV: str | None = None" in client
    assert "client = AsyncClient(config)" in client


def test_skip_if_exists_protects_content_files(template_src: Path, tmp_path: Path) -> None:
    """A source's files survive a re-render; the template's own are rendered again.

    The slug ends in -api, so the package itself is .../api/: the patterns name the package
    directory, and its mcp.py is the template's while its api/ is the source's.
    """
    dst = generate(template_src, tmp_path / "repo", source_slug="ex-api", **keyed(""))
    pkg = "src/xippios/ex/api"
    names = ["tasks.py", "_client.py", "errors.py", "__init__.py", "api/__init__.py"]
    mine = [f"{pkg}/{n}" for n in names]
    mine += ["tests/test_tasks.py", "CLAUDE.md"]
    templates = [".claude/family.md", "tests/conftest.py", f"{pkg}/mcp.py"]
    for rel in [*mine, *templates]:
        (dst / rel).write_text("# edited\n")
    generate(template_src, dst, source_slug="ex-api", **keyed(""))
    for rel in mine:
        assert (dst / rel).read_text() == "# edited\n", f"{rel} is the source's"
    for rel in templates:
        assert (dst / rel).read_text() != "# edited\n", f"{rel} is the template's"


def test_the_files_a_source_fills_are_one_list(template_src: Path, tmp_path: Path) -> None:
    """The family rules and /adopt-release name every protected path, in skip order."""
    patterns = yaml.safe_load((template_src / "copier.yml").read_text())["_skip_if_exists"]
    names = [
        f"`{p.removeprefix('src/xippios/{{ package_dir }}/').replace('/**', '/')}`"
        for p in patterns
    ]
    listing = ", ".join(names[:-1]) + f" and {names[-1]}"
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    assert names[-1] == "`CLAUDE.md`", "the facts are the source's"
    for rel in [".claude/family.md", ".claude/commands/adopt-release.md"]:
        assert listing in " ".join((dst / rel).read_text().split()), rel


def test_errors_module_and_classify_hook_are_scaffolded(generated: tuple[str, Path]) -> None:
    """A source's own error classes (conventions §5) and the classify hook (§6), both empty."""
    name, dst = generated
    pkg = dst / "src/xippios" / package_dir(VARIANTS[name])
    errors = (pkg / "errors.py").read_text()
    assert "conventions §5" in errors.splitlines()[0]
    assert "# class UnknownFilter(InvalidRequestError):" in errors, "a commented pattern"
    assert errors.endswith("\n__all__: list[str] = []\n")
    client = (pkg / "_client.py").read_text()
    assert "def classify(response: httpx.Response) -> XippiosError | None:" in client
    assert "``ClientConfig.classify`` hook" in client
    assert "    return None\n" in client
    assert "    classify=classify,\n" in client, "wired into the config"


def test_a_long_source_name_passes_ruff(template_src: Path, tmp_path: Path) -> None:
    """The four docstrings that once put the name into their summary line pass ruff with a
    64-character name, rendered and checked as the proof does."""
    answers = VARIANTS["long-name"]
    assert len(str(answers["source_name"])) >= 64
    dst = generate(template_src, tmp_path / "repo", **answers)
    pkg = f"src/xippios/{package_dir(answers)}"
    files = [f"{pkg}/{name}" for name in ["__init__.py", "_client.py", "models.py", "params.py"]]
    check = ruff(dst, "check", *files)
    assert check.returncode == 0, check.stdout + check.stderr


def test_tool_prefix_is_the_underscored_slug_everywhere(generated: tuple[str, Path]) -> None:
    """The MCP tool prefix is the slug with underscores, never the dotted import path."""
    name, dst = generated
    slug = str(VARIANTS[name]["source_slug"])
    prefix = slug.replace("-", "_")
    dotted = package_dir(VARIANTS[name]).replace("/", ".")
    for rel in ["README.md", ".claude/commands/add-endpoint.md"]:
        text = (dst / rel).read_text()
        assert f"`{prefix}_" in text, rel
        if "." in dotted:
            assert f"{dotted}_" not in text, rel


CONFTEST = """\
# Core's plugin keeps the default run offline and free of real keys (ADR-0013), runs anyio
# tests on asyncio and serves the family check in tests/test_family.py; a key's variable is
# named under xippios_placeholder_key_envs in pyproject.toml, not here.
pytest_plugins = ["xippios.core.testing.plugin"]
"""
# A keyless source names no key variable, so its conftest points at none (row 61 d).
CONFTEST_KEYLESS = """\
# Core's plugin keeps the default run offline (ADR-0013), runs anyio tests on asyncio and
# serves the family check in tests/test_family.py.
pytest_plugins = ["xippios.core.testing.plugin"]
"""


def test_the_plugin_sends_the_placeholder_unless_live(generated: tuple[str, Path]) -> None:
    """ADR-0013: core's plugin pins the key; a keyed source only names its variable.

    No placeholder fixture, constant or test of the source's own, keyed or open.
    """
    name, dst = generated
    env = str(VARIANTS[name]["api_key_env"])
    assert (dst / "tests/conftest.py").read_text() == (CONFTEST if env else CONFTEST_KEYLESS)
    ini = tomllib.loads((dst / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert ini.get("xippios_placeholder_key_envs") == ([env] if env else None)
    assert "placeholder" not in (dst / "tests/test_tasks.py").read_text()


def test_secret_detection_skips_the_answers_file(generated: tuple[str, Path]) -> None:
    """The hook and a baseline rescan exclude the same files, the answers file among them."""
    _, dst = generated
    baseline = json.loads((dst / ".secrets.baseline").read_text())
    (excluded,) = [
        pattern
        for entry in baseline["filters_used"]
        if entry["path"].endswith(".should_exclude_file")
        for pattern in entry["pattern"]
    ]
    config = yaml.safe_load((dst / ".pre-commit-config.yaml").read_text())
    (hook,) = [h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "detect-secrets"]
    for name in ["uv.lock", ".copier-answers.yml"]:
        assert re.search(excluded, name), name
        assert re.search(hook["exclude"], name), name


def test_upstream_snapshot_is_kept_byte_for_byte(generated: tuple[str, Path]) -> None:
    """Git never converts line endings under docs/upstream/: upstream files may carry CRLF.

    FETCHED.md records a UTC time, the attribution and HTML-kept tables (ADR-0003).
    """
    _, dst = generated
    assert (dst / ".gitattributes").read_text() == "docs/upstream/** -text\n"
    fetched = (dst / "docs/upstream/FETCHED.md").read_text()
    assert f"{TABLE_HEADER}\n" in fetched, "the columns scripts/refresh_upstream.py writes"
    assert "## Attribution" in fetched
    flat = " ".join(fetched.split())
    assert "the publisher's objection" in flat, "a vendor or a public-sector publisher"
    assert "UTC time of the run in ISO 8601 with an explicit `Z`" in fetched
    example = fetched.split("```text\n", 1)[1].split("```", 1)[0].splitlines()
    assert [row.split(" | ")[0] for row in example] == [
        "| openapi/openapi.json",
        "| (no file)",
        "| openapi/part.json",
    ], "a file row, a shell row and an excerpt row"
    assert "Bytes and sha256 are the whole document's" in example[2], "conventions §3"


TABLE_HEADER = "| File | URL | Fetched | HTTP | Bytes | sha256 | ETag | Last-Modified | Note |"


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


def refresh_upstream(template_src: Path, dst: Path) -> ModuleType:
    """The rendered scripts/refresh_upstream.py of a fresh repository, imported, no pause."""
    generate(template_src, dst, source_slug="ex", **keyed(""))
    path = dst / "scripts/refresh_upstream.py"
    spec = importlib.util.spec_from_file_location("refresh_upstream", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PAUSE = 0.0
    return module


def test_refresh_upstream_command_follows_the_skeleton(template_src: Path, tmp_path: Path) -> None:
    """The command names what the skeleton defines: the hooks a source fills, --check, the
    shell and excerpt rows, the spec URL convention (row 67 b) and the one converter a
    capture script may declare (row 70); the skeleton itself declares no dependency."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    command = " ".join((dst / ".claude/commands/refresh-upstream.md").read_text().split())
    script = (dst / "scripts/refresh_upstream.py").read_text()
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
    template_src: Path, tmp_path: Path, site: tuple[Path, str]
) -> None:
    """Rows 35 c and 67 c: the skeleton fetches through its one fetch function, writes a
    file row and a shell row, and ``--check`` compares without writing (here against pages
    served on the loopback interface)."""
    root, base = site
    (root / "openapi.json").write_text('{"openapi": "3.1.0"}\n')
    module = refresh_upstream(template_src, tmp_path / "repo")
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
    template_src: Path, tmp_path: Path, site: tuple[Path, str]
) -> None:
    """Row 35 b: every run checks the attribution, and stops before writing on a copyright,
    licence or terms that ATTRIBUTION does not record; a recorded one passes."""
    root, base = site
    (root / "guide.html").write_text("<p>Guide</p><footer>&copy; 2026 Example Ltd.</footer>\n")
    module = refresh_upstream(template_src, tmp_path / "repo")
    out = tmp_path / "repo/docs/upstream"
    stub = (out / "FETCHED.md").read_bytes()
    module.PAGES = (module.Page(f"{base}/guide.html", "pages/guide.html"),)
    with pytest.raises(SystemExit, match="ATTRIBUTION does not record"):
        module.main(["--out", str(out)])
    assert (out / "FETCHED.md").read_bytes() == stub, "nothing written"
    module.ATTRIBUTION = ("\N{COPYRIGHT SIGN} 2026 Example Ltd.",)
    assert module.main(["--out", str(out)]) == 0
    assert "The documentation states `\N{COPYRIGHT SIGN} 2026" in (out / "FETCHED.md").read_text()


def test_models_use_validation_alias(generated: tuple[str, Path]) -> None:
    """Adapters serialise by alias: a plain alias would hand agents the upstream spelling.

    The commands also carry ADR-0017's rule on personal identifiers.
    """
    name, dst = generated
    plain_alias = re.compile(r"Field\((?:[^)]*[\s,])?alias=")
    for path in dst.rglob("*.py"):
        assert not plain_alias.search(path.read_text()), path
    add_endpoint = (dst / ".claude/commands/add-endpoint.md").read_text()
    assert "`Field(validation_alias=...)`" in add_endpoint
    models = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/models.py").read_text()
    assert "``/add-endpoint`` give the rules" in models, "the scaffold points at them"
    for command in ["add-endpoint", "record-fixture"]:
        assert "ADR-0017" in (dst / f".claude/commands/{command}.md").read_text(), command


def test_list_tools_are_not_promised(generated: tuple[str, Path]) -> None:
    """A new repository has no list_<thing> tool yet; the wording must hold either way."""
    name, dst = generated
    prefix = str(VARIANTS[name]["source_slug"]).replace("-", "_")
    mcp = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/mcp.py").read_text()
    assert "Call the list tools first" not in mcp
    assert f"Where list tools ({prefix}_list_*) exist" in mcp
    assert "to find valid values, then query" in mcp, "codes, releases or agencies alike"


def test_servers_take_the_caps_kept_with_the_tasks(template_src: Path, tmp_path: Path) -> None:
    """ADR-0016: per-tool caps live next to the tasks as MCP_CAPS; the server reads them."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex")
    pkg = dst / "src/xippios/ex"
    assert 'caps=getattr(tasks, "MCP_CAPS", None),' in (pkg / "mcp.py").read_text()
    tasks = (pkg / "tasks.py").read_text()
    assert "# MCP_CAPS = {" in tasks, "a commented scaffold"
    assert "# from xippios.core import ResultCap" in tasks, "core 0.3.0 exports it"


def test_local_env_files_are_ignored(generated: tuple[str, Path]) -> None:
    """Belt and braces: no variant of a local env file is ever committed."""
    _, dst = generated
    ignored = set((dst / ".gitignore").read_text().splitlines())
    assert {".env", ".env.*", ".envrc", ".envrc.*"} <= ignored


def test_rate_limit_renders_pace_burst_and_provenance(generated: tuple[str, Path]) -> None:
    """ADR-0010 decision 1: the pace, a burst of 1 unless upstream documents one, and where
    the pace comes from, in the client and in the contract; a quota's policy commented."""
    name, dst = generated
    answers = {**BASE_ANSWERS, **VARIANTS[name]}
    burst = answers.get("rate_limit_burst", 1)
    client = (dst / f"src/xippios/{package_dir(answers)}/_client.py").read_text()
    pace = f"RATE_LIMIT = RateLimit(per_minute={answers['rate_limit_per_minute']}, burst={burst})"
    assert pace in client
    claude = (dst / "CLAUDE.md").read_text()
    family = (dst / ".claude/family.md").read_text()
    row = f"| Rate limit | {answers['rate_limit_per_minute']} requests per minute, burst {burst}; "
    assert row in claude
    assert "# config = policy.install(config)" in client, "ADR-0015, a commented scaffold"
    assert "one `QuotaPolicy` installed on `config`" in " ".join(family.split())
    if answers.get("rate_limit_provenance") == "self-imposed":
        own = "self-imposed pace: upstream documents no per-second or per-minute limit"
        assert f"# A {own} (ADR-0010 decision 1)." in client, "a daily quota may exist"
        assert f"a {own} (ADR-0010)" in claude
    else:
        assert "# Paced within the limit upstream documents" in client
        assert "within the limit documented by upstream (ADR-0010)" in claude


def test_client_exports_one_sorted_name_per_line(generated: tuple[str, Path]) -> None:
    """One name per line, so a source's extra export never conflicts on copier update."""
    name, dst = generated
    client = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/_client.py").read_text()
    (node,) = [
        node
        for node in ast.parse(client).body
        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "__all__"
    ]
    assert isinstance(node.value, ast.List)
    names = [str(ast.literal_eval(element)) for element in node.value.elts]
    upper = [n for n in names if n.isupper()]
    assert names == sorted(upper) + sorted(set(names) - set(upper)), "isort-style, as RUF022"
    lines = client.splitlines()
    start = lines.index("__all__ = [")
    assert lines[start + 1 : start + 1 + len(names)] == [f'    "{n}",' for n in names]
    assert lines[start + 1 + len(names)] == "]"


def detect_secrets_hook(directory: Path, *files: str) -> subprocess.CompletedProcess[str]:
    """The generated repository's detect-secrets hook, on ``files`` in ``directory``."""
    hook = [sys.executable, "-m", "detect_secrets.pre_commit_hook"]
    return subprocess.run(
        [*hook, "--baseline", ".secrets.baseline", *files],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )


def test_core_dependency_is_one_minor(generated: tuple[str, Path], tmp_path: Path) -> None:
    """Conventions §12: one core minor, the extras likewise; a git pin keeps the bound.

    uv takes a pinned core from ``[tool.uv.sources]`` and does not check the bound against
    it, so the bound stays ``~=``; the pin's ``rev`` line is allowlisted for detect-secrets,
    which a 40-character commit SHA trips without the pragma.
    """
    name, dst = generated
    answers = VARIANTS[name]
    version = str(answers.get("core_version", "0.2.1"))
    pyproject = (dst / "pyproject.toml").read_text()
    project = tomllib.loads(pyproject)["project"]
    assert project["dependencies"] == [f"xippios-core~={version}"]
    assert project["optional-dependencies"] == {
        extra: [f"xippios-core[{extra}]~={version}"] for extra in ["mcp", "http", "testing"]
    }
    assert ">=0.1.0" not in pyproject
    if answers.get("core_git_ref"):
        (rev,) = [line for line in pyproject.splitlines() if line.startswith("xippios-core = {")]
        assert f'rev = "{answers["core_git_ref"]}" }}' in rev
        assert "# pragma: allowlist secret" in rev
        assert "until it is on PyPI" not in pyproject
        assert "uvx copier update --defaults --vcs-ref=:current: -d core_git_ref=" in pyproject
        assert "X.Y.Z with Z the patch that shipped it, or X.Y.0 when the minor" in pyproject
        if len(str(answers["core_git_ref"])) == 40:
            shutil.copy(dst / ".secrets.baseline", tmp_path / ".secrets.baseline")
            (tmp_path / "pyproject.toml").write_text(pyproject)
            (tmp_path / "unmarked.toml").write_text(
                pyproject.replace(rev, rev.split("  # pragma")[0])
            )
            hook = detect_secrets_hook(tmp_path, "pyproject.toml")
            assert hook.returncode == 0, hook.stdout + hook.stderr
            control = detect_secrets_hook(tmp_path, "unmarked.toml")
            assert control.returncode == 1, "without the pragma the SHA must be flagged"
            assert "Hex High Entropy String" in control.stdout, control.stdout


# SHA-256 of sdk-core's files at v0.2.1, which the template copies verbatim, taken at
# core's `feature/release-train-and-family-tests` head 4aa24b8; re-verified against the
# v0.2.1 tag at gate 4b: git -C ../sdk-core show <ref>:<path> | sha256sum (digests, not
# secrets). gates.yml's is core's `.github/workflows/gates.yml` from after v0.2.1 (the
# gates repository renamed to `xippios/sdk-gates`, 2026-10-27), pinned by digest;
# re-verify against core `main` once that change merges.
CORE_VERBATIM = {
    ".github/workflows/gates.yml": (
        # pragma: allowlist nextline secret
        "cf3097a2a34f40b98d4e511435204fdb07a7edf8aed94bcf5de467bbb0b814c5"
    ),
    ".github/PULL_REQUEST_TEMPLATE.md": (
        # pragma: allowlist nextline secret
        "657a5d0e61d1c1e7a3e47f3a0ee53acef7ade9f6e452b193a4d0fa92d7eb3d22"
    ),
}
# The same for the two workflows the template extends: core's bytes once the template's
# own lines, named in CLAUDE.md's Rules, are taken out.
CORE_EXTENDED = {
    # pragma: allowlist nextline secret
    ".github/workflows/ci.yml": "ebee09e20d7004a6761c1986f3bc0e16ee4a2dfa749921ac25040ebad5abacab",
    ".github/workflows/publish.yml": (
        # pragma: allowlist nextline secret
        "bf846b59d1c832d8873ad56b3edb339c4d2fbe5fbafd428075ef1df922feb6ba"
    ),
}
# The template's own lines: in ci.yml the full history for the two steps that read the
# pull request (core's docs/handover.md, "Template v0.2.1"), in publish.yml the refusal
# of a git-pinned core before the tag.
FETCH_DEPTH = "          fetch-depth: 0 # both steps below diff against origin/<base>\n"
CI_STEPS = ("      # Conventions §12: every PR but a release", "      - uses: astral-sh/setup-uv@")
PUBLISH_STEP = (
    "      # sdk-template's one step beyond core's file",
    "      - name: Tag the merge commit",
)


def without(text: str, first: str, stop: str) -> str:
    """``text`` without the lines from the one starting ``first`` up to ``stop``."""
    start = text.index(first)
    return text[:start] + text[text.index(stop, start) :]


def test_workflows_and_pr_template_are_core_v0_2_1(template_src: Path, tmp_path: Path) -> None:
    """The verbatim files are core's bytes; ci.yml and publish.yml core's plus ours."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    for rel, digest in CORE_VERBATIM.items():
        assert hashlib.sha256((dst / rel).read_bytes()).hexdigest() == digest, rel
    ci = (dst / ".github/workflows/ci.yml").read_text()
    assert ci.count(FETCH_DEPTH) == 1
    core_ci = without(ci.replace(FETCH_DEPTH, ""), *CI_STEPS)
    publish = (dst / ".github/workflows/publish.yml").read_text()
    core_publish = without(publish, *PUBLISH_STEP)
    for rel, core in [
        (".github/workflows/ci.yml", core_ci),
        (".github/workflows/publish.yml", core_publish),
    ]:
        assert hashlib.sha256(core.encode()).hexdigest() == CORE_EXTENDED[rel], rel


def test_the_templates_own_gates_caller_is_the_one_it_ships() -> None:
    """sdk-template carries core's gates.yml as every repository does, off until GATES_CALLER."""
    own = (ROOT / ".github/workflows/gates.yml").read_bytes()
    assert own == (ROOT / "template/.github/workflows/gates.yml").read_bytes()
    assert hashlib.sha256(own).hexdigest() == CORE_VERBATIM[".github/workflows/gates.yml"]


def steps_of(workflow: dict[str, object], job: str) -> list[dict[str, object]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    steps = jobs[job]["steps"]
    assert isinstance(steps, list)
    return steps


def test_ci_reads_the_pull_request_and_runs_once_on_main(generated: tuple[str, Path]) -> None:
    """No push trigger (publish.yml calls it for a release); the two family CI steps."""
    _, dst = generated
    workflow = yaml.safe_load((dst / ".github/workflows/ci.yml").read_text())
    assert set(workflow[True]) == {"pull_request", "workflow_call"}, "conventions §12"
    steps = steps_of(workflow, "test")
    assert steps[0]["with"] == {"fetch-depth": 0, "persist-credentials": False}
    changelog, cap = steps[1], steps[2]
    assert changelog["name"] == "CHANGELOG.md has an entry"
    for prefix in ["chore/release-", "dependabot/"]:
        assert f"!startsWith(github.head_ref, '{prefix}')" in changelog["if"], prefix
    assert "chore/template-update" not in changelog["if"], "conventions §15 item 9"
    rules = " ".join((dst / ".claude/family.md").read_text().split())
    assert "Every PR but a release or Dependabot's adds an entry" in rules, "as ci.yml checks"
    assert cap["name"] == "Fixture files under 256 KiB"
    assert cap["env"]["LEVEL"] == "warning", "an error from template v0.3.0 (ADR-0019)"
    assert "--no-renames --diff-filter=AM" in cap["run"]
    assert "262144" in cap["run"]


def workflow_uses(path: Path) -> list[tuple[str, str]]:
    """Each ``uses:`` of a workflow: the action and what follows it on the line."""
    return re.findall(r"^\s+(?:- )?uses: (\S+)(.*)$", path.read_text(), re.MULTILINE)


def test_workflow_actions_are_pinned_by_sha(generated: tuple[str, Path]) -> None:
    """ci.yml, publish.yml, live.yml and, where rendered, siblings.yml pin every action to a
    commit, its version in a comment (conventions §13); live.yml and siblings.yml take
    ci.yml's pins."""
    _, dst = generated
    workflows = dst / ".github/workflows"
    rendered = sorted(path.name for path in workflows.glob("*.yml"))
    assert rendered in [CORE_WORKFLOWS, sorted([*CORE_WORKFLOWS, "siblings.yml"])]
    for rel in rendered:
        if rel == "gates.yml":
            continue  # core's bytes, calling the gates at @main by design (conventions §13)
        uses = workflow_uses(workflows / rel)
        assert uses, rel
        for action, comment in uses:
            if action.startswith("./"):
                continue
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"{rel}: {action}"
            assert re.fullmatch(r" # v\d+(\.\d+)*", comment), f"{rel}: {action}{comment}"
    for rel in set(rendered) & {"live.yml", "siblings.yml"}:
        assert set(workflow_uses(workflows / rel)) <= set(workflow_uses(workflows / "ci.yml"))


CORE_WORKFLOWS = ["ci.yml", "gates.yml", "live.yml", "publish.yml"]


def skip_matcher(pkg: str) -> Callable[[str], bool]:
    """Whether copier's ``_skip_if_exists`` protects a path, matched as copier 9.19.1 does:
    the patterns rendered, read as gitignore lines by pathspec."""
    patterns = yaml.safe_load((ROOT / "copier.yml").read_text())["_skip_if_exists"]
    rendered = [pattern.replace("{{ package_dir }}", pkg) for pattern in patterns]
    return PathSpec.from_lines("gitignore", rendered).match_file


SIBLINGS_SCRIPT = ROOT / "template/.github/{% if '.' in import_path %}scripts{% endif %}"


def test_siblings_check_renders_where_the_import_path_nests(generated: tuple[str, Path]) -> None:
    """ADR-0006's sibling proof is the template's (T10): siblings.yml and the script it runs
    render, byte for byte and executable, only where the import path nests, outside the
    skip-listed scripts/ so that a source's copy is trusted when identical to the render;
    a visible job, `ci` never aggregates it (ci.yml stays core's)."""
    name, dst = generated
    nested = "/" in package_dir(VARIANTS[name])
    workflow = dst / ".github/workflows/siblings.yml"
    script = dst / ".github/scripts/check-siblings.sh"
    assert workflow.is_file() is nested
    assert (dst / ".github/scripts").exists() is nested, "no empty directory where flat"
    assert not (dst / "scripts/check-siblings.sh").exists()
    claude = (dst / "CLAUDE.md").read_text()
    assert ("siblings.yml" in claude) is nested
    if not nested:
        return
    assert script.read_bytes() == (SIBLINGS_SCRIPT / "check-siblings.sh").read_bytes()
    assert script.stat().st_mode & 0o111, "executable, as the render the merge classes compare"
    syntax = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert syntax.returncode == 0, syntax.stderr
    lines = script.read_text().splitlines()
    first_uv = min(n for n, line in enumerate(lines) if line.lstrip().startswith("uv "))
    assert lines.index("unset GITHUB_TOKEN") < first_uv, "conventions §13"
    (handed,) = [line for line in lines if '"$token"' in line]
    assert handed.startswith('  siblings="$(GITHUB_TOKEN="$token" "$python" - '), "listing only"
    # D87: a sibling on another core minor is told by resolved versions, never by the text
    # of uv's error; prove.sh runs both outcomes, since each needs PyPI.
    assert not [line for line in lines if "$trial" in line and "grep" in line]
    assert "uv pip compile --quiet --no-header --no-annotate" in script.read_text()
    skipped = skip_matcher(package_dir(VARIANTS[name]))
    assert skipped("scripts/check-siblings.sh"), "why the script is not under scripts/"
    for rel in [".github/workflows/siblings.yml", ".github/scripts/check-siblings.sh"]:
        assert not skipped(rel), f"{rel}: the template's, trusted when identical to the render"
    text = workflow.read_text()
    assert "{{" not in text.replace("${{", ""), "copied verbatim: only its name is rendered"
    parsed = yaml.safe_load(text)
    assert parsed[True] == {"push": {"branches": ["main"]}, "pull_request": None}
    assert parsed["permissions"] == {"contents": "read"}
    (job,) = parsed["jobs"].values()
    assert job["name"] == "siblings"
    checkout, setup, run = job["steps"]
    assert checkout["with"] == {"persist-credentials": False}, "conventions §13"
    assert setup["uses"].startswith("astral-sh/setup-uv@")
    assert run["run"] == ".github/scripts/check-siblings.sh"
    assert run["env"] == {"GITHUB_TOKEN": "${{ github.token }}"}, "the job's read-only token"
    assert "secrets." not in text
    ci = yaml.safe_load((dst / ".github/workflows/ci.yml").read_text())
    assert "siblings" not in json.dumps(ci), "ci.yml stays core's file (row 34 c)"


def test_the_templates_own_workflows_are_hardened() -> None:
    """Conventions §13 for this repository's own workflows too: SHA pins with the version
    in a comment (the gates at ``@main`` by design), ``contents: read`` at the top, and no
    checkout keeps its credentials but the one in a job that pushes, which says so."""
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for action, comment in workflow_uses(path):
            if action.startswith("xippios/sdk-gates/") and action.endswith("@main"):
                continue
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"{path.name}: {action}"
            assert re.fullmatch(r" # v\d+(\.\d+)*", comment), f"{path.name}: {action}{comment}"
        text = path.read_text()
        workflow = yaml.safe_load(text)
        assert workflow["permissions"] == {"contents": "read"}, path.name
        for name, job in workflow["jobs"].items():
            steps = job.get("steps", [])
            pushes = any("git push" in step.get("run", "") for step in steps)
            for step in steps:
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    kept = step.get("with", {}).get("persist-credentials", True)
                    assert kept is pushes, f"{path.name}: {name}"
            if pushes:
                assert "The one checkout that keeps its credentials" in text, path.name


def test_publish_is_the_release_train(generated: tuple[str, Path]) -> None:
    """Conventions §12: every push to main; a release tags itself; no concurrency group.

    A release cannot carry a git-pinned core: the tag job refuses it before the tag, so no
    tag is left without a release.
    """
    name, dst = generated
    workflow = yaml.safe_load((dst / ".github/workflows/publish.yml").read_text())
    assert workflow[True] == {"push": {"branches": ["main"]}, "workflow_dispatch": None}
    assert "concurrency" not in workflow, "a pending release run would be cancelled"
    assert list(workflow["jobs"]) == ["release-check", "ci", "tag", "build", "publish"]
    assert workflow["jobs"]["ci"]["uses"] == "./.github/workflows/ci.yml"
    assert workflow["jobs"]["publish"]["environment"] == "pypi"
    check = steps_of(workflow, "release-check")[-1]["run"]
    assert "grep -qx 'CHANGELOG.md'" in check, "a first release changes only the CHANGELOG"
    tag = steps_of(workflow, "tag")
    names = [step.get("name") or step.get("uses") for step in tag]
    guard = names.index("Refuse a pyproject with [tool.uv.sources]")
    assert names[guard + 1] == "Tag the merge commit with its CHANGELOG section"
    assert "[tool\\.uv\\.sources\\]" in tag[guard]["run"]
    release_prep = (dst / ".claude/commands/release-prep.md").read_text()
    assert "-d core_git_ref= -d core_version=X.Y.Z" in release_prep
    assert "`X.Y.Z` with `Z` the patch that shipped it, or `X.Y.0`" in release_prep
    assert release_prep.index("No git-pinned core") < release_prep.index("set `version`")
    flat = " ".join(release_prep.split())
    subset = (
        "`pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `README.md`, `CLAUDE.md` and "
        "`docs/handover.md`"
    )
    assert subset in flat, "the release subset of conventions §12"
    assert "`/refresh-reference-data`, merged before this one" in flat, "its own PR first"
    assert "if the `merge-class` check says `auto`" in flat, "ADR-0018, amendment (e)"
    slug = VARIANTS[name]["source_slug"]
    assert f"gh pr merge --auto --squash -R xippios/sdk-{slug} <number>" in release_prep


def test_adopt_release_walks_the_adoption_checklist(template_src: Path, tmp_path: Path) -> None:
    """Conventions §15, ADR-0018: the nine items in order, one chore/template-update PR."""
    items = ["Items 1 and 2", "Items 3 and 4", *(f"Item {n}:" for n in range(5, 10))]
    update = "uvx copier update --defaults --vcs-ref=<tag> -d core_version=X.Y.Z -d core_git_ref="
    keyed_line = "`xippios_placeholder_key_envs` under `[tool.pytest.ini_options]` names"
    for env in ["EX_API_KEY", ""]:
        dst = generate(template_src, tmp_path / (env or "open"), source_slug="ex", **keyed(env))
        text = (dst / ".claude/commands/adopt-release.md").read_text()
        positions = [text.index(item) for item in items]
        assert positions == sorted(positions)
        assert update in text
        moved = text.index("First move the tests of the\n   source's own out of every file")
        assert moved < text.index(update), "the update deletes a removed file, no marker"
        assert "`git show HEAD:tests/test_adapters.py` brings its tests back" in text
        assert "`chore/template-update-<tag>`" in text
        assert (keyed_line in text) is bool(env), "the ini option, for a keyed source only"
        assert "gh pr merge --auto --squash -R xippios/sdk-ex <number>" in text, "from the root"
        github = "`https://github.com/xippios/sdk-template/blob/<tag>/CHANGELOG.md` (or"
        local = "git -C <workspace root>/sdk-template"
        assert text.index(github) < text.index(local), "GitHub first, the local clone named"
        flat = " ".join(text.split())
        assert "(`~=0.2.1` for template v0.2.1)" in flat, "the patch case, ADR-0018 amendment c"
        assert "a third never: core takes it in that minor (ADR-0023)" in flat, "§15 item 4"
        assert "`docs/upstream/FETCHED.md`, left to the next `/refresh-upstream`" in flat
        assert "nothing more (ADR-0018, amendment (d))" in flat, "dead fixtures may go"
        assert "sdk-template v0.2.1 and conventions 1.15" in flat
        assert "if the `merge-class` check says `auto`" in flat, "ADR-0018, amendment (e)"


def test_reference_data_has_both_enum_paths(template_src: Path, tmp_path: Path) -> None:
    """ADR-0008 amendment: StrEnum for value lists, IntEnum for integer ids, as rendered;
    ``--render-only`` re-renders them from the packaged files, as an adoption does."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    script = (dst / "scripts/refresh_reference.py").read_text()
    for call in ["render_str_enums(values,", "id_name_pairs(records,", "render_int_enums(pairs,"]:
        assert call in script, call
    command = (dst / ".claude/commands/refresh-reference-data.md").read_text()
    assert "ruff format" not in command, "core 0.2.0 renders enums.py ruff-clean"
    assert "records = [upstream_record(record) for record in" in script, "upstream's names"
    render_only = "uv run python scripts/refresh_reference.py --render-only"
    assert '"--render-only",' in script
    assert render_only in command
    assert render_only in (dst / ".claude/commands/adopt-release.md").read_text(), "§15 item 6"
    enums = (dst / "src/xippios/ex/enums.py").read_text()
    assert enums.startswith('"""StrEnums for packaged value lists (conventions, section 3).')


def test_live_workflow_hands_the_key_to_its_pytest_step(generated: tuple[str, Path]) -> None:
    """Conventions §10: nightly and on demand; the secret in the pytest step's env only."""
    name, dst = generated
    answers = VARIANTS[name]
    env_var = str(answers["api_key_env"])
    text = (dst / ".github/workflows/live.yml").read_text()
    workflow = yaml.safe_load(text)
    triggers = workflow[True]  # YAML 1.1 reads the key `on` as a boolean
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert "env" not in workflow, "the secret reaches the pytest step only"
    (job,) = workflow["jobs"].values()
    assert "env" not in job, "the secret reaches the pytest step only"
    *setup, pytest_step = job["steps"]
    assert pytest_step["run"] == "uv run pytest -m live --tb=short", "every live test"
    assert all("env" not in step for step in setup), "checkout and uv sync never see it"
    checkout = setup[0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {"persist-credentials": False}, "conventions §13"
    expected_env: dict[str, str] = {"XIPPIOS_LIVE_TESTS": "1"}
    if env_var:
        expected_env[env_var] = f"${{{{ secrets.{env_var} }}}}"
        assert text.count(f"${{{{ secrets.{env_var} }}}}") == 1
        assert text.count("secrets.") == 1
    else:
        assert "secrets." not in text
    assert pytest_step["env"] == expected_env
    for reason in ["the secret it names", "so that sources sharing a key do not start"]:
        assert (reason in " ".join(text.split())) is bool(env_var), f"keyed only: {reason}"
    claude = (dst / "CLAUDE.md").read_text()
    if env_var:
        step = "Only its `uv run pytest -m live --tb=short` step sees the key"
        assert f"{step}, from the org secret `{env_var}`." in claude
    else:
        assert "The API needs no key, so the workflow uses no secret." in claude


def test_every_live_run_keeps_payloads_out_of_tracebacks(generated: tuple[str, Path]) -> None:
    """Row 42: every live command, run or documented, takes ``--tb=short``; a live test
    asserts on shapes and counts, since assertion introspection prints what it compares."""
    _, dst = generated
    runs = 0
    for path in sorted(dst.rglob("*")):
        if path.is_file() and path.suffix in {".md", ".yml", ".toml", ".py"}:
            text = path.read_text()
            assert not re.search(r"pytest -m live(?! --tb=short)", text), path
            runs += text.count("pytest -m live --tb=short")
    assert runs >= 4, "live.yml, CLAUDE.md, .claude/family.md and /release-prep"
    rules = " ".join((dst / ".claude/family.md").read_text().split())
    assert "pytest's assertion introspection still prints the values an `assert`" in rules
    assert "a live test asserts on shapes and counts, never on a raw payload" in rules


def live_start(dst: Path) -> tuple[int, int]:
    """(hour, minute) of the nightly live run, checked against its cron and the CLAUDE.md."""
    workflow = yaml.safe_load((dst / ".github/workflows/live.yml").read_text())
    (schedule,) = workflow[True]["schedule"]
    match = re.fullmatch(r"(\d{1,2}) (\d) \* \* \*", schedule["cron"])
    assert match, schedule["cron"]
    minute, hour = int(match[1]), int(match[2])
    assert 0 <= minute <= 59, schedule["cron"]
    assert 1 <= hour <= 5, f"{schedule['cron']}: inside the night window, 01:00 to 05:59 UTC"
    assert f"nightly at {hour:02d}:{minute:02d} UTC" in (dst / "CLAUDE.md").read_text()
    return hour, minute


def test_live_workflow_runs_inside_the_night_window(generated: tuple[str, Path]) -> None:
    _, dst = generated
    live_start(dst)


def test_sources_sharing_a_key_start_at_stable_different_times(
    template_src: Path, tmp_path: Path
) -> None:
    """ADR-0009: usda-psd, usda-esr and usda-gats share one key and one gateway quota; their
    nightly runs never start together, and a render keeps a repository's time."""
    shared = keyed("DATA_GOV_API_KEY", "query", "api_key")
    starts = {
        slug: live_start(generate(template_src, tmp_path / slug, source_slug=slug, **shared))
        for slug in ["usda-psd", "usda-esr", "usda-gats"]
    }
    assert len(set(starts.values())) == 3, starts
    again = generate(template_src, tmp_path / "again", source_slug="usda-psd", **shared)
    assert live_start(again) == starts["usda-psd"], "stable across renders"


def test_generated_tests_need_no_key(generated: tuple[str, Path]) -> None:
    """The reachability probe sends no key."""
    name, dst = generated
    live = (dst / "tests/test_live.py").read_text()
    flat = " ".join(live.split())
    assert ("it spends no keyed call" in flat) is bool(VARIANTS[name]["api_key_env"])
    assert "quota" not in live, "a keyed source need not have a quota"
    assert "httpx.AsyncClient(" in live
    assert "await http.get(BASE_URL)" in live
    assert "follow_redirects=True" in live
    assert "client.request" not in live, "the package's client would send the key"


def test_documents_promise_what_the_code_does(generated: tuple[str, Path]) -> None:
    """The http docstring states ADR-0007; the CLAUDE.md names every namespace level, the
    family rules forbid an ``__init__.py`` at any of them."""
    name, dst = generated
    pkg = package_dir(VARIANTS[name])
    http = (dst / f"src/xippios/{pkg}/http.py").read_text()
    assert "is a ``GET`` with query parameters" in http
    assert "is a ``POST`` whose JSON body is keyed by parameter name (ADR-0007)" in http
    claude = (dst / "CLAUDE.md").read_text()
    family = (dst / ".claude/family.md").read_text()
    flat = " ".join(claude.split())
    if "/" in pkg:
        provider = pkg.rsplit("/", 1)[0]
        assert f"and so is `src/xippios/{provider}/`, the provider level" in flat
    else:
        assert "the provider level" not in claude
    assert f"The import path is `xippios.{pkg.replace('/', '.')}` (ADR-0006)" in flat
    never = "nor an `__init__.py` at a level between it and the package (the provider level"
    assert never in " ".join(family.split()), "every namespace level, in every source"
    assert ".github/workflows/live.yml" in claude
    assert "Hand-apply" in family
    assert "`/adopt-release <tag>` walks it" in family, "conventions §15, ADR-0018"
    assert "`tests/conftest.py` and `tests/test_family.py` among them" in " ".join(family.split())
    keyed_source = bool(VARIANTS[name]["api_key_env"])
    assert ("xippios_placeholder_key_envs" in claude) is keyed_source
    assert ("(base URL, key, rate limit)" in claude) is keyed_source, "a key only if there is one"
    stagger = "so that sources sharing a key never start together"
    assert (stagger in flat) is keyed_source, "the start time's reason, keyed sources only"
    assert "PACKAGED_LISTS" not in claude, "the Layout names the lists generically"
    # A block tag that ends a line eats its newline (trim_blocks); these blank lines stay.
    assert "\n\nuv run xippios-" in claude, "a blank line between the two commands"
    record = (dst / ".claude/commands/record-fixture.md").read_text()
    assert "\n\n2. Find the request path" in record
    assert "xippios_placeholder_key_envs" not in family, "the same file for every source"
    rules = " ".join(family.split())
    assert "or one per service where operation ids repeat across services" in rules
    assert "lives there too, unexported, since `enums.py` is generated whole" in rules
    assert "may gain a lead paragraph" in rules, "the released section is the tag's message"
    assert "a write task" not in rules, "the template renders read-only packages"
    assert "(ADR-0017)" in family
    assert "| Write tools | no, this package is read-only |" in claude, "conventions §8"


# Claude Code imports a line `@<path>` relative to the importing file, never one inside
# backticks or a code block, and cuts a file that loads on demand at 40,000 characters.
FAMILY_RULES = ROOT / "template/.claude/family.md.jinja"
IMPORT_LINE = "@.claude/family.md"
SDK_CORE_DOCS = "https://github.com/xippios/sdk-core/blob/main/docs/"


def test_claude_md_imports_the_family_rules(generated: tuple[str, Path]) -> None:
    """The source's CLAUDE.md holds its facts and imports the family rules on the line after
    its intro; the family rules hold no Jinja, so they render the same in every source."""
    _, dst = generated
    claude = (dst / "CLAUDE.md").read_text()
    family = (dst / ".claude/family.md").read_text()
    title, intro, first = claude.split("\n\n")[:3]
    assert title.startswith("# sdk-"), title
    assert intro.startswith("`xippios-"), intro
    assert first == IMPORT_LINE, "the import on a line of its own, first after the intro"
    assert [line for line in claude.splitlines() if line.startswith("@")] == [IMPORT_LINE]
    assert family == FAMILY_RULES.read_text(), "no Jinja: identical in every source"
    assert not [line for line in family.splitlines() if line.startswith("@")], "no import"
    for doc in ["conventions.md", "definition-of-done.md", "review-checklist.md"]:
        assert SDK_CORE_DOCS + doc in family, doc
    assert "https://github.com/xippios/sdk-core/tree/main/docs/adr" in family
    for text in [claude, family]:
        assert "../" not in text, "a relative path leaves the repository (worktree, GitHub)"
        assert len(text) < 40_000, "Claude Code cuts a file that loads on demand"


def test_every_command_points_at_the_process(template_src: Path, tmp_path: Path) -> None:
    """The definition of done and the review checklist, by URL, instead of repeated text."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    commands = sorted((dst / ".claude/commands").glob("*.md"))
    assert len(commands) == 6
    for path in commands:
        flat = " ".join(path.read_text().split())
        for doc in ["definition-of-done.md", "review-checklist.md"]:
            assert SDK_CORE_DOCS + doc in flat, f"{path.name}: {doc}"
        assert "../" not in flat, f"{path.name}: a relative path leaves a worktree"


def test_generated_tree_names_no_source_and_no_workspace_file(generated: tuple[str, Path]) -> None:
    """Nothing source-specific is scaffolded (ADR-0008), nor a workspace-local reference."""
    _, dst = generated
    caches = {".ruff_cache", "__pycache__"}
    for path in dst.rglob("*"):
        if not path.is_file() or path.name == ".copier-answers.yml" or caches & set(path.parts):
            continue
        text = path.read_text()
        for needle in ["commodity_desc", "corn_2024", "api_GET", "row 12", "COORDINATION"]:
            assert needle not in text, f"{path}: {needle}"


def test_generated_baseline_scans_swagger_files(generated: tuple[str, Path]) -> None:
    """sdk-core dropped is_swagger_file: an upstream Swagger snapshot is scanned too."""
    _, dst = generated
    baseline = json.loads((dst / ".secrets.baseline").read_text())
    filters = {entry["path"] for entry in baseline["filters_used"]}
    assert "detect_secrets.filters.heuristic.is_swagger_file" not in filters
    assert baseline["results"] == {}


def test_keyless_flat_render_is_how_eurostat_starts(template_src: Path, tmp_path: Path) -> None:
    """A keyless flat source (eurostat's start on v0.2.1, roadmap §4) names no key anywhere.

    The family check runs on it as on a keyed one: its test file is the same line.
    """
    dst = generate(template_src, tmp_path / "repo", source_slug="eurostat", **keyed(""))
    assert (dst / "src/xippios/eurostat/tasks.py").is_file(), "flat: xippios.eurostat"
    assert not (dst / "src/xippios/__init__.py").exists()
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["api_key_env"] == ""
    assert "api_key_location" not in answers, "not asked without a key"
    assert "api_key_name" not in answers
    pyproject = tomllib.loads((dst / "pyproject.toml").read_text())
    assert "xippios_placeholder_key_envs" not in pyproject["tool"]["pytest"]["ini_options"]
    assert "xippios_package" not in pyproject["tool"]["pytest"]["ini_options"], "one tasks.py"
    assert pyproject["project"]["dependencies"] == ["xippios-core~=0.2.1"]
    assert "secrets." not in (dst / ".github/workflows/live.yml").read_text()
    client = (dst / "src/xippios/eurostat/_client.py").read_text()
    assert "API_KEY_ENV: str | None = None" in client
    assert "Auth" not in client
    assert "No API key is needed." in (dst / "README.md").read_text()
    assert "| Credentials | none; the API is open |" in (dst / "CLAUDE.md").read_text()
    assert (dst / "tests/test_family.py").read_text() == FAMILY_TEST
    for rel in REMOVED_FILES:
        assert not (dst / rel).exists(), rel
    check = ruff(dst, "check", ".")
    assert check.returncode == 0, check.stdout + check.stderr


@pytest.mark.parametrize(
    "ref",
    [
        "v0.2.0",
        "feature/release-train",
        FAKE_CORE_SHA[:7],
        FAKE_CORE_SHA.upper(),
        FAKE_CORE_SHA + "0",
        FAKE_CORE_SHA + "\n",
        "main\n",
        "origin/main",
    ],
)
def test_core_git_ref_is_main_or_a_full_sha(template_src: Path, tmp_path: Path, ref: str) -> None:
    """uv and the merge-class check read main or a full SHA as one commit; nothing else."""
    with pytest.raises(ValueError, match="core_git_ref"):
        generate(template_src, tmp_path / "repo", source_slug="ex", core_git_ref=ref, **keyed(""))


@pytest.mark.parametrize("version", ["0.2", "v0.2.1", "0.2.1rc1", "0.2.1\n"])
def test_core_version_is_a_release_version(
    template_src: Path, tmp_path: Path, version: str
) -> None:
    """A release version, X.Y.Z, and nothing after it: the bound renders it verbatim."""
    with pytest.raises(ValueError, match="core_version"):
        generate(
            template_src, tmp_path / "repo", source_slug="ex", core_version=version, **keyed("")
        )


SOURCE_NAME = "{{ source_name }}"


def test_source_name_is_bounded_by_the_longest_python_line(
    template_src: Path, tmp_path: Path
) -> None:
    """A name at the bound renders ruff-clean (E501 at 100 columns); one more is refused.

    The long-name variant, sdk-usda-esmis's 64-character name, is within it and renders
    ruff-clean with every variant.
    """
    lines = [
        line
        for path in (ROOT / "template").rglob("*.py.jinja")
        for line in path.read_text().splitlines()
        if SOURCE_NAME in line
    ]
    bound = 100 - max(len(line) - len(SOURCE_NAME) for line in lines)
    assert (
        f"at most {bound} characters"
        in yaml.safe_load((ROOT / "copier.yml").read_text())["source_name"]["help"]
    )
    assert len(str(VARIANTS["long-name"]["source_name"])) <= bound
    name = ("Data Service " * 7)[: bound - 1] + "s"
    dst = generate(template_src, tmp_path / "bound", source_slug="ex", source_name=name)
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr
    for refused in ["x" * (bound + 1), 'The "Data" Service', "Data\\Service"]:
        with pytest.raises(ValueError, match="source_name"):
            generate(template_src, tmp_path / "refused", source_slug="ex", source_name=refused)


PR_TEMPLATE = ROOT / "template/.github/PULL_REQUEST_TEMPLATE.md"


def write_body(tmp_path: Path, pr_template: str) -> subprocess.CompletedProcess[str]:
    """new-source.sh's human_steps and write_body, run on a PR template and an answers file."""
    script = (ROOT / "scripts/new-source.sh").read_text()
    start = script.index("human_steps() {")
    functions = script[start : script.index("\n}\n", script.index("write_body() {")) + 3]
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/PULL_REQUEST_TEMPLATE.md").write_text(pr_template)
    (tmp_path / ".copier-answers.yml").write_text("_commit: v0.0.1\nsource_slug: ex\n")
    (tmp_path / "scratch").mkdir()
    harness = (
        "set -euo pipefail\n"
        "slug=ex source_name=Ex ref=v0.0.1 topic=data evidence= api_key_env= dest=/x/sdk-ex\n"
        f"scratch={tmp_path / 'scratch'}\n{functions}\nwrite_body\n"
    )
    return subprocess.run(
        ["bash", "-c", harness], cwd=tmp_path, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("old", "new", "missing"),
    [
        ("", "", ""),
        ("### Enforced by CI", "### Checked by CI", 'unticked items under "### Enforced by CI"'),
        ("### Adoption PR", "### Adoption", 'the "### Adoption PR" block'),
        ("## Assumptions\n\n<!--", "## Assumptions\n\n-", 'a comment line under "## Assumptions"'),
    ],
)
def test_new_source_fills_the_pr_template_or_names_what_it_lacks(
    tmp_path: Path, old: str, new: str, missing: str
) -> None:
    """The scaffold PR's body: the CI block ticked, no Adoption PR block; a PR template of
    another shape stops the script loudly, before anything is created on GitHub."""
    run = write_body(
        tmp_path, PR_TEMPLATE.read_text().replace(old, new) if old else PR_TEMPLATE.read_text()
    )
    if not missing:
        assert run.returncode == 0, run.stderr
        body = (tmp_path / "scratch/body.md").read_text()
        ci = body.split("### Enforced by CI\n", 1)[1].split("\n### ", 1)[0]
        assert ci.count("- [x] ") == 4
        assert "- [ ] " not in ci
        assert "### Adoption PR" not in body
        assert "  - `source_slug: ex`" in body
        assert "_commit" not in body
        return
    assert run.returncode == 1
    assert missing in run.stderr
    assert "Nothing was\ncreated on GitHub; /x/sdk-ex is generated and verified." in run.stderr


def test_core_answers_each_say_their_own() -> None:
    """One core_version answer, the bound's rule in its help; core_git_ref only the pin."""
    questions = yaml.safe_load((ROOT / "copier.yml").read_text())
    version, ref = questions["core_version"]["help"], questions["core_git_ref"]["help"]
    assert "xippios-core~=X.Y.Z" in version
    assert "(ADR-0018 amendment (c))" in version
    assert "pin" not in version, "the pin is core_git_ref's"
    assert "core_version" not in ref, "the bound is core_version's"
    assert "main, or the full 40-character SHA of a commit on main" in ref


def test_core_git_ref_takes_main(template_src: Path, tmp_path: Path) -> None:
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", core_git_ref="main")
    assert 'rev = "main" }' in (dst / "pyproject.toml").read_text()


def git(cwd: Path, *args: str) -> str:
    """git with a fixed identity and no signing, independent of the user's configuration."""
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    unsigned = ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    return subprocess.run(
        ["git", *identity, *unsigned, *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.parametrize("variant", ["bearer-git-core", "header-key", "open", "nested"])
def test_answers_file_is_copiers_canonical_form(
    template_src: Path, tmp_path: Path, variant: str
) -> None:
    """The merge-class check trusts an answers file only as copier writes it back.

    It re-renders the template at ``_commit`` (by SHA) with the answers less ``_commit``
    and ``_src_path`` as ``--data-file`` and compares the answers file byte for byte
    (merge classes, rule 4); a render from a tagged template must survive that.
    """
    repo = tmp_path / "template"
    shutil.copytree(template_src, repo)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "template")
    git(repo, "tag", "v0.0.1")
    sha = git(repo, "rev-parse", "HEAD").strip()
    first = tmp_path / "first"
    run_copy(
        str(repo),
        str(first),
        data={**BASE_ANSWERS, **VARIANTS[variant]},
        defaults=True,
        vcs_ref="v0.0.1",
        quiet=True,
    )
    written = (first / ".copier-answers.yml").read_bytes()
    assert b"_commit: v0.0.1\n" in written
    kept = [
        line
        for line in written.decode().splitlines()
        if not line.startswith(("_commit:", "_src_path:"))
    ]
    data_file = tmp_path / "answers.yml"
    data_file.write_text("\n".join(kept) + "\n")
    again = tmp_path / "again"
    copy = [sys.executable, "-m", "copier", "copy", "--defaults", "--trust", "--skip-tasks"]
    subprocess.run(
        [*copy, "--quiet", "--vcs-ref", sha, "--data-file", str(data_file), str(repo), str(again)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert (again / ".copier-answers.yml").read_bytes() == written


def test_readme_mcp_snippet_is_json(generated: tuple[str, Path]) -> None:
    """The MCP client snippet parses, the key's env only for a keyed source, and no line
    carries a closing brace after the args (the keyless render's trailing brace)."""
    name, dst = generated
    readme = (dst / "README.md").read_text()
    block = readme.split("```json\n", 1)[1].split("```", 1)[0]
    (server,) = json.loads(block)["mcpServers"].values()
    env = str(VARIANTS[name]["api_key_env"])
    assert server.get("env") == ({env: "..."} if env else None)
    (args,) = [line for line in block.splitlines() if '"args"' in line]
    assert args.rstrip().endswith(("]", "],")), args


def test_readme_status_table_names_the_format_the_family_check_reads(
    template_src: Path, tmp_path: Path
) -> None:
    """The family check reads the tables under ``## Status`` with a Task function column."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    readme = (dst / "README.md").read_text()
    status = readme[readme.index("\n## Status\n") :]
    status = status[: status.index("\n## ", 1)]
    comment = " ".join(status[status.index("<!--") : status.index("-->")].split())
    assert "Core's family check (tests/test_family.py) reads this table" in comment
    assert "starts with the task's name in backticks" in comment
    assert "backticked names separated by commas" in comment
    assert "| Upstream operation | Task function | MCP tool | Status |" in status


# Instruction files: what a session or a human reads to act. CHANGELOG history is not one.
INSTRUCTION_FILES = ["copier.yml", "README.md", "CLAUDE.md", ".claude", "scripts", "template"]
HUMAN_TAGS = re.compile(r"\btag v[0-9<]|push the tag|human tags|\bgit tag\b")


def test_no_instruction_tells_a_human_to_tag() -> None:
    """The release train (conventions §12): a release PR's merge tags, through a workflow."""
    scanned = set()
    for name in INSTRUCTION_FILES:
        root = ROOT / name
        for path in [root] if root.is_file() else sorted(root.rglob("*")):
            if not path.is_file() or ".github/workflows" in path.as_posix():
                continue
            scanned.add(path.relative_to(ROOT).as_posix())
            for number, line in enumerate(path.read_text().splitlines(), 1):
                assert not HUMAN_TAGS.search(line), f"{path.relative_to(ROOT)}:{number}: {line}"
    generated_contract = {"template/CLAUDE.md.jinja", "template/.claude/family.md.jinja"}
    assert generated_contract <= scanned, "the facts and the family rules alike"
