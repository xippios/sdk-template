"""Generation tests: the family's variants render, pass ruff, and respect skip-if-exists.

Each variant renders once per session; a check that differs between variants reads every
render, a check no answer changes reads one. The tests assert mechanics only: a file
rendered or not, a name present or absent, no Jinja left, a digest equal, a script's
behaviour. ``scripts/prove.sh`` proves that a render passes its own suite.
"""

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
QUESTIONS = yaml.safe_load((ROOT / "copier.yml").read_text())
CORE_DEFAULT = str(QUESTIONS["core_version"]["default"])

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


# What the api.data.gov gateway answer derives (ADR-0009): the key's variable, its
# location and its header, recorded as if answered.
DATA_GOV = "api.data.gov"
GATEWAY_KEY = keyed("DATA_GOV_API_KEY", "header", "X-Api-Key")


def gateway_of(answers: dict[str, object]) -> str:
    return str(answers.get("gateway", "none"))


def key_answers(answers: dict[str, object]) -> dict[str, object]:
    """The three key answers a render reads: the gateway's where it is set, else as given."""
    if gateway_of(answers) == DATA_GOV:
        return GATEWAY_KEY
    return {k: v for k, v in answers.items() if k.startswith("api_key_")}


# The family's variants (T11 as narrowed): the shapes its sources take. Their pace answers
# differ so that both provenances and a burst render; the key locations, a core pin and a
# name at its bound are answers of their own, each tested by its rule below.
VARIANTS: dict[str, dict[str, object]] = {
    # sdk-usda-nass's shape: a key of its own, sent as a query parameter, and a nested
    # import path (ADR-0006); no gateway, answered as such.
    "keyed-nested": {
        "source_slug": "usda-nass",
        "gateway": "none",
        **keyed("NASS_API_KEY", "query", "key"),
    },
    # sdk-eurostat's: no key, a flat import path.
    "keyless-flat": {
        "source_slug": "eurostat",
        "rate_limit_provenance": "self-imposed",
        **keyed(""),
    },
    # sdk-usda-esmis's (and sdk-usda-wasde's): no key, a nested import path; with the
    # 64-character name that broke four docstrings' line length (row 60), which
    # test_generated_code_is_lint_and_format_clean checks with every other file.
    "keyless-nested": {
        "source_slug": "usda-esmis",
        "source_name": "USDA ESMIS (Economics, Statistics and Market Information System)",
        "rate_limit_burst": 3,
        "rate_limit_provenance": "self-imposed",
        **keyed(""),
    },
    # sdk-usda-wasde's, as it will start (ADR-0021): no key, a nested import path, and the
    # source packages it depends on, one open and one keyed, whose variable then reaches
    # the offline placeholder and live.yml (D47).
    "dependency": {
        "source_slug": "usda-wasde",
        "source_dependencies": (
            '[{name: example-base, minor: "0.3", key_env: ""},'
            ' {name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'
        ),
        **keyed(""),
    },
    # sdk-usda-psd's (and sdk-usda-esr's and sdk-usda-gats's): behind the api.data.gov
    # gateway (T9, ADR-0009), which derives the key answers, so none is passed; nested.
    "gateway": {
        "source_slug": "usda-psd",
        "gateway": DATA_GOV,
        "rate_limit_per_minute": 60,
        "rate_limit_provenance": "self-imposed",
    },
    # A source that parses the files it downloads (T-ADR-0020), keyless and nested as
    # sdk-usda-wasde starts: has_files renders parse/ and the samples' provenance table.
    "files": {
        "source_slug": "example-files",
        "has_files": True,
        **keyed(""),
    },
}
# A source on unreleased core: the keyed nested answers with a full-SHA core pin.
PINNED = {**VARIANTS["keyed-nested"], "core_git_ref": FAKE_CORE_SHA}


def package_dir(answers: dict[str, object]) -> str:
    import_path = str(answers.get("import_path") or str(answers["source_slug"]).replace("-", "."))
    return import_path.replace(".", "/")


def dependencies(answers: dict[str, object]) -> list[dict[str, str]]:
    """The source packages a variant depends on, parsed from its answer (ADR-0021)."""
    parsed = yaml.safe_load(str(answers.get("source_dependencies", "[]")))
    assert isinstance(parsed, list)
    return parsed


def has_files(answers: dict[str, object]) -> bool:
    """Whether a variant parses the files it downloads (ADR-0020); copier's default no."""
    return answers.get("has_files", False) is True


def key_envs(answers: dict[str, object]) -> list[str]:
    """Every key variable a render reads: the source's own, then its dependencies', once."""
    own = str(key_answers(answers).get("api_key_env", ""))
    keys = [own] + [d["key_env"] for d in dependencies(answers)]
    return list(dict.fromkeys(key for key in keys if key))


# Every file a render has: the package's at the import path's directories, the rest at the
# repository's root (the sibling check, where the import path nests, is tested on its own).
PACKAGE_FILES = [
    "__init__.py",
    "py.typed",
    "_version.py",
    "_client.py",
    "errors.py",
    "models.py",
    "tasks.py",
    "api/__init__.py",
    "mcp.py",
    "http.py",
    "params.py",
    "enums.py",
    "reference/README.md",
]
REPOSITORY_FILES = [
    "scripts/refresh_reference.py",
    "scripts/refresh_upstream.py",
    "docs/upstream/FETCHED.md",
    "tests/conftest.py",
    "tests/test_family.py",
    "tests/test_tasks.py",
    "tests/test_live.py",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "pyproject.toml",
    ".copier-answers.yml",
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
    ".claude/family.md",
    ".claude/settings.json",
    ".claude/commands/add-endpoint.md",
    ".claude/commands/record-fixture.md",
    ".claude/commands/refresh-upstream.md",
    ".claude/commands/refresh-reference-data.md",
    ".claude/commands/release-prep.md",
    ".claude/commands/adopt-release.md",
]

# Template v0.2.1 deleted the two structural tests: core's family check, which
# tests/test_family.py collects, makes their checks (conventions §10). v0.3.0 renders
# read-only packages (D35).
REMOVED_FILES = [
    "tests/test_layout.py",
    "tests/test_adapters.py",
    "tests/test_tasks_write.py",
    "src/xippios/{pkg}/tasks_write.py",
    "src/xippios/{pkg}/mcp_write.py",
]
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


def ruff(dst: Path, command: str, *args: str) -> subprocess.CompletedProcess[str]:
    """``ruff <command>`` in ``dst``, writing no cache into a render the tests share."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", command, "--no-cache", *args],
        cwd=dst,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="session")
def render(template_src: Path, tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Path]:
    """Each variant rendered once per session, when a test first reads it. The renders are
    shared: a test reads them and writes nothing into them."""
    renders: dict[str, Path] = {}

    def get(name: str) -> Path:
        if name not in renders:
            dst = tmp_path_factory.mktemp(name) / "repo"
            renders[name] = generate(template_src, dst, **VARIANTS[name])
        return renders[name]

    return get


@pytest.fixture(params=list(VARIANTS), scope="session")
def variant(request: pytest.FixtureRequest, render: Callable[[str], Path]) -> tuple[str, Path]:
    """A check that differs between variants, run on each render."""
    return request.param, render(request.param)


@pytest.fixture(scope="session")
def keyed_nested(render: Callable[[str], Path]) -> Path:
    """The render a check no answer changes reads."""
    return render("keyed-nested")


@pytest.fixture(scope="session")
def keyless_flat(render: Callable[[str], Path]) -> Path:
    return render("keyless-flat")


# The checks every variant runs.

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json"}


def test_layout(variant: tuple[str, Path]) -> None:
    """Every file at the import path's directories, no ``__init__.py`` at a namespace level
    (ADR-0006), none of the removed files, one read server and no core pin."""
    name, dst = variant
    answers = VARIANTS[name]
    pkg = package_dir(answers)
    for rel in [*(f"src/xippios/{pkg}/{part}" for part in PACKAGE_FILES), *REPOSITORY_FILES]:
        assert (dst / rel).is_file(), rel
    for rel in REMOVED_FILES:
        assert not (dst / rel.format(pkg=pkg)).exists(), rel
    fixtures = sorted(p.relative_to(dst).as_posix() for p in dst.glob("tests/fixtures/**/*"))
    expected = ["tests/fixtures/files", "tests/fixtures/files/README.md"]
    assert fixtures == (expected if has_files(answers) else []), "the rule is /record-fixture's"
    assert (dst / "tests/test_family.py").read_text() == FAMILY_TEST
    level = (dst / "src/xippios" / pkg).parent
    while level != dst / "src":
        assert not (level / "__init__.py").exists(), level
        level = level.parent
    pyproject = tomllib.loads((dst / "pyproject.toml").read_text())
    slug, dotted = answers["source_slug"], pkg.replace("/", ".")
    assert pyproject["project"]["scripts"] == {f"xippios-{slug}-mcp": f"xippios.{dotted}.mcp:run"}
    assert "uv" not in pyproject["tool"], "no [tool.uv.sources] without core_git_ref"


def test_generated_code_is_lint_and_format_clean(variant: tuple[str, Path]) -> None:
    _, dst = variant
    check = ruff(dst, "check", ".")
    assert check.returncode == 0, check.stdout + check.stderr
    fmt = ruff(dst, "format", "--check", ".")
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr


def test_answers_file_round_trips(variant: tuple[str, Path]) -> None:
    name, dst = variant
    expected = VARIANTS[name]
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["source_slug"] == expected["source_slug"]
    assert answers["import_path"] == package_dir(expected).replace("/", ".")
    assert answers["gateway"] == gateway_of(expected), "recorded, the default included"
    key = key_answers(expected)
    assert answers["api_key_env"] == key["api_key_env"]
    if key["api_key_env"]:
        assert answers["api_key_location"] == key["api_key_location"]
        assert answers["api_key_name"] == key.get("api_key_name", "key")
    else:
        assert "api_key_location" not in answers, "not asked without a key"
        assert "api_key_name" not in answers
    assert answers["source_dependencies"] == expected.get("source_dependencies", "[]")
    assert yaml.safe_load(answers["source_dependencies"]) == dependencies(expected)
    assert answers["has_files"] is has_files(expected), "recorded, the default included"
    for computed in ["package_dir", "tool_prefix", "live_schedule", "depends_on", "key_envs"]:
        assert computed not in answers, f"{computed}: derived, never recorded"
    for gone in ["source_pkg", "domain_topic", "needs_write_tools"]:
        assert gone not in answers, f"{gone}: no question asks it"


def test_no_jinja_left_behind(variant: tuple[str, Path]) -> None:
    """Workflow files carry GitHub's own ${{ }}; nothing else may, and nothing else in them."""
    _, dst = variant
    for path in dst.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text()
        assert "{%" not in text, path
        if ".github/workflows" in str(path):
            assert not re.search(r"(?<!\$)\{\{", text), f"{path}: only ${{{{ }}}} may remain"
        else:
            assert "{{" not in text, path


def test_no_dotted_import_path_used_as_a_directory(variant: tuple[str, Path]) -> None:
    """A nested import path (usda.psd) must appear as usda/psd wherever a path is meant."""
    name, dst = variant
    dotted = package_dir(VARIANTS[name]).replace("/", ".")
    if "." not in dotted:
        pytest.skip("flat import path")
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            assert f"src/xippios/{dotted}" not in path.read_text(), path


def test_tool_prefix_is_the_underscored_slug_everywhere(variant: tuple[str, Path]) -> None:
    """The MCP tool prefix is the slug with underscores, never the dotted import path."""
    name, dst = variant
    slug = str(VARIANTS[name]["source_slug"])
    prefix = slug.replace("-", "_")
    dotted = package_dir(VARIANTS[name]).replace("/", ".")
    for rel in ["README.md", ".claude/commands/add-endpoint.md"]:
        text = (dst / rel).read_text()
        assert f"`{prefix}_" in text, rel
        if "." in dotted:
            assert f"{dotted}_" not in text, rel


def test_the_plugin_sends_the_placeholder_unless_live(variant: tuple[str, Path]) -> None:
    """ADR-0013: core's plugin pins the key; a keyed source only names its variable, and
    the keys of the source packages it depends on beside it (ADR-0021), and only a source
    with a key to name has the option in its conftest (row 61 d). No placeholder fixture,
    constant or test of the source's own."""
    name, dst = variant
    keys = key_envs(VARIANTS[name])
    conftest = (dst / "tests/conftest.py").read_text()
    code = [line for line in conftest.splitlines() if not line.startswith("#")]
    assert code == ['pytest_plugins = ["xippios.core.testing.plugin"]']
    assert ("xippios_placeholder_key_envs" in conftest) is bool(keys)
    ini = tomllib.loads((dst / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert ini.get("xippios_placeholder_key_envs") == (keys or None)
    assert "placeholder" not in (dst / "tests/test_tasks.py").read_text()


def test_rate_limit_renders_pace_burst_and_provenance(variant: tuple[str, Path]) -> None:
    """ADR-0010 decision 1: the pace and the burst in the client and in the facts, and where
    the pace comes from; a quota's policy pointed at (ADR-0015), but behind the gateway,
    whose policy is core's (ADR-0009)."""
    name, dst = variant
    answers = {**BASE_ANSWERS, **VARIANTS[name]}
    per_minute, burst = answers["rate_limit_per_minute"], answers.get("rate_limit_burst", 1)
    self_imposed = answers.get("rate_limit_provenance") == "self-imposed"
    client = (dst / f"src/xippios/{package_dir(answers)}/_client.py").read_text()
    assert f"RATE_LIMIT = RateLimit(per_minute={per_minute}, burst={burst})" in client
    assert ("QuotaPolicy" in client) is (gateway_of(answers) == "none"), "the gateway's own"
    assert ("self-imposed" in client) is self_imposed
    claude = (dst / "CLAUDE.md").read_text().splitlines()
    (row,) = [line for line in claude if line.startswith("| Rate limit | ")]
    assert row.startswith(f"| Rate limit | {per_minute} requests per minute, burst {burst}; ")
    assert ("self-imposed" in row) is self_imposed


def test_client_exports_one_sorted_name_per_line(variant: tuple[str, Path]) -> None:
    """One name per line, so a source's extra export never conflicts on copier update."""
    name, dst = variant
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


def test_the_gateway_answer_renders_cores_gateway(variant: tuple[str, Path]) -> None:
    """T9, ADR-0009: behind api.data.gov the client takes ``xippios.core.data_gov``'s
    ``Gateway``, its auth, its policy's hooks through ``install`` and its ``classify``
    asked first; the facts name ``Gateway`` and its shared policy, and ``live.yml`` the
    shared key. Any other answer renders none of it."""
    name, dst = variant
    answers = VARIANTS[name]
    behind = gateway_of(answers) == DATA_GOV
    client = (dst / f"src/xippios/{package_dir(answers)}/_client.py").read_text()
    lines = client.splitlines()
    assert ("from xippios.core.data_gov import Gateway" in lines) is behind
    assert ("Gateway" in client) is behind
    claude = (dst / "CLAUDE.md").read_text().splitlines()
    (credentials,) = [line for line in claude if line.startswith("| Credentials | ")]
    (rate,) = [line for line in claude if line.startswith("| Rate limit | ")]
    assert ("`Gateway`" in credentials) is behind
    assert ("`Gateway.policy`" in rate) is behind
    assert ("<!-- " in rate) is not behind, "a quota to name where no gateway keeps it"
    live = (dst / ".github/workflows/live.yml").read_text()
    assert (DATA_GOV in live) is behind
    readme = (dst / "README.md").read_text()
    assert (DATA_GOV in readme) is behind
    if not behind:
        return
    for line in [
        "gateway = Gateway(SOURCE)",
        "config = gateway.install(",
        "auth = gateway.auth",
        "client = AsyncClient(config, auth=auth)",
        '    "gateway",',
    ]:
        assert line in lines, line
    (classify,) = [
        node
        for node in ast.parse(client).body
        if isinstance(node, ast.FunctionDef) and node.name == "classify"
    ]
    _, first, second, last = classify.body  # the docstring, then the gateway's say
    assert ast.unparse(first) == "error = gateway.classify(response)"
    assert ast.unparse(second) == "if error is not None:\n    return error"
    assert ast.unparse(last) == "return None"
    (install,) = [
        node.value
        for node in ast.parse(client).body
        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "config"
    ]
    assert isinstance(install, ast.Call)
    assert ast.unparse(install.func) == "gateway.install"
    (config,) = install.args
    assert "classify=classify" in ast.unparse(config)


def test_core_dependency_is_one_minor(variant: tuple[str, Path]) -> None:
    """Conventions §12: one core minor, the extras likewise; a source package depended on
    bound to its minor the same way, ``~=X.Y.0`` (ADR-0021), in no extra."""
    name, dst = variant
    assert CORE_DEFAULT == "0.3.0", "the core release the template adopts, its verbatim files'"
    version = str(VARIANTS[name].get("core_version", CORE_DEFAULT))
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]
    depended = [f"xippios-{d['name']}~={d['minor']}.0" for d in dependencies(VARIANTS[name])]
    assert project["dependencies"] == [f"xippios-core~={version}", *depended]
    assert project["optional-dependencies"] == {
        extra: [f"xippios-core[{extra}]~={version}"] for extra in ["mcp", "http", "testing"]
    }


FILES_TABLE = "| File | Release | URL | Bytes | sha256 | Fetched |"


def test_has_files_renders_the_parsers_and_the_samples_table(variant: tuple[str, Path]) -> None:
    """ADR-0020: a source that parses the files it downloads gets ``parse/``, a package of
    one docstring, and ``tests/fixtures/files/README.md``, the samples' provenance table,
    both skip-listed, and its CLAUDE.md names them in a Files row and in the Layout; every
    other source renders none of it, a retrieval-only one included (row 57)."""
    name, dst = variant
    answers = VARIANTS[name]
    parses, pkg = has_files(answers), package_dir(answers)
    parse = dst / "src/xippios" / pkg / "parse"
    samples = dst / "tests/fixtures/files/README.md"
    assert parse.exists() is parses
    assert samples.exists() is parses
    claude = (dst / "CLAUDE.md").read_text().splitlines()
    assert len([line for line in claude if line.startswith("| Files | ")]) == parses
    layout = [line.split()[0] for line in claude if line.startswith("  ") and line.strip()]
    assert ("parse/" in layout) is parses
    assert ("fixtures/files/" in layout) is parses
    if not parses:
        return
    assert [path.name for path in parse.iterdir()] == ["__init__.py"]
    module = ast.parse((parse / "__init__.py").read_text())
    assert len(module.body) == 1, "a docstring, no code"
    assert ast.get_docstring(module)
    assert f"{FILES_TABLE}\n" in samples.read_text()
    skipped = skip_matcher(pkg)
    for rel in [f"src/xippios/{pkg}/parse/__init__.py", "tests/fixtures/files/README.md"]:
        assert skipped(rel), f"{rel}: the source's once rendered"


def workflow_uses(path: Path) -> list[tuple[str, str]]:
    """Each ``uses:`` of a workflow: the action and what follows it on the line."""
    return re.findall(r"^\s+(?:- )?uses: (\S+)(.*)$", path.read_text(), re.MULTILINE)


CORE_WORKFLOWS = ["ci.yml", "gates.yml", "live.yml", "publish.yml"]


def test_workflow_actions_are_pinned_by_sha(variant: tuple[str, Path]) -> None:
    """ci.yml, publish.yml, live.yml and, where rendered, siblings.yml pin every action to a
    commit, its version in a comment (conventions §13); live.yml and siblings.yml take
    ci.yml's pins."""
    _, dst = variant
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


def skip_matcher(pkg: str) -> Callable[[str], bool]:
    """Whether copier's ``_skip_if_exists`` protects a path, matched as copier 9.19.1 does:
    the patterns rendered, read as gitignore lines by pathspec."""
    rendered = [p.replace("{{ package_dir }}", pkg) for p in QUESTIONS["_skip_if_exists"]]
    return PathSpec.from_lines("gitignore", rendered).match_file


SIBLINGS_SCRIPT = (
    ROOT / "template/.github/{% if '.' in import_path or depends_on %}scripts{% endif %}"
)


def test_siblings_check_renders_where_the_import_path_nests(variant: tuple[str, Path]) -> None:
    """ADR-0006's sibling proof is the template's (T10): siblings.yml and the script it runs
    render, byte for byte and executable, only where the import path nests or the source
    declares a source package it depends on (ADR-0021), outside the skip-listed scripts/ so
    that a source's copy is trusted when identical to the render; a visible job, `ci` never
    aggregates it (ci.yml stays core's)."""
    name, dst = variant
    answers = VARIANTS[name]
    rendered = "/" in package_dir(answers) or bool(dependencies(answers))
    assert (dst / ".github/workflows/siblings.yml").is_file() is rendered
    assert (dst / ".github/scripts").exists() is rendered, "no empty directory where flat"
    assert ("siblings.yml" in (dst / "CLAUDE.md").read_text()) is rendered
    if rendered:
        assert_the_sibling_check(dst, package_dir(answers))


def test_a_flat_source_with_a_dependency_has_the_sibling_check(
    template_src: Path, tmp_path: Path
) -> None:
    """ADR-0021: the check installs a declared dependency beside the wheel, so a flat source
    that declares one renders it too (sdk-eurostat's shape with a dependency)."""
    answers = {**VARIANTS["keyless-flat"], "source_dependencies": DEPENDS_ON_BASE}
    dst = generate(template_src, tmp_path / "repo", **answers)
    assert_the_sibling_check(dst, package_dir(answers))
    assert "siblings.yml" in (dst / "CLAUDE.md").read_text()


DEPENDS_ON_BASE = '[{name: example-base, minor: "0.3", key_env: ""}]'


def assert_the_sibling_check(dst: Path, pkg: str) -> None:
    """The rendered sibling check: the template's files byte for byte, hardened, the token
    for the listing only, outside the skip-listed paths."""
    workflow = dst / ".github/workflows/siblings.yml"
    script = dst / ".github/scripts/check-siblings.sh"
    assert not (dst / "scripts/check-siblings.sh").exists()
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
    skipped = skip_matcher(pkg)
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


def test_live_workflow_hands_the_key_to_its_pytest_step(variant: tuple[str, Path]) -> None:
    """Conventions §10: nightly and on demand; the secrets in the pytest step's env only, the
    source's and those of the source packages it depends on (D47), and a render with no key
    names no key at all (row 61 b)."""
    name, dst = variant
    keys = key_envs(VARIANTS[name])
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
    for key in keys:
        expected_env[key] = f"${{{{ secrets.{key} }}}}"
        assert text.count(f"${{{{ secrets.{key} }}}}") == 1
    assert text.count("secrets.") == len(keys)
    if not keys:
        assert "key" not in text.lower()
    assert pytest_step["env"] == expected_env


def test_release_prep_waits_for_the_dependencies(variant: tuple[str, Path]) -> None:
    """ADR-0021 decision 5: a dependent releases after the packages it depends on, which
    /release-prep names in step 1 only where a dependency is declared."""
    name, dst = variant
    text = (dst / ".claude/commands/release-prep.md").read_text()
    depended = dependencies(VARIANTS[name])
    assert ("ADR-0021 decision 5" in text) is bool(depended)
    for dependency in depended:
        assert f"`xippios-{dependency['name']}`" in text, dependency


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


def test_live_workflow_runs_inside_the_night_window(variant: tuple[str, Path]) -> None:
    _, dst = variant
    live_start(dst)


def test_every_live_run_keeps_payloads_out_of_tracebacks(variant: tuple[str, Path]) -> None:
    """Row 42: every live command, run or documented, takes ``--tb=short``."""
    _, dst = variant
    runs = 0
    for path in sorted(dst.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text()
            assert not re.search(r"pytest -m live(?! --tb=short)", text), path
            runs += text.count("pytest -m live --tb=short")
    assert runs >= 4, "live.yml, CLAUDE.md, .claude/family.md and /release-prep"


# Claude Code imports a line `@<path>` relative to the importing file, never one inside
# backticks or a code block, and cuts a file that loads on demand at 40,000 characters.
FAMILY_RULES = ROOT / "template/.claude/family.md.jinja"
IMPORT_LINE = "@.claude/family.md"
SDK_CORE_DOCS = "https://github.com/xippios/sdk-core/blob/main/docs/"


def test_claude_md_holds_the_facts_and_imports_the_family_rules(
    variant: tuple[str, Path],
) -> None:
    """The source's CLAUDE.md imports the family rules on the line after its intro and names
    its own import path, the provider level where it nests, the key's ini option only where
    there is a key (row 61), and a "Depends on" row naming each bound only where it
    declares a dependency (ADR-0021)."""
    name, dst = variant
    answers = VARIANTS[name]
    slug, pkg = answers["source_slug"], package_dir(answers)
    claude = (dst / "CLAUDE.md").read_text()
    title, intro, first = claude.split("\n\n")[:3]
    assert title.startswith(f"# sdk-{slug} "), title
    assert intro.startswith(f"`xippios-{slug}`"), intro
    assert first == IMPORT_LINE, "the import on a line of its own, first after the intro"
    assert [line for line in claude.splitlines() if line.startswith("@")] == [IMPORT_LINE]
    assert f"`xippios.{pkg.replace('/', '.')}`" in claude
    if "/" in pkg:
        assert f"`src/xippios/{pkg.rsplit('/', 1)[0]}/`" in claude, "the provider level"
    assert ("xippios_placeholder_key_envs" in claude) is bool(key_envs(answers))
    rows = [line for line in claude.splitlines() if line.startswith("| Depends on | ")]
    depended = [f"`xippios-{d['name']}~={d['minor']}.0`" for d in dependencies(answers)]
    assert len(rows) == bool(depended)
    for bound in depended:
        assert bound in rows[0], bound
    assert "../" not in claude, "a relative path leaves the repository (worktree, GitHub)"
    assert len(claude) < 40_000, "Claude Code cuts a file that loads on demand"


def test_generated_tree_names_no_source_and_no_workspace_file(variant: tuple[str, Path]) -> None:
    """Nothing source-specific is scaffolded (ADR-0008), nor a workspace-local reference."""
    _, dst = variant
    caches = {".ruff_cache", "__pycache__"}
    for path in dst.rglob("*"):
        if not path.is_file() or path.name == ".copier-answers.yml" or caches & set(path.parts):
            continue
        text = path.read_text()
        for needle in ["commodity_desc", "corn_2024", "api_GET", "row 12", "COORDINATION"]:
            assert needle not in text, f"{path}: {needle}"


def test_readme_mcp_snippet_is_json(variant: tuple[str, Path]) -> None:
    """The MCP client snippet parses, an env only with a key to name, a dependency's too
    (its tasks run in this server), and no line carries a closing brace after the args (the
    keyless render's trailing brace). The packages depended on are named (ADR-0021)."""
    name, dst = variant
    readme = (dst / "README.md").read_text()
    block = readme.split("```json\n", 1)[1].split("```", 1)[0]
    (server,) = json.loads(block)["mcpServers"].values()
    keys = key_envs(VARIANTS[name])
    assert server.get("env") == (dict.fromkeys(keys, "...") or None)
    for dependency in dependencies(VARIANTS[name]):
        assert f"`xippios-{dependency['name']}`" in readme
    (args,) = [line for line in block.splitlines() if '"args"' in line]
    assert args.rstrip().endswith(("]", "],")), args


# The checks no answer changes, on one render.


def test_family_rules_render_the_same_in_every_source(keyed_nested: Path) -> None:
    """``.claude/family.md`` holds no Jinja, so a render is the template's file byte for
    byte, in every source: it imports nothing and names sdk-core's documents by URL."""
    family = (keyed_nested / ".claude/family.md").read_text()
    assert family == FAMILY_RULES.read_text()
    assert not [line for line in family.splitlines() if line.startswith("@")], "no import"
    for doc in ["conventions.md", "definition-of-done.md", "review-checklist.md"]:
        assert SDK_CORE_DOCS + doc in family, doc
    assert "https://github.com/xippios/sdk-core/tree/main/docs/adr" in family
    assert "../" not in family, "a relative path leaves the repository (worktree, GitHub)"
    assert len(family) < 40_000, "Claude Code cuts a file that loads on demand"


def test_pyproject_tooling(keyed_nested: Path) -> None:
    """mypy covers scripts/; record_property raises no warning; the sdist ships no tests."""
    tool = tomllib.loads((keyed_nested / "pyproject.toml").read_text())["tool"]
    assert tool["mypy"]["files"] == ["src", "tests", "scripts"]
    assert tool["pytest"]["ini_options"]["junit_family"] == "xunit1"
    sdist = tool["hatch"]["build"]["targets"]["sdist"]
    assert sdist == {"include": ["/src", "/docs", "/README.md", "/CHANGELOG.md", "/LICENSE"]}


def test_dev_ruff_is_the_pre_commit_hooks(keyed_nested: Path) -> None:
    """A new lock resolves the ruff the pre-commit hook runs, not the newest one."""
    hooks = yaml.safe_load((keyed_nested / ".pre-commit-config.yaml").read_text())["repos"]
    (rev,) = [repo["rev"] for repo in hooks if repo["repo"].endswith("/ruff-pre-commit")]
    dev = tomllib.loads((keyed_nested / "pyproject.toml").read_text())["dependency-groups"]["dev"]
    assert [spec for spec in dev if spec.startswith("ruff")] == [f"ruff=={rev.removeprefix('v')}"]


def test_secret_detection_skips_the_answers_file(keyed_nested: Path) -> None:
    """The hook and a baseline rescan exclude the same files, the answers file among them."""
    baseline = json.loads((keyed_nested / ".secrets.baseline").read_text())
    (excluded,) = [
        pattern
        for entry in baseline["filters_used"]
        if entry["path"].endswith(".should_exclude_file")
        for pattern in entry["pattern"]
    ]
    config = yaml.safe_load((keyed_nested / ".pre-commit-config.yaml").read_text())
    (hook,) = [h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "detect-secrets"]
    for name in ["uv.lock", ".copier-answers.yml"]:
        assert re.search(excluded, name), name
        assert re.search(hook["exclude"], name), name


def test_generated_baseline_scans_swagger_files(keyed_nested: Path) -> None:
    """sdk-core dropped is_swagger_file: an upstream Swagger snapshot is scanned too."""
    baseline = json.loads((keyed_nested / ".secrets.baseline").read_text())
    filters = {entry["path"] for entry in baseline["filters_used"]}
    assert "detect_secrets.filters.heuristic.is_swagger_file" not in filters
    assert baseline["results"] == {}


def test_local_env_files_are_ignored(keyed_nested: Path) -> None:
    """Belt and braces: no variant of a local env file is ever committed."""
    ignored = set((keyed_nested / ".gitignore").read_text().splitlines())
    assert {".env", ".env.*", ".envrc", ".envrc.*"} <= ignored


TABLE_HEADER = "| File | URL | Fetched | HTTP | Bytes | sha256 | ETag | Last-Modified | Note |"


def test_upstream_snapshot_is_kept_byte_for_byte(keyed_nested: Path) -> None:
    """Git never converts line endings under docs/upstream/: upstream files may carry CRLF.
    FETCHED.md's stub has the columns and the shell row's marker refresh_upstream.py writes."""
    assert (keyed_nested / ".gitattributes").read_text() == "docs/upstream/** -text\n"
    fetched = (keyed_nested / "docs/upstream/FETCHED.md").read_text()
    assert f"{TABLE_HEADER}\n" in fetched
    assert "| (no file) |" in fetched
    assert "## Attribution" in fetched


def test_errors_module_and_classify_hook_are_scaffolded(keyed_nested: Path) -> None:
    """A source's own error classes (conventions §5) and the classify hook (§6), both empty."""
    pkg = keyed_nested / "src/xippios" / package_dir(VARIANTS["keyed-nested"])
    assert (pkg / "errors.py").read_text().endswith("\n__all__: list[str] = []\n")
    client = (pkg / "_client.py").read_text()
    assert "def classify(response: httpx.Response) -> XippiosError | None:" in client
    assert "    return None\n" in client
    assert "    classify=classify,\n" in client, "wired into the config"


def test_models_use_validation_alias(keyed_nested: Path) -> None:
    """Adapters serialise by alias: a plain alias would hand agents the upstream spelling."""
    plain_alias = re.compile(r"Field\((?:[^)]*[\s,])?alias=")
    for path in keyed_nested.rglob("*.py"):
        assert not plain_alias.search(path.read_text()), path
    add_endpoint = (keyed_nested / ".claude/commands/add-endpoint.md").read_text()
    assert "`Field(validation_alias=...)`" in add_endpoint


def test_servers_take_the_caps_kept_with_the_tasks(keyed_nested: Path) -> None:
    """ADR-0016: per-tool caps live next to the tasks as MCP_CAPS; the server reads them.
    ADR-0019 decision 4: beside them ``BULK_TASKS``, empty in the scaffold, names the
    Python-only tasks; the adapters pass ``tasks.__all__`` whole, since core's
    ``register_tasks`` and ``router_from_tasks`` skip those names themselves (row 64)."""
    pkg = keyed_nested / "src/xippios" / package_dir(VARIANTS["keyed-nested"])
    assert 'caps=getattr(tasks, "MCP_CAPS", None),' in (pkg / "mcp.py").read_text()
    tasks = (pkg / "tasks.py").read_text()
    assert "# MCP_CAPS = {" in tasks, "a commented scaffold"
    assert "# from xippios.core import ResultCap" in tasks, "core 0.3.0 exports it"
    (bulk,) = [
        node
        for node in ast.parse(tasks).body
        if isinstance(node, ast.AnnAssign) and ast.unparse(node.target) == "BULK_TASKS"
    ]
    assert ast.unparse(bulk) == "BULK_TASKS: frozenset[str] = frozenset()"
    assert tasks.index("BULK_TASKS") < tasks.index("# MCP_CAPS"), "beside MCP_CAPS"
    whole = "[getattr(tasks, name) for name in tasks.__all__]"
    for adapter in ["mcp.py", "http.py"]:
        assert whole in (pkg / adapter).read_text(), adapter


def test_generated_tests_need_no_key(keyed_nested: Path) -> None:
    """The reachability probe is a plain request: the package's client would send the key."""
    live = (keyed_nested / "tests/test_live.py").read_text()
    assert "httpx.AsyncClient(" in live
    assert "await http.get(BASE_URL)" in live
    assert "follow_redirects=True" in live
    assert "client.request" not in live


# SHA-256 of sdk-core's files the template copies verbatim, at v0.3.0, the core release the
# template adopts: git -C <workspace root>/sdk-core show v0.3.0:<path> | sha256sum (digests,
# not secrets).
CORE_VERBATIM = {
    ".github/workflows/gates.yml": (
        # pragma: allowlist nextline secret
        "cf3097a2a34f40b98d4e511435204fdb07a7edf8aed94bcf5de467bbb0b814c5"
    ),
    ".github/PULL_REQUEST_TEMPLATE.md": (
        # pragma: allowlist nextline secret
        "13900fdecd972d68bc9bab45c21dcfef0b40b73e64ace0f9328e21b7f345d409"
    ),
}
# The same for the two workflows the template extends: core's bytes once the template's
# own lines, named in CLAUDE.md's Rules, are taken out.
CORE_EXTENDED = {
    # pragma: allowlist nextline secret
    ".github/workflows/ci.yml": "ebee09e20d7004a6761c1986f3bc0e16ee4a2dfa749921ac25040ebad5abacab",
    ".github/workflows/publish.yml": (
        # pragma: allowlist nextline secret
        "dc98ee245673db75f639fa94318668078ea0242f07072b6c333716ee9ffdcf9f"
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


def test_workflows_and_pr_template_are_cores_bytes(keyed_nested: Path) -> None:
    """The verbatim files are core's bytes; ci.yml and publish.yml core's plus ours."""
    for rel, digest in CORE_VERBATIM.items():
        assert hashlib.sha256((keyed_nested / rel).read_bytes()).hexdigest() == digest, rel
    ci = (keyed_nested / ".github/workflows/ci.yml").read_text()
    assert ci.count(FETCH_DEPTH) == 1
    core_ci = without(ci.replace(FETCH_DEPTH, ""), *CI_STEPS)
    publish = (keyed_nested / ".github/workflows/publish.yml").read_text()
    core_publish = without(publish, *PUBLISH_STEP)
    for rel, core in [
        (".github/workflows/ci.yml", core_ci),
        (".github/workflows/publish.yml", core_publish),
    ]:
        assert hashlib.sha256(core.encode()).hexdigest() == CORE_EXTENDED[rel], rel


def steps_of(workflow: dict[str, object], job: str) -> list[dict[str, object]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    steps = jobs[job]["steps"]
    assert isinstance(steps, list)
    return steps


def test_ci_reads_the_pull_request_and_runs_once_on_main(keyed_nested: Path) -> None:
    """No push trigger (publish.yml calls it for a release); the two family CI steps."""
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/ci.yml").read_text())
    assert set(workflow[True]) == {"pull_request", "workflow_call"}, "conventions §12"
    steps = steps_of(workflow, "test")
    assert steps[0]["with"] == {"fetch-depth": 0, "persist-credentials": False}
    changelog, cap = steps[1], steps[2]
    assert changelog["name"] == "CHANGELOG.md has an entry"
    for prefix in ["chore/release-", "dependabot/"]:
        assert f"!startsWith(github.head_ref, '{prefix}')" in changelog["if"], prefix
    assert "chore/template-update" not in changelog["if"], "conventions §15 item 9"
    assert cap["name"] == "Fixture files under 256 KiB"
    assert cap["env"]["LEVEL"] == "error", "the cap binds a source from v0.3.0 (ADR-0019)"
    assert "--no-renames --diff-filter=AM" in cap["run"]
    assert "262144" in cap["run"]


def test_publish_is_the_release_train(keyed_nested: Path) -> None:
    """Conventions §12: every push to main; a release tags itself; no concurrency group.

    A release cannot carry a git-pinned core: the tag job refuses it before the tag, so no
    tag is left without a release.
    """
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/publish.yml").read_text())
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
    release_prep = (keyed_nested / ".claude/commands/release-prep.md").read_text()
    assert "-d core_git_ref= -d core_version=X.Y.Z" in release_prep, "the pin goes first"
    slug = VARIANTS["keyed-nested"]["source_slug"]
    assert f"gh pr merge --auto --squash -R xippios/sdk-{slug} <number>" in release_prep


def test_the_session_enables_auto_merge_in_the_repository(keyed_nested: Path) -> None:
    """ADR-0018 decision 3 and amendment (e): core's settings allow the one merge action,
    ``gh pr merge --auto``, and deny no ``gh pr merge``, so ``/adopt-release`` and
    ``/release-prep`` run it in the repository's own panel."""
    permissions = json.loads((keyed_nested / ".claude/settings.json").read_text())["permissions"]
    assert "Bash(gh pr merge --auto *)" in permissions["allow"]
    assert not [rule for rule in permissions["deny"] if rule.startswith("Bash(gh pr merge")]
    slug = VARIANTS["keyed-nested"]["source_slug"]
    for command in ["adopt-release.md", "release-prep.md"]:
        text = (keyed_nested / ".claude/commands" / command).read_text()
        assert f"gh pr merge --auto --squash -R xippios/sdk-{slug} <number>" in text, command


def test_adopt_release_runs_the_update_for_this_source(render: Callable[[str], Path]) -> None:
    """Conventions §15, ADR-0018: one chore/template-update PR that names the nine items
    and whose commands name this source, the key's ini option only where there is a key,
    and a dependency's minor raised with the core's only where there is one (ADR-0021)."""
    update = (
        "uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=<tag>"
        " -d core_version=X.Y.Z -d core_git_ref="
    )
    items = ["Items 1 and 2", "Items 3 and 4", *(f"Item {n}:" for n in range(5, 10))]
    for name in ["keyed-nested", "keyless-flat", "dependency"]:
        dst = render(name)
        text = (dst / ".claude/commands/adopt-release.md").read_text()
        for item in items:
            assert item in text, f"{item}: every item of conventions §15"
        assert update in text
        assert "`chore/template-update-<tag>`" in text
        assert "`https://github.com/xippios/sdk-template/blob/<tag>/CHANGELOG.md`" in text
        assert "`git show HEAD:tests/test_adapters.py`" in text
        assert "uv run python scripts/refresh_reference.py --render-only" in text, "§15 item 6"
        slug = VARIANTS[name]["source_slug"]
        assert f"gh pr merge --auto --squash -R xippios/sdk-{slug} <number>" in text
        keys = key_envs(VARIANTS[name])
        assert ("xippios_placeholder_key_envs" in text) is bool(keys), name
        for key in keys:
            assert f"`{key}`" in text, key
        depended = dependencies(VARIANTS[name])
        assert ("-d source_dependencies=" in text) is bool(depended), name


def assigned(tree: ast.Module) -> set[str]:
    """The names a module assigns at its top level, annotated or not."""
    return {
        target.id
        for node in tree.body
        if isinstance(node, ast.AnnAssign | ast.Assign)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }


def test_reference_data_is_packaged_lists_and_one_renderer(keyless_flat: Path) -> None:
    """Conventions §3, ADR-0022 and ADR-0008 as amended: value lists, id lists and tables
    are fetched into core's ``PackagedList`` and written by it, records under upstream's
    names (``dump_upstream``); ``enums.py`` is one ``render_enums`` call, then ``ruff
    format`` and ``ruff check --fix``; ``--render-only`` re-renders from the packaged
    files, as an adoption does. ``params.py`` names the lists core's loader reads."""
    pkg = keyless_flat / "src/xippios" / package_dir(VARIANTS["keyless-flat"])
    script = ast.parse((keyless_flat / "scripts/refresh_reference.py").read_text())
    assert {"LISTS", "ID_LISTS", "TABLES"} <= assigned(script)
    calls = [ast.unparse(node.func) for node in ast.walk(script) if isinstance(node, ast.Call)]
    assert calls.count("render_enums") == 1, "one module, both kinds"
    for call in ["PackagedList", "record.dump_upstream", "fetched.write", "id_name_pairs"]:
        assert call in calls, call
    loops = [ast.unparse(node.iter) for node in ast.walk(script) if isinstance(node, ast.For)]
    assert "(['format'], ['check', '--fix'])" in loops, "ruff format, then ruff check --fix"
    imported = {
        alias.name
        for node in script.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {"PackagedList", "render_enums", "PACKAGED_LISTS"} <= imported
    assert not {"render_str_enums", "render_int_enums"} & imported, "gone in core 0.3.0"
    params = ast.parse((pkg / "params.py").read_text())
    assert assigned(params) == {"__all__", "PACKAGE", "PACKAGED_LISTS"}, "core's loader reads"
    command = (keyless_flat / ".claude/commands/refresh-reference-data.md").read_text()
    assert "uv run python scripts/refresh_reference.py --render-only" in command


def test_every_command_points_at_the_process(keyless_flat: Path) -> None:
    """The definition of done and the review checklist, by URL, instead of repeated text."""
    commands = sorted((keyless_flat / ".claude/commands").glob("*.md"))
    assert len(commands) == 6
    for path in commands:
        flat = " ".join(path.read_text().split())
        for doc in ["definition-of-done.md", "review-checklist.md"]:
            assert SDK_CORE_DOCS + doc in flat, f"{path.name}: {doc}"
        assert "../" not in flat, f"{path.name}: a relative path leaves a worktree"


def test_readme_status_table_has_the_columns_the_family_check_reads(keyless_flat: Path) -> None:
    """Core's family check reads the tables under ``## Status`` by their Task function column."""
    readme = (keyless_flat / "README.md").read_text()
    status = readme[readme.index("\n## Status\n") :]
    status = status[: status.index("\n## ", 1)]
    assert "| Upstream operation | Task function | MCP tool | Status |" in status


def test_the_files_a_source_fills_are_one_list(keyless_flat: Path) -> None:
    """The family rules and /adopt-release name every protected path, in skip order."""
    names = [
        f"`{p.removeprefix('src/xippios/{{ package_dir }}/').replace('/**', '/')}`"
        for p in QUESTIONS["_skip_if_exists"]
    ]
    listing = ", ".join(names[:-1]) + f" and {names[-1]}"
    assert names[-1] == "`CLAUDE.md`", "the facts are the source's"
    for rel in [".claude/family.md", ".claude/commands/adopt-release.md"]:
        assert listing in " ".join((keyless_flat / rel).read_text().split()), rel


# The answers: what each renders, and what copier refuses.


def test_key_auth_matches_location(
    template_src: Path, tmp_path: Path, keyed_nested: Path, keyless_flat: Path
) -> None:
    """Each key location renders its auth, exported, in a ruff-clean ``_client.py``, the one
    Python file the location changes; a keyless client has none; ``basic`` is refused (D35)."""
    clients = {
        "query": keyed_nested / "src/xippios/usda/nass/_client.py",
        "": keyless_flat / "src/xippios/eurostat/_client.py",
    }
    for location in ["header", "bearer"]:
        answers = keyed("EX_API_KEY", location)
        dst = generate(template_src, tmp_path / location, source_slug="ex", **answers)
        clients[location] = dst / "src/xippios/ex/_client.py"
        for args in [("check",), ("format", "--check")]:
            run = ruff(dst, *args, "src/xippios/ex/_client.py")
            assert run.returncode == 0, run.stdout + run.stderr
    for location, auth in [
        ("query", 'QueryKeyAuth("key", API_KEY_ENV, source=SOURCE)'),
        ("header", 'HeaderKeyAuth("X-Api-Key", API_KEY_ENV, source=SOURCE)'),
        ("bearer", "BearerAuth(API_KEY_ENV, source=SOURCE)"),
    ]:
        client = clients[location].read_text()
        assert f"auth = {auth}" in client, location
        assert '    "auth",\n' in client, "auth is exported"
    keyless = clients[""].read_text()
    assert "Auth" not in keyless
    assert '"auth"' not in keyless
    assert "API_KEY_ENV: str | None = None" in keyless
    assert "client = AsyncClient(config)" in keyless
    with pytest.raises(ValueError, match="api_key_location"):
        generate(template_src, tmp_path / "basic", source_slug="ex", **keyed("EX_API_KEY", "basic"))


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


@pytest.mark.parametrize("ref", ["main", FAKE_CORE_SHA])
def test_core_git_ref_pins_core_and_keeps_the_bound(
    template_src: Path, tmp_path: Path, ref: str
) -> None:
    """uv takes a pinned core from ``[tool.uv.sources]`` and does not check the bound against
    it, so the bound stays ``~=``; the pin's ``rev`` line is allowlisted for detect-secrets,
    which a 40-character commit SHA trips without the pragma."""
    dst = generate(template_src, tmp_path / "repo", **{**PINNED, "core_git_ref": ref})
    pyproject = (dst / "pyproject.toml").read_text()
    parsed = tomllib.loads(pyproject)
    git_source = {"git": "https://github.com/xippios/sdk-core.git", "rev": ref}
    assert parsed["tool"]["uv"]["sources"] == {"xippios-core": git_source}
    assert parsed["project"]["dependencies"] == [f"xippios-core~={CORE_DEFAULT}"]
    update = "uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=:current:"
    assert f"{update} -d core_git_ref=" in pyproject, "copier 9.19.0 on, _min_copier_version"
    (rev,) = [line for line in pyproject.splitlines() if line.startswith("xippios-core = {")]
    assert "# pragma: allowlist secret" in rev
    if ref == "main":
        return
    scan = tmp_path / "scan"
    scan.mkdir()
    shutil.copy(dst / ".secrets.baseline", scan / ".secrets.baseline")
    (scan / "pyproject.toml").write_text(pyproject)
    (scan / "unmarked.toml").write_text(pyproject.replace(rev, rev.split("  # pragma")[0]))
    hook = detect_secrets_hook(scan, "pyproject.toml")
    assert hook.returncode == 0, hook.stdout + hook.stderr
    control = detect_secrets_hook(scan, "unmarked.toml")
    assert control.returncode == 1, "without the pragma the SHA must be flagged"
    assert "Hex High Entropy String" in control.stdout, control.stdout


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


# A line at column 0 of an answers file that the merge classes read (sdk-gates README,
# rule 2): a plain key, a colon, then a blank or the end of the line.
ANSWER_LINE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*:(?:[ \t].*)?")


def test_answers_file_stays_in_the_merge_classes_subset(variant: tuple[str, Path]) -> None:
    """The merge classes read an answers file whose lines at column 0 are comments or plain
    ``key: value`` lines only, and free a new answer at its question's literal default, one
    scalar (rule 2). ``source_dependencies`` is a string holding a YAML flow list, so a
    list of dependencies never writes block lines there, and its default, the string
    ``[]``, is recorded as that one quoted scalar; ``gateway``'s default, ``none``, as
    one plain scalar."""
    name, dst = variant
    text = (dst / ".copier-answers.yml").read_text()
    for line in text.splitlines():
        if line and not line.startswith(("#", " ", "\t")):
            assert ANSWER_LINE.fullmatch(line), line
    question = QUESTIONS["source_dependencies"]
    assert (question["type"], question["default"]) == ("str", "[]")
    raw = (ROOT / "copier.yml").read_text().split("\nsource_dependencies:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert '\n  default: "[]"\n' in block, "one quoted scalar, a literal for rule 2"
    if not dependencies(VARIANTS[name]):
        assert "\nsource_dependencies: '[]'\n" in text
    # The gateway answer, which every source before it lacks, is free at its default.
    assert (QUESTIONS["gateway"]["type"], QUESTIONS["gateway"]["default"]) == ("str", "none")
    raw = (ROOT / "copier.yml").read_text().split("\ngateway:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: none\n" in block, "one plain scalar, a literal for rule 2"
    assert f"\ngateway: {gateway_of(VARIANTS[name])}\n" in text
    # has_files likewise: a bool whose default, false, is one plain scalar.
    assert (QUESTIONS["has_files"]["type"], QUESTIONS["has_files"]["default"]) == ("bool", False)
    raw = (ROOT / "copier.yml").read_text().split("\nhas_files:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: false\n" in block, "one plain scalar, a literal for rule 2"
    assert f"\nhas_files: {str(has_files(VARIANTS[name])).lower()}\n" in text


@pytest.mark.parametrize(
    "value",
    [
        "",
        "{name: example-base, minor: '0.3', key_env: ''}",
        "[{name: example-base, minor: '0.3'}]",
        "[{name: example-base, minor: '0.3', key_env: '', extra: 1}]",
        "[{name: Example_Base, minor: '0.3', key_env: ''}]",
        "[{name: ex, minor: '0.3', key_env: ''}]",
        "[{name: core, minor: '0.3', key_env: ''}]",
        "[{name: a, minor: '0.3', key_env: ''}, {name: a, minor: '0.2', key_env: ''}]",
        "[{name: example-base, minor: 0.10, key_env: ''}]",
        "[{name: example-base, minor: '0.3.0', key_env: ''}]",
        "[{name: example-base, minor: '0.3', key_env: EXAMPLE_KEY}]",
        "[{name: example-base",
    ],
)
def test_source_dependencies_are_slugs_minors_and_key_variables(
    template_src: Path, tmp_path: Path, value: str
) -> None:
    """ADR-0021: each entry names another source by its slug, neither this one nor core and
    each once, its minor as ``X.Y`` in quotes (YAML reads 0.10 as a number), and its key's
    variable or ``""``; nothing else, and nothing that is not a YAML flow list."""
    with pytest.raises(ValueError, match="source_dependencies"):
        generate(
            template_src,
            tmp_path / "repo",
            source_slug="ex",
            source_dependencies=value,
            **keyed(""),
        )


@pytest.mark.parametrize(
    ("answers", "refused"),
    [
        ({"gateway": "data.gov"}, "gateway"),
        ({"gateway": DATA_GOV, **keyed("EX_API_KEY", "header")}, "api_key_env"),
        ({"gateway": DATA_GOV, **keyed("")}, "api_key_env"),
        ({"gateway": DATA_GOV, **keyed("DATA_GOV_API_KEY")}, "api_key_location"),
        ({"gateway": DATA_GOV, **keyed("DATA_GOV_API_KEY", "header", "Key")}, "api_key_name"),
        ({"gateway": DATA_GOV, "core_version": "0.2.1"}, "core_version"),
    ],
)
def test_the_gateway_derives_the_key_answers(
    template_src: Path, tmp_path: Path, answers: dict[str, object], refused: str
) -> None:
    """D84 (1): behind api.data.gov the three key answers are derived, never asked, so an
    answer that differs from the gateway's is refused rather than rendered beside it, and
    so is a core before 0.3.0, which has no ``xippios.core.data_gov``."""
    with pytest.raises(ValueError, match=refused):
        generate(template_src, tmp_path / "repo", source_slug="ex", **answers)


def test_the_sibling_check_names_the_declared_dependencies(render: Callable[[str], Path]) -> None:
    """The script reads the source packages a render depends on from ``pyproject.toml``,
    every ``xippios-*`` but core in ``[project] dependencies`` (ADR-0021), to install and
    import them beside the wheel; run here offline on the dependency render."""
    dst = render("dependency")
    script = (dst / ".github/scripts/check-siblings.sh").read_text()
    opening = """names="$("$python" - <<'PY'\n"""
    start = script.index(opening) + len(opening)
    reader = script[start : script.index("\nPY\n", start)]
    run = subprocess.run(
        [sys.executable, "-c", reader], cwd=dst, capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    names = [f"xippios-{d['name']}" for d in dependencies(VARIANTS["dependency"])]
    assert run.stdout.split() == names


SOURCE_NAME = "{{ source_name }}"


def test_source_name_is_bounded_by_the_longest_python_line(
    template_src: Path, tmp_path: Path
) -> None:
    """A name at the bound renders ruff-clean (E501 at 100 columns); one more is refused, as
    are the characters the generated Python cannot quote. The keyless nested variant's
    64-character name, sdk-usda-esmis's (row 60), lies between 60 and the bound."""
    lines = [
        line
        for path in (ROOT / "template").rglob("*.py.jinja")
        for line in path.read_text().splitlines()
        if SOURCE_NAME in line
    ]
    bound = 100 - max(len(line) - len(SOURCE_NAME) for line in lines)
    assert f"at most {bound} characters" in QUESTIONS["source_name"]["help"]
    assert 60 < len(str(VARIANTS["keyless-nested"]["source_name"])) <= bound
    name = ("Data Service " * 7)[: bound - 1] + "s"
    dst = generate(template_src, tmp_path / "bound", source_slug="ex", source_name=name)
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr
    for refused in ["x" * (bound + 1), 'The "Data" Service', "Data\\Service"]:
        with pytest.raises(ValueError, match="source_name"):
            generate(template_src, tmp_path / "refused", source_slug="ex", source_name=refused)


def git(cwd: Path, *args: str) -> str:
    """git with a fixed identity and no signing, independent of the user's configuration."""
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    unsigned = ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    return subprocess.run(
        ["git", *identity, *unsigned, *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.parametrize("case", [*VARIANTS, "pinned"])
def test_answers_file_is_copiers_canonical_form(
    template_src: Path, tmp_path: Path, case: str
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
        data={**BASE_ANSWERS, **{**VARIANTS, "pinned": PINNED}[case]},
        defaults=True,
        vcs_ref="v0.0.1",
        quiet=True,
    )
    written = (first / ".copier-answers.yml").read_bytes()
    assert b"_commit: v0.0.1\n" in written
    recorded = yaml.safe_load(written)
    expected = {**VARIANTS, "pinned": PINNED}[case]
    assert recorded["gateway"] == gateway_of(expected)
    assert recorded["has_files"] is has_files(expected)
    key = key_answers(expected)
    assert recorded["api_key_env"] == key["api_key_env"]
    for answer, value in key.items() if key["api_key_env"] else []:
        assert recorded[answer] == value, f"{answer}: recorded, so the re-render reads it back"
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


def test_import_path_overrides_the_slug_for_every_package_path(
    template_src: Path, tmp_path: Path
) -> None:
    """ADR-0006 and ``import_path``'s help: a single-API provider whose slug carries a
    hyphen overrides the import path (world-bank, world_bank). Every package path and the
    entry point follow ``import_path``; a line that derived one from the slug instead
    would render world.bank or world/bank."""
    dst = generate(
        template_src, tmp_path / "repo", source_slug="world-bank", import_path="world_bank"
    )
    for part in PACKAGE_FILES:
        assert (dst / "src/xippios/world_bank" / part).is_file(), part
    assert sorted(path.name for path in (dst / "src/xippios").iterdir()) == ["world_bank"]
    scripts = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["scripts"]
    assert scripts == {"xippios-world-bank-mcp": "xippios.world_bank.mcp:run"}
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text()
            assert "world.bank" not in text, path
            assert "world/bank" not in text, path
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr


def test_skip_if_exists_protects_content_files(template_src: Path, tmp_path: Path) -> None:
    """A source's files survive a re-render; the template's own are rendered again.

    The slug ends in -api, so the package itself is .../api/: the patterns name the package
    directory, and its mcp.py is the template's while its api/ is the source's, as are the
    parsers' package and the samples' table that has_files renders (ADR-0020).
    """
    answers = {"source_slug": "ex-api", "has_files": True, **keyed("")}
    dst = generate(template_src, tmp_path / "repo", **answers)
    pkg = "src/xippios/ex/api"
    names = ["tasks.py", "_client.py", "errors.py", "__init__.py", "api/__init__.py"]
    mine = [f"{pkg}/{n}" for n in [*names, "parse/__init__.py"]]
    mine += ["tests/test_tasks.py", "tests/fixtures/files/README.md", "CLAUDE.md"]
    templates = [".claude/family.md", "tests/conftest.py", f"{pkg}/mcp.py"]
    for rel in [*mine, *templates]:
        (dst / rel).write_text("# edited\n")
    generate(template_src, dst, **answers)
    for rel in mine:
        assert (dst / rel).read_text() == "# edited\n", f"{rel} is the source's"
    for rel in templates:
        assert (dst / rel).read_text() != "# edited\n", f"{rel} is the template's"


def test_sources_sharing_a_key_start_at_stable_different_times(
    template_src: Path, tmp_path: Path, render: Callable[[str], Path]
) -> None:
    """ADR-0009: usda-psd, usda-esr and usda-gats share one key and one gateway quota; their
    nightly runs never start together, and a render keeps a repository's time."""
    shared = VARIANTS["gateway"]
    starts = {"usda-psd": live_start(render("gateway"))}
    for slug in ["usda-esr", "usda-gats"]:
        dst = generate(template_src, tmp_path / slug, **{**shared, "source_slug": slug})
        starts[slug] = live_start(dst)
    assert len(set(starts.values())) == 3, starts
    again = generate(template_src, tmp_path / "again", **shared)
    assert live_start(again) == starts["usda-psd"], "stable across renders"


# The scripts: new-source.sh and the capture skeleton.


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


# The template's own files.


JINJA_BLOCK_TAG = re.compile(r"\{%-?\s*(\w+)[^%]*?-?%\}")
OPENS_A_BLOCK = {"if", "for", "macro", "block", "call", "filter", "raw", "with"}


def test_block_tags_that_span_lines_stand_on_their_own() -> None:
    """``trim_blocks`` drops the newline after a block tag that ends a line, so a tag after
    content takes that line's newline with it (481f479: the blank lines lost in the
    generated CLAUDE.md's Commands and between /record-fixture's steps 1 and 2), and a
    block opened mid-line puts the line's newline inside it (row 61 a: the keyless
    README's MCP snippet closing its server on the args line). In every ``.jinja`` file a
    block tag stands alone on its line or opens and closes there, before the line's end."""
    misplaced = []
    for path in sorted((ROOT / "template").rglob("*.jinja")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            tags = JINJA_BLOCK_TAG.findall(line)
            if not tags or JINJA_BLOCK_TAG.fullmatch(line.strip()):
                continue
            depth = lowest = 0
            for word in tags:
                depth += (word in OPENS_A_BLOCK) - word.startswith("end")
                lowest = min(lowest, depth)
            if depth or lowest or line.rstrip().endswith("%}"):
                misplaced.append(f"{path.relative_to(ROOT)}:{number}: {line}")
    assert not misplaced, "\n".join(misplaced)


def test_the_templates_own_gates_caller_is_the_one_it_ships() -> None:
    """sdk-template carries core's gates.yml as every repository does, off until GATES_CALLER."""
    own = (ROOT / ".github/workflows/gates.yml").read_bytes()
    assert own == (ROOT / "template/.github/workflows/gates.yml").read_bytes()
    assert hashlib.sha256(own).hexdigest() == CORE_VERBATIM[".github/workflows/gates.yml"]


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


def test_ci_proves_the_familys_variants() -> None:
    """T11: the required ``ci`` job runs scripts/prove.sh on the keyed nested, the keyless
    flat, the keyless nested, the keyless nested shape that parses files (``has_files``,
    ADR-0020) and the gateway shape (T9), so a proof that fails blocks the merge."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    (job,) = workflow["jobs"].values()
    assert job["name"] == "ci", "the check the org ruleset requires"
    runs = [str(step.get("run", "")) for step in job["steps"]]
    proofs = [run for run in runs if run.startswith("scripts/prove.sh")]
    assert proofs == [
        "scripts/prove.sh",
        "scripts/prove.sh --keyless",
        "scripts/prove.sh --keyless-nested",
        "scripts/prove.sh --keyless-nested -d has_files=true",
        "scripts/prove.sh --gateway",
    ]


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
