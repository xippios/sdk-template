"""Generation tests: variants render, pass ruff, and respect skip-if-exists."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]

BASE_ANSWERS: dict[str, object] = {
    "source_name": "Example Data Service",
    "upstream_url": "https://api.example.org",
    "upstream_docs_url": "https://api.example.org/docs",
    "api_base_url": "https://api.example.org/v1",
    "rate_limit_per_minute": 120,
    "domain_topic": "example-domain",
}


def keyed(env: str, location: str = "query", name: str | None = None) -> dict[str, object]:
    """Answers for how the key is sent; values are variables so no line looks like a secret."""
    answers: dict[str, object] = {"api_key_env": env, "api_key_location": location}
    if name is not None:
        answers["api_key_name"] = name
    return answers


VARIANTS: dict[str, dict[str, object]] = {
    "query-key": {"source_slug": "usda-nass", **keyed("NASS_API_KEY", "query", "key")},
    "header-key-write": {
        "source_slug": "comtrade",
        "needs_write_tools": True,
        **keyed("COMTRADE_API_KEY", "header", "Ocp-Apim-Subscription-Key"),
    },
    "bearer": {"source_slug": "abc-data", **keyed("ABC_API_KEY", "bearer")},
    "basic-git-core": {
        "source_slug": "cashctrl",
        "core_git_ref": "main",
        **keyed("CASHCTRL_API_KEY", "basic"),
    },
    "open": {"source_slug": "eurostat", **keyed("")},
    "nested": {"source_slug": "usda-nass", **keyed("NASS_API_KEY", "query", "key")},
    "hyphenated-flat": {"source_slug": "world-bank", "import_path": "world_bank", **keyed("")},
    "long-name-write": {
        "source_slug": "fao-faostat-bulk",
        "source_name": "Food and Agriculture Organization Statistics",
        "needs_write_tools": True,
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
    "src/xippios/{pkg}/models.py",
    "src/xippios/{pkg}/tasks.py",
    "src/xippios/{pkg}/api/__init__.py",
    "src/xippios/{pkg}/mcp.py",
    "src/xippios/{pkg}/http.py",
    "src/xippios/{pkg}/reference/README.md",
    "src/xippios/{pkg}/params.py",
    "src/xippios/{pkg}/enums.py",
    "scripts/refresh_reference.py",
    "tests/conftest.py",
    "tests/test_tasks.py",
    "tests/test_adapters.py",
    "tests/test_layout.py",
    "tests/test_live.py",
    "tests/fixtures/README.md",
    "docs/upstream/FETCHED.md",
    "CLAUDE.md",
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
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".claude/settings.json",
    ".claude/commands/add-endpoint.md",
    ".claude/commands/record-fixture.md",
    ".claude/commands/refresh-upstream.md",
    ".claude/commands/refresh-reference-data.md",
    ".claude/commands/release-prep.md",
    ".copier-answers.yml",
]


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
    level = (dst / "src/xippios" / pkg).parent
    while level != dst / "src":
        assert not (level / "__init__.py").exists(), level
        level = level.parent
    write = bool(answers.get("needs_write_tools"))
    pyproject = (dst / "pyproject.toml").read_text()
    assert (dst / f"src/xippios/{pkg}/tasks_write.py").exists() is write
    assert (dst / f"src/xippios/{pkg}/mcp_write.py").exists() is write
    assert ("-mcp-write" in pyproject) is write
    assert ("[tool.uv.sources]" in pyproject) is bool(answers.get("core_git_ref"))


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
    assert "source_pkg" not in answers, "computed answers are derived, never recorded"
    assert "package_dir" not in answers


def test_no_jinja_left_behind(generated: tuple[str, Path]) -> None:
    """Workflow files are copied verbatim and carry GitHub's own ${{ }}; nothing else may."""
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
        if ".github/workflows" not in str(path):
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
        ("basic", "auth = BasicKeyAuth(API_KEY_ENV, source=SOURCE)"),
    ]:
        dst = generate(
            template_src, tmp_path / location, source_slug="ex", **keyed("EX_API_KEY", location)
        )
        client = (dst / "src/xippios/ex/_client.py").read_text()
        assert needle in client, location
        assert '"SOURCE", "auth", "client"' in client, "the conftest imports auth"
    dst = generate(template_src, tmp_path / "open", source_slug="ex", **keyed(""))
    client = (dst / "src/xippios/ex/_client.py").read_text()
    assert "Auth" not in client
    assert '"auth"' not in client
    assert "API_KEY_ENV: str | None = None" in client
    assert "client = AsyncClient(config)" in client


def test_skip_if_exists_protects_content_files(template_src: Path, tmp_path: Path) -> None:
    dst = generate(template_src, tmp_path / "repo", source_slug="ex-api", **keyed(""))
    tasks = dst / "src/xippios/ex/api/tasks.py"
    claude = dst / "CLAUDE.md"
    tasks.write_text("# my work\n")
    claude.write_text("# clobbered\n")
    (dst / "tests/test_mine.py").write_text("def test_x(): pass\n")
    generate(template_src, dst, source_slug="ex-api", **keyed(""))
    assert tasks.read_text() == "# my work\n"
    assert (dst / "tests/test_mine.py").exists()
    assert claude.read_text() != "# clobbered\n"


def test_tool_prefix_is_the_underscored_slug_everywhere(generated: tuple[str, Path]) -> None:
    """The MCP tool prefix is the slug with underscores, never the dotted import path."""
    name, dst = generated
    slug = str(VARIANTS[name]["source_slug"])
    prefix = slug.replace("-", "_")
    dotted = package_dir(VARIANTS[name]).replace("/", ".")
    for rel in [
        "README.md",
        ".claude/commands/add-endpoint.md",
        f"src/xippios/{package_dir(VARIANTS[name])}/reference/README.md",
    ]:
        text = (dst / rel).read_text()
        assert f"`{prefix}_" in text, rel
        if "." in dotted:
            assert f"{dotted}_" not in text, rel


OPEN_CONFTEST = """import pytest

pytest_plugins = ["xippios.core.testing.plugin"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
"""


def test_conftest_sends_the_placeholder_unless_live(generated: tuple[str, Path]) -> None:
    """Keyed: every test but a live one sends the placeholder, whatever the shell holds.

    The variants cover all four ways a key is sent; each auth class reads it through
    ``key``, which the fixture pins. The open variant has no key handling at all.
    """
    name, dst = generated
    answers = VARIANTS[name]
    conftest = (dst / "tests/conftest.py").read_text()
    test_tasks = (dst / "tests/test_tasks.py").read_text()
    if not answers["api_key_env"]:
        assert conftest == OPEN_CONFTEST
        assert "placeholder" not in test_tasks
        return
    dotted = package_dir(answers).replace("/", ".")
    assert f"from xippios.{dotted}._client import API_KEY_ENV, auth" in conftest
    assert 'if "live" in request.keywords:' in conftest
    assert "monkeypatch.setenv(API_KEY_ENV, PLACEHOLDER_KEY)" in conftest
    assert 'monkeypatch.setattr(auth, "key", lambda: PLACEHOLDER_KEY)' in conftest
    assert "os.environ" not in conftest, "the placeholder must not depend on the shell"
    assert "def test_replay_tests_send_the_placeholder_key" in test_tasks
    assert "sent = next(auth.sync_auth_flow(" in test_tasks, "assert on what goes out"


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
    """Git never converts line endings under docs/upstream/: upstream files may carry CRLF."""
    _, dst = generated
    assert (dst / ".gitattributes").read_text() == "docs/upstream/** -text\n"


def test_models_use_validation_alias(generated: tuple[str, Path]) -> None:
    """Adapters serialise by alias: a plain alias would hand agents the upstream spelling."""
    _, dst = generated
    plain_alias = re.compile(r"Field\((?:[^)]*[\s,])?alias=")
    for path in dst.rglob("*.py"):
        assert not plain_alias.search(path.read_text()), path
    assert "`Field(validation_alias=...)`" in (dst / ".claude/commands/add-endpoint.md").read_text()


def test_list_tools_are_not_promised(generated: tuple[str, Path]) -> None:
    """A new repository has no list_<thing> tool yet; the wording must hold either way."""
    name, dst = generated
    prefix = str(VARIANTS[name]["source_slug"]).replace("-", "_")
    mcp = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/mcp.py").read_text()
    assert "Call the list tools first" not in mcp
    assert f"Where list tools ({prefix}_list_*) exist" in mcp


def test_local_env_files_are_ignored(generated: tuple[str, Path]) -> None:
    """Belt and braces: no variant of a local env file is ever committed."""
    _, dst = generated
    ignored = set((dst / ".gitignore").read_text().splitlines())
    assert {".env", ".env.*", ".envrc", ".envrc.*"} <= ignored
