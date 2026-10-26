"""Generation tests: variants render, pass ruff, and respect skip-if-exists."""

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
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
    "header-key-write": {
        "source_slug": "comtrade",
        "needs_write_tools": True,
        **keyed("COMTRADE_API_KEY", "header", "Ocp-Apim-Subscription-Key"),
    },
    "bearer": {
        "source_slug": "abc-data",
        "rate_limit_burst": 3,
        "rate_limit_provenance": "self-imposed",
        "core_version": "0.3.0",
        **keyed("ABC_API_KEY", "bearer"),
    },
    "basic-git-core": {
        "source_slug": "cashctrl",
        "core_git_ref": FAKE_CORE_SHA,
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
    "tests/test_family.py",
    "tests/test_tasks.py",
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
    assert (dst / "tests/test_family.py").read_text() == FAMILY_TEST
    level = (dst / "src/xippios" / pkg).parent
    while level != dst / "src":
        assert not (level / "__init__.py").exists(), level
        level = level.parent
    write = bool(answers.get("needs_write_tools"))
    pyproject = (dst / "pyproject.toml").read_text()
    assert (dst / f"src/xippios/{pkg}/tasks_write.py").exists() is write
    assert (dst / f"src/xippios/{pkg}/mcp_write.py").exists() is write
    assert (dst / "tests/test_tasks_write.py").exists() is write
    assert ("-mcp-write" in pyproject) is write
    assert ("[tool.uv.sources]" in pyproject) is bool(answers.get("core_git_ref"))
    tool = tomllib.loads(pyproject)["tool"]
    assert tool["mypy"]["files"] == ["src", "tests", "scripts"], "scripts/ is type-checked"
    sdist = tool["hatch"]["build"]["targets"]["sdist"]
    assert sdist == {"include": ["/src", "/docs", "/README.md", "/CHANGELOG.md", "/LICENSE"]}
    assert "tests" not in json.dumps(sdist), "the sdist ships no tests; they live in the repo"


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
    assert "live_schedule" not in answers


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
        ("basic", "auth = BasicKeyAuth(API_KEY_ENV, source=SOURCE)"),
    ]:
        dst = generate(
            template_src, tmp_path / location, source_slug="ex", **keyed("EX_API_KEY", location)
        )
        client = (dst / "src/xippios/ex/_client.py").read_text()
        assert needle in client, location
        assert '    "auth",\n' in client, "auth is exported"
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
    mine = [f"{pkg}/{n}" for n in ["tasks.py", "_client.py", "__init__.py", "api/__init__.py"]]
    mine.append("tests/test_tasks.py")
    templates = ["CLAUDE.md", "tests/conftest.py", f"{pkg}/mcp.py"]
    for rel in [*mine, *templates]:
        (dst / rel).write_text("# edited\n")
    generate(template_src, dst, source_slug="ex-api", **keyed(""))
    for rel in mine:
        assert (dst / rel).read_text() == "# edited\n", f"{rel} is the source's"
    for rel in templates:
        assert (dst / rel).read_text() != "# edited\n", f"{rel} is the template's"


def test_the_files_a_source_fills_are_one_list(template_src: Path, tmp_path: Path) -> None:
    """The generated contract and /adopt-release name every protected path, in skip order."""
    patterns = yaml.safe_load((template_src / "copier.yml").read_text())["_skip_if_exists"]
    names = [
        f"`{p.removeprefix('src/xippios/{{ package_dir }}/').replace('/**', '/')}`"
        for p in patterns
    ]
    listing = ", ".join(names[:-1]) + f" and {names[-1]}"
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **keyed(""))
    for rel in ["CLAUDE.md", ".claude/commands/adopt-release.md"]:
        assert listing in " ".join((dst / rel).read_text().split()), rel


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


CONFTEST = """\
# Core's plugin keeps the default run offline and free of real keys (ADR-0013), runs anyio
# tests on asyncio and serves the family check in tests/test_family.py; a key's variable is
# named under xippios_placeholder_key_envs in pyproject.toml, not here.
pytest_plugins = ["xippios.core.testing.plugin"]
"""


def test_the_plugin_sends_the_placeholder_unless_live(generated: tuple[str, Path]) -> None:
    """ADR-0013: core's plugin pins the key; a keyed source only names its variable.

    No placeholder fixture, constant or test of the source's own, keyed or open.
    """
    name, dst = generated
    env = str(VARIANTS[name]["api_key_env"])
    assert (dst / "tests/conftest.py").read_text() == CONFTEST
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
    assert "| File | URL | Fetched | Note |" in fetched
    assert "## Attribution" in fetched
    assert "UTC time of the run in ISO 8601 with an explicit `Z`" in fetched


def test_models_use_validation_alias(generated: tuple[str, Path]) -> None:
    """Adapters serialise by alias: a plain alias would hand agents the upstream spelling.

    The scaffold and the fixture check also carry ADR-0017's rule on personal identifiers.
    """
    name, dst = generated
    plain_alias = re.compile(r"Field\((?:[^)]*[\s,])?alias=")
    for path in dst.rglob("*.py"):
        assert not plain_alias.search(path.read_text()), path
    assert "`Field(validation_alias=...)`" in (dst / ".claude/commands/add-endpoint.md").read_text()
    models = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/models.py").read_text()
    assert "fixtures never carry their values (ADR-0017)" in models
    assert "ADR-0017" in (dst / ".claude/commands/record-fixture.md").read_text()


def test_list_tools_are_not_promised(generated: tuple[str, Path]) -> None:
    """A new repository has no list_<thing> tool yet; the wording must hold either way."""
    name, dst = generated
    prefix = str(VARIANTS[name]["source_slug"]).replace("-", "_")
    mcp = (dst / f"src/xippios/{package_dir(VARIANTS[name])}/mcp.py").read_text()
    assert "Call the list tools first" not in mcp
    assert f"Where list tools ({prefix}_list_*) exist" in mcp


def test_servers_take_the_caps_kept_with_the_tasks(template_src: Path, tmp_path: Path) -> None:
    """ADR-0016: per-tool caps live next to the tasks as MCP_CAPS; each server reads its own."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", needs_write_tools=True)
    pkg = dst / "src/xippios/ex"
    assert 'caps=getattr(tasks, "MCP_CAPS", None),' in (pkg / "mcp.py").read_text()
    assert 'caps=getattr(tasks_write, "MCP_CAPS", None),' in (pkg / "mcp_write.py").read_text()
    tasks = (pkg / "tasks.py").read_text()
    assert "#     MCP_CAPS = {" in tasks, "a commented scaffold"
    assert '#     MCP_CAPS: "Mapping[str, ResultCap]" = {}' in tasks, "a base install's caps"


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
    row = f"| Rate limit | {answers['rate_limit_per_minute']} requests per minute, burst {burst}; "
    assert row in claude
    assert "# config = policy.install(config)" in client, "ADR-0015, a commented scaffold"
    assert "one `QuotaPolicy` installed on `config`" in " ".join(claude.split())
    if answers.get("rate_limit_provenance") == "self-imposed":
        assert "# A self-imposed pace: upstream documents no limit" in client
        assert "a self-imposed pace, upstream documents none (ADR-0010)" in claude
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
# secrets).
CORE_VERBATIM = {
    ".github/workflows/gates.yml": (
        # pragma: allowlist nextline secret
        "d5dccf9823d784ffe21ebebd023fb423a2bc2b00c31503a0c58e2d3e94800890"
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
    """The verbatim files are core 0.2.1's bytes; ci.yml and publish.yml core's plus ours."""
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
    for prefix in ["chore/release-", "chore/template-update", "dependabot/"]:
        assert f"!startsWith(github.head_ref, '{prefix}')" in changelog["if"], prefix
    assert cap["name"] == "Fixture files under 256 KiB"
    assert cap["env"]["LEVEL"] == "warning", "an error from template v0.3.0 (ADR-0019)"
    assert "--no-renames --diff-filter=AM" in cap["run"]
    assert "262144" in cap["run"]


def test_workflow_actions_are_pinned_by_sha(generated: tuple[str, Path]) -> None:
    """ci.yml and publish.yml pin every action to a commit, its version in a comment."""
    _, dst = generated
    for rel in [".github/workflows/ci.yml", ".github/workflows/publish.yml"]:
        uses = re.findall(r"^\s+(?:- )?uses: (\S+)(.*)$", (dst / rel).read_text(), re.MULTILINE)
        assert uses, rel
        for action, comment in uses:
            if action.startswith("./"):
                continue
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"{rel}: {action}"
            assert re.fullmatch(r" # v\d+(\.\d+)*", comment), f"{rel}: {action}{comment}"


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
        assert "`chore/template-update-<tag>`" in text
        assert (keyed_line in text) is bool(env), "the ini option, for a keyed source only"
        assert "gh pr merge --auto --squash -R xippios/sdk-ex <number>" in text, "from the root"
        github = "`https://github.com/xippios/sdk-template/blob/<tag>/CHANGELOG.md` (or"
        assert text.index(github) < text.index("git -C ../sdk-template"), "GitHub first"
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
    assert pytest_step["run"] == "uv run pytest -m live", "every live test, write tests too"
    assert all("env" not in step for step in setup), "checkout and uv sync never see it"
    expected_env: dict[str, str] = {"XIPPIOS_LIVE_TESTS": "1"}
    if env_var:
        expected_env[env_var] = f"${{{{ secrets.{env_var} }}}}"
        assert text.count(f"${{{{ secrets.{env_var} }}}}") == 1
        assert text.count("secrets.") == 1
    else:
        assert "secrets." not in text
    assert pytest_step["env"] == expected_env
    claude = (dst / "CLAUDE.md").read_text()
    if env_var:
        step = "Only its `uv run pytest -m live` step sees the key"
        assert f"{step}, from the org secret `{env_var}`." in claude
    write_note = "Every `live` test runs, write tests included"
    assert (write_note in claude) is bool(answers.get("needs_write_tools"))


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


def test_write_path_has_its_own_tests(generated: tuple[str, Path]) -> None:
    """Conventions §8 through core's assert_write_tools, plus what it leaves out."""
    name, dst = generated
    write = bool(VARIANTS[name].get("needs_write_tools"))
    changelog = (dst / "CHANGELOG.md").read_text()
    slug = VARIANTS[name]["source_slug"]
    assert (f"`xippios-{slug}-mcp-write`" in changelog) is write
    if not write:
        return
    test = (dst / "tests/test_tasks_write.py").read_text()
    call = "write_server, WRITE_TASKS.values(), source=SOURCE, read_server=server, router=router"
    assert f"assert_write_tools(\n        {call}\n    )" in test
    assert "list_tools" not in test, "assert_write_tools lists the tools"
    assert '== ["confirm"], "confirm comes last"' in test
    assert "test_tasks_write.py" in (dst / "CLAUDE.md").read_text()


def test_generated_tests_need_no_key(generated: tuple[str, Path]) -> None:
    """The reachability probe sends no key."""
    name, dst = generated
    live = (dst / "tests/test_live.py").read_text()
    assert ("the key's quota" in live) is bool(VARIANTS[name]["api_key_env"]), "keyed only"
    assert "httpx.AsyncClient(" in live
    assert "await http.get(BASE_URL)" in live
    assert "follow_redirects=True" in live
    assert "client.request" not in live, "the package's client would send the key"


def test_documents_promise_what_the_code_does(generated: tuple[str, Path]) -> None:
    """The http docstring states ADR-0007; the CLAUDE.md names every namespace level."""
    name, dst = generated
    pkg = package_dir(VARIANTS[name])
    http = (dst / f"src/xippios/{pkg}/http.py").read_text()
    assert "is a ``GET`` with query parameters" in http
    assert "is a ``POST`` whose JSON body is keyed by parameter name (ADR-0007)" in http
    claude = (dst / "CLAUDE.md").read_text()
    if "/" in pkg:
        provider = pkg.rsplit("/", 1)[0]
        assert f"or `src/xippios/{provider}/__init__.py`, the provider level" in claude
    else:
        assert "the provider level" not in claude
    assert ".github/workflows/live.yml" in claude
    assert "Hand-apply" in claude
    assert "`/adopt-release <tag>` walks it" in claude, "conventions §15, ADR-0018"
    assert "`tests/conftest.py` and `tests/test_family.py` among them" in " ".join(claude.split())
    assert ("xippios_placeholder_key_envs" in claude) is bool(VARIANTS[name]["api_key_env"])
    assert "(ADR-0017)" in claude


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
        "origin/main",
    ],
)
def test_core_git_ref_is_main_or_a_full_sha(template_src: Path, tmp_path: Path, ref: str) -> None:
    """uv and the merge-class check read main or a full SHA as one commit; nothing else."""
    with pytest.raises(ValueError, match="core_git_ref"):
        generate(template_src, tmp_path / "repo", source_slug="ex", core_git_ref=ref, **keyed(""))


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


@pytest.mark.parametrize("variant", ["basic-git-core", "header-key-write", "open", "nested"])
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
    for name in INSTRUCTION_FILES:
        root = ROOT / name
        for path in [root] if root.is_file() else sorted(root.rglob("*")):
            if not path.is_file() or ".github/workflows" in path.as_posix():
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                assert not HUMAN_TAGS.search(line), f"{path.relative_to(ROOT)}:{number}: {line}"
