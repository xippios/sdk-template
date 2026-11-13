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
import os
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
from copier import run_copy, run_update
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
    # the offline placeholder and live.yml (D47); the first parser package, it parses the
    # files it downloads (ADR-0020), so has_files renders parse/ and the samples' table.
    "dependency": {
        "source_slug": "usda-wasde",
        "source_dependencies": (
            '[{name: example-base, minor: "0.3", key_env: ""},'
            ' {name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'
        ),
        "has_files": True,
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


def live_secrets(answers: dict[str, object]) -> list[str]:
    """The other variables a render's live run reads (#105), parsed from its answer; none at
    the default, which every variant takes."""
    parsed = yaml.safe_load(str(answers.get("live_secrets", "[]")))
    assert isinstance(parsed, list)
    return parsed


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
    "scripts/adr_index.py",
    "docs/upstream/FETCHED.md",
    "docs/adr/README.md",
    "docs/adr.md",
    "docs/adr.json",
    "docs/reports/README.md",
    "tests/conftest.py",
    "tests/test_family.py",
    "tests/test_tasks.py",
    "tests/test_live.py",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "changelog/README.md",
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
    ".github/workflows/live.yml",
    ".github/workflows/organization.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/CODEOWNERS",
    ".claude/settings.json",
    ".claude/commands/add-endpoint.md",
    ".claude/commands/record-fixture.md",
    ".claude/commands/refresh-upstream.md",
    ".claude/commands/refresh-reference-data.md",
    ".claude/commands/release-prep.md",
]

# Template v0.2.1 deleted the two structural tests: core's family check, which
# tests/test_family.py collects, makes their checks (conventions §10). v0.3.0 renders
# read-only packages (D35). v0.3.3 renders no caller of the retired merge gates, whose
# reusable workflows are gone (#99), and no family rules beside CLAUDE.md, whose rules the
# CLAUDE.md, the commands and sdk-core's documents state (#128).
REMOVED_FILES = [
    "tests/test_layout.py",
    "tests/test_adapters.py",
    "tests/test_tasks_write.py",
    "src/xippios/{pkg}/tasks_write.py",
    "src/xippios/{pkg}/mcp_write.py",
    ".github/workflows/gates.yml",
    ".claude/family.md",
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
    assert answers["live_secrets"] == expected.get("live_secrets", "[]"), "the default included"
    assert yaml.safe_load(answers["live_secrets"]) == live_secrets(expected)
    assert answers["has_files"] is has_files(expected), "recorded, the default included"
    assert answers["human"] == HUMAN, "recorded, the default included"
    computed = ["package_dir", "tool_prefix", "live_schedule", "depends_on", "key_envs"]
    for derived in [*computed, "live_secret_names"]:
        assert derived not in answers, f"{derived}: derived, never recorded"
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


CORE_WORKFLOWS = ["ci.yml", "live.yml", "publish.yml"]
# The caller of the organization's checks (#129): its jobs call reusable workflows of
# xippios/.github at `@main`, the one reference to another repository that is not pinned
# (conventions §13).
ORG_CALLER = "organization.yml"
ORG_WORKFLOW = "xippios/.github/.github/workflows/{}.yml@main"


def test_workflow_actions_are_pinned_by_sha(variant: tuple[str, Path]) -> None:
    """ci.yml, publish.yml, live.yml and, where rendered, siblings.yml pin every action to a
    commit, its version in a comment (conventions §13); live.yml and siblings.yml take
    ci.yml's pins. The caller of the organization's checks calls them at ``@main``."""
    _, dst = variant
    workflows = dst / ".github/workflows"
    rendered = sorted(path.name for path in workflows.glob("*.yml"))
    always = [*CORE_WORKFLOWS, ORG_CALLER]
    assert rendered in [sorted(always), sorted([*always, "siblings.yml"])]
    for rel in rendered:
        uses = workflow_uses(workflows / rel)
        assert uses, rel
        for action, comment in uses:
            if action.startswith("./"):
                continue
            if rel == ORG_CALLER:
                assert re.fullmatch(r"xippios/\.github/\.github/workflows/[\w-]+\.yml@main", action)
                assert not comment, f"{rel}: {action}{comment}"
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
    declares a source package it depends on (ADR-0021), outside the skip-listed paths so
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
    assert script.stat().st_mode & 0o111, "executable, as rendered"
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


LIVE_RUN = "uv run pytest -m live --tb=short --assert=plain"


def assert_the_live_env(dst: Path, keys: list[str], secrets: list[str]) -> None:
    """Conventions §10: nightly and on demand; the secrets in the pytest step's env only, each
    once, the keys first, the source's and those of the source packages it depends on (D47),
    then the others the answer ``live_secrets`` names (#105), in its order; a render with no
    key names no key at all (row 61 b). The run takes ``--assert=plain`` beside
    ``--tb=short``, so a failed assertion prints no value it compared, a record of the
    upstream among them, into a log that is public (#58)."""
    text = (dst / ".github/workflows/live.yml").read_text()
    workflow = yaml.safe_load(text)
    triggers = workflow[True]  # YAML 1.1 reads the key `on` as a boolean
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert "env" not in workflow, "the secret reaches the pytest step only"
    (job,) = workflow["jobs"].values()
    assert "env" not in job, "the secret reaches the pytest step only"
    *setup, pytest_step = job["steps"]
    assert pytest_step["run"] == LIVE_RUN, "every live test"
    assert all("env" not in step for step in setup), "checkout and uv sync never see it"
    checkout = setup[0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {"persist-credentials": False}, "conventions §13"
    expected_env: dict[str, str] = {"XIPPIOS_LIVE_TESTS": "1"}
    for name in [*keys, *secrets]:
        expected_env[name] = f"${{{{ secrets.{name} }}}}"
        assert text.count(f"${{{{ secrets.{name} }}}}") == 1
    assert text.count("secrets.") == len(keys) + len(secrets)
    if not keys:
        assert "key" not in text.lower()
    assert pytest_step["env"] == expected_env
    assert list(pytest_step["env"]) == list(expected_env), "the answers' order"


def test_live_workflow_hands_the_key_to_its_pytest_step(variant: tuple[str, Path]) -> None:
    """Every variant takes ``live_secrets``' default, so its pytest step names its keys and
    no other secret."""
    name, dst = variant
    assert_the_live_env(dst, key_envs(VARIANTS[name]), live_secrets(VARIANTS[name]))


# Two variables a live run reads beside its key, as sdk-faostat's username and password.
LIVE_SECRETS = "[A_B, C_D]"


@pytest.mark.parametrize("key", ["", "EX_API_KEY"])
def test_live_secrets_reach_the_pytest_step(template_src: Path, tmp_path: Path, key: str) -> None:
    """#105: two names render two more lines on the pytest step, after the key where the
    source has one, and the answer is recorded on one line at column 0, a quoted scalar."""
    dst = generate(
        template_src,
        tmp_path / "repo",
        source_slug="ex",
        live_secrets=LIVE_SECRETS,
        **keyed(key),
    )
    assert_the_live_env(dst, [key] if key else [], ["A_B", "C_D"])
    assert f"\nlive_secrets: '{LIVE_SECRETS}'\n" in (dst / ".copier-answers.yml").read_text()


KEYED_DEPENDENCY = '[{name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'


@pytest.mark.parametrize(
    ("value", "answers"),
    [
        ("", keyed("")),
        ("A_B", keyed("")),
        ("{A_B: C_D}", keyed("")),
        ("[a_b]", keyed("")),
        ("[A-B]", keyed("")),
        ("[1_A]", keyed("")),
        ("[[A_B]]", keyed("")),
        ("[A_B, A_B]", keyed("")),
        ("[GITHUB_TOKEN]", keyed("")),
        ("[XIPPIOS_LIVE_TESTS]", keyed("")),
        ("[EX_API_KEY]", keyed("EX_API_KEY")),
        (
            "[EXAMPLE_KEYED_API_KEY]",
            {"source_dependencies": KEYED_DEPENDENCY, **keyed("")},
        ),
        ("[A_B", keyed("")),
    ],
)
def test_live_secrets_are_names_the_step_sets_once(
    template_src: Path, tmp_path: Path, value: str, answers: dict[str, object]
) -> None:
    """#105: a YAML flow list of UPPER_SNAKE_CASE names, each once; none a key, which
    ``api_key_env`` or ``source_dependencies`` passes already, none the switch the step sets
    itself and none of GitHub's prefix, which no secret takes; nothing that is not a list."""
    with pytest.raises(ValueError, match="live_secrets"):
        generate(template_src, tmp_path / "repo", source_slug="ex", live_secrets=value, **answers)


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
    assert runs >= 4, "live.yml, CLAUDE.md's commands and live run, and /release-prep"


# Claude Code imports a line `@<path>` relative to the importing file, never one inside
# backticks or a code block, and cuts a file that loads on demand at 40,000 characters.
SDK_CORE_DOCS = "https://github.com/xippios/sdk-core/blob/main/docs/"


def test_claude_md_holds_the_facts_and_imports_nothing(variant: tuple[str, Path]) -> None:
    """The source's CLAUDE.md links the README's documents in its intro and imports no
    file (#128), and names its own import path, the provider level where it nests, the key's
    ini option only where there is a key (row 61), and a "Depends on" row naming each bound
    only where it declares a dependency (ADR-0021)."""
    name, dst = variant
    answers = VARIANTS[name]
    slug, pkg = answers["source_slug"], package_dir(answers)
    claude = (dst / "CLAUDE.md").read_text()
    title, intro = claude.split("\n\n")[:2]
    assert title.startswith(f"# sdk-{slug} "), title
    assert intro.startswith(f"`xippios-{slug}`"), intro
    assert "(README.md#documents)" in intro, "the README's section, linked"
    assert not [line for line in claude.splitlines() if line.startswith("@")], "no import"
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


# The render's documents and instructions (#128). The README lists the repository's
# documents under `## Documents`, each by its file on GitHub, and links nothing relative,
# since PyPI shows it with no repository around it. The CLAUDE.md links that section instead
# of repeating it, says what the package wraps, its layout, its commands and its code rules,
# and names nothing around the repository, nor does any file under .claude/.
DOCUMENT_ITEM = re.compile(
    r"- (?P<repository>[\w-]+): \[(?P<path>[^\]]+)\]"
    r"\(https://github\.com/xippios/(?P<on>[\w-]+)/blob/main/(?P<file>[^)\s]+)\) — \S"
)
CORE_DOCUMENTS = [
    "docs/conventions.md",
    "docs/adr.md",
    "docs/definition-of-done.md",
    "docs/review-checklist.md",
]
OWN_DOCUMENTS = ["docs/adr.md", "docs/upstream/FETCHED.md"]
# What a repository that works alone names nothing of, in its CLAUDE.md and its .claude/:
# the tooling around it, its sessions and claims, its numbered rules, a pull request's
# class and the script before the tooling.
AROUND = re.compile(
    r"\bcoordinat|\bworkspace\b|\bsessions?\b|\bclaims?\b|\bC\d+\b|\bmerge[ -]class"
    r"|\bcoord\.py\b",
    re.I,
)
# What its CLAUDE.md says nothing of on how a change lands: a branch, the GitHub CLI, a
# merge, a reviewer or a person, and the release's own files and section.
CHANGE_LANDING = re.compile(
    r"\bbranch(?:es)?\b|\b(?:feature|fix|chore|docs)/<|\bgh\b|\bmerg(?:e|es|ed|ing)\b"
    r"|\breviewers?\b|\bJohannes\b|\bjdidaskalu\b|docs/handover\.md|\bUnreleased\b",
    re.I,
)
SECRET_SUFFIXES = ["`_API_KEY`", "`_REFRESH_TOKEN`", "`_SECRET`"]
LIVE_COMMAND = "uv run pytest -m live --tb=short --assert=plain"


def documents(readme: str) -> list[tuple[str, str]]:
    """The items under a README's ``## Documents``, up to the next heading, as (repository,
    path): an item not in the form, or whose URL is not its repository's path, fails."""
    section = readme.split("\n## Documents\n", 1)[1].split("\n## ", 1)[0]
    found = []
    for item in [line for line in section.splitlines() if line.strip()]:
        match = DOCUMENT_ITEM.match(item)
        assert match, item
        assert (match["on"], match["file"]) == (match["repository"], match["path"]), item
        found.append((match["repository"], match["path"]))
    return found


def layout_entries(claude: str) -> list[str]:
    """The first word of each entry of the CLAUDE.md's Layout block: a line at the left
    margin or two spaces in, never a description's continuation."""
    block = claude.split("\n## Layout\n", 1)[1].split("```\n", 2)[1]
    lines = [line for line in block.splitlines() if line.strip()]
    return [line.split()[0] for line in lines if len(line) - len(line.lstrip()) <= 2]


def secrecy_rule(claude: str) -> str:
    """The rule of the Never list on what is never read or printed, its lines joined."""
    never = claude.split("\n## Never\n", 1)[1].split("\n## ", 1)[0]
    (rule,) = [item for item in never.split("\n- ") if "`.envrc`" in item]
    return " ".join(rule.split())


def test_the_readme_lists_its_documents(variant: tuple[str, Path]) -> None:
    """``## Documents`` lists sdk-core's conventions, ADR index, definition of done and review
    checklist, then the source's own ADR index and upstream snapshot, each as
    ``- <repository>: [<path>](<its file on GitHub>) — <what it is>``; the source's own are
    files of the render."""
    name, dst = variant
    own = f"sdk-{VARIANTS[name]['source_slug']}"
    readme = (dst / "README.md").read_text()
    assert readme.count("\n## Documents\n") == 1
    expected = [("sdk-core", path) for path in CORE_DOCUMENTS]
    expected += [(own, path) for path in OWN_DOCUMENTS]
    assert documents(readme) == expected
    for path in OWN_DOCUMENTS:
        assert (dst / path).is_file(), path


def test_the_readme_links_only_by_url(variant: tuple[str, Path]) -> None:
    """#28 (a): PyPI shows the README with no repository around it, so every link is a URL,
    the license's its file on GitHub."""
    name, dst = variant
    readme = (dst / "README.md").read_text()
    targets = re.findall(r"\]\(([^)\s]+)\)", readme)
    assert [target for target in targets if not target.startswith("https://")] == []
    slug = VARIANTS[name]["source_slug"]
    assert f"[LICENSE](https://github.com/xippios/sdk-{slug}/blob/main/LICENSE)" in readme


def test_the_status_table_comment_names_both_task_lists(keyless_flat: Path) -> None:
    """#88: core's family check reads the status table against ``tasks.__all__`` and
    ``tasks_write.__all__``, so the comment above the table names both."""
    readme = (keyless_flat / "README.md").read_text()
    status = readme[readme.index("\n## Status\n") :]
    comment = status.split("<!--", 1)[1].split("-->", 1)[0]
    for name in ["tasks.__all__", "tasks_write.__all__"]:
        assert name in comment, name


def test_claude_md_and_its_commands_name_nothing_around_the_repository(
    variant: tuple[str, Path],
) -> None:
    """The CLAUDE.md and every file under ``.claude/`` name no tooling, session, claim,
    numbered rule or pull request's class around the repository, and the CLAUDE.md no branch, no
    GitHub CLI, no merge, no reviewer and no person; no ``.claude/family.md`` is left."""
    _, dst = variant
    found = []
    claude = dst / "CLAUDE.md"
    paths = [claude, *sorted(p for p in (dst / ".claude").rglob("*") if p.is_file())]
    for path in paths:
        patterns = [AROUND, CHANGE_LANDING] if path == claude else [AROUND]
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                found.append(f"{path.relative_to(dst)}:{number}: {line}")
    assert not found, "\n".join(found)
    assert not (dst / ".claude/family.md").exists()
    assert "family.md" not in claude.read_text()


def test_claude_md_links_the_documents_and_repeats_none(variant: tuple[str, Path]) -> None:
    """The CLAUDE.md names the documents through the README's section: no URL that the
    section lists stands in it."""
    _, dst = variant
    readme = (dst / "README.md").read_text()
    claude = (dst / "CLAUDE.md").read_text()
    for repository, path in documents(readme):
        url = f"https://github.com/xippios/{repository}/blob/main/{path}"
        assert url not in claude, url
    assert "https://github.com/xippios/sdk-core/tree/" not in claude


def test_the_secrecy_rule_names_every_credential_variable(variant: tuple[str, Path]) -> None:
    """#82: the Never list's secrecy rule names each credential variable of the source, its
    keys and its dependencies' (none in a keyless render), and the endings of every other
    credential's variable that sdk-core's review checklist names."""
    name, dst = variant
    rule = secrecy_rule((dst / "CLAUDE.md").read_text())
    for variable in [*key_envs(VARIANTS[name]), *live_secrets(VARIANTS[name])]:
        assert f"`{variable}`" in rule, variable
    for suffix in SECRET_SUFFIXES:
        assert suffix in rule, suffix


@pytest.mark.parametrize("key", ["", "EX_API_KEY"])
def test_claude_md_names_the_live_secrets(template_src: Path, tmp_path: Path, key: str) -> None:
    """#108, #82: the variables ``live_secrets`` names stand in the live run's paragraph after
    the key, in the answer's order, and in the secrecy rule beside the key."""
    dst = generate(
        template_src,
        tmp_path / "repo",
        source_slug="ex",
        live_secrets=LIVE_SECRETS,
        **keyed(key),
    )
    claude = (dst / "CLAUDE.md").read_text()
    names = [*([key] if key else []), "A_B", "C_D"]
    rule = secrecy_rule(claude)
    (live,) = [p for p in claude.split("\n\n") if p.startswith("`.github/workflows/live.yml`")]
    live = " ".join(live.split())
    for name in names:
        assert f"`{name}`" in rule, name
    places = [live.find(f"`{name}`") for name in names]
    assert -1 not in places, live
    assert places == sorted(places), "the keys first, then the answer's order"


def test_claude_md_lays_out_the_decisions_and_the_fragments(variant: tuple[str, Path]) -> None:
    """#135: the Layout lists ``scripts/adr_index.py``, ``docs/adr/`` with its index and
    ``docs/reports/``, which the render holds, and ``changelog/``; where ``siblings.yml``
    renders, the entry it continues ends with a comma (#35)."""
    _, dst = variant
    claude = (dst / "CLAUDE.md").read_text()
    entries = layout_entries(claude)
    for entry in ["adr_index.py", "adr/", "adr.md", "adr.json", "reports/", "changelog/"]:
        assert entry in entries, entry
    block = claude.split("\n## Layout\n", 1)[1].split("```\n", 2)[1].splitlines()
    siblings = [n for n, line in enumerate(block) if line.lstrip().startswith("siblings.yml")]
    for number in siblings:
        assert block[number - 1].rstrip().endswith(","), block[number - 1]


def test_claude_md_lays_out_every_workflow(variant: tuple[str, Path]) -> None:
    """#145: the Layout's ``.github/workflows/`` entry names each workflow the render has,
    the caller of the organization's checks among them, and none it lacks."""
    _, dst = variant
    claude = (dst / "CLAUDE.md").read_text()
    block = claude.split("\n## Layout\n", 1)[1].split("```\n", 2)[1].splitlines()
    start = next(n for n, line in enumerate(block) if line.startswith(".github/workflows/"))
    end = next((n for n in range(start + 1, len(block)) if block[n][:1].strip()), len(block))
    named = set(re.findall(r"\b[\w-]+\.yml\b", " ".join(block[start:end])))
    rendered = {path.name for path in (dst / ".github/workflows").glob("*.yml")}
    assert named == rendered


def test_claude_md_asks_for_a_fragment_and_takes_a_release_with_copier(
    keyed_nested: Path,
) -> None:
    """#130: a change's changelog entry is a fragment under ``changelog/``, as
    ``changelog/README.md`` lays it out; a template release is taken with one ``copier
    update`` at its tag."""
    claude = " ".join((keyed_nested / "CLAUDE.md").read_text().split())
    for name in [
        "`changelog/`",
        "`changelog/README.md`",
        "`uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=<tag>`",
    ]:
        assert name in claude, name


def test_every_documented_live_run_asserts_plain(variant: tuple[str, Path]) -> None:
    """#58: wherever the render documents the live run, in its CLAUDE.md and its commands,
    the command is ``uv run pytest -m live --tb=short --assert=plain``, as ``live.yml``
    runs it."""
    _, dst = variant
    claude = (dst / "CLAUDE.md").read_text()
    for path in [dst / "CLAUDE.md", *sorted((dst / ".claude/commands").glob("*.md"))]:
        text = " ".join(path.read_text().split())
        assert text.count("pytest -m live") == text.count(LIVE_COMMAND), path.name
    assert claude.count(LIVE_COMMAND) >= 2, "the commands and the live run's paragraph"
    assert LIVE_COMMAND in (dst / ".claude/commands/release-prep.md").read_text()


def test_no_instruction_calls_a_hand_written_enumeration_unexported(keyed_nested: Path) -> None:
    """#36: an enumeration written by hand lives in ``models.py`` by precedent, and one a
    dependent imports is part of its source's contract, so no instruction calls it
    unexported."""
    for rel in ["CLAUDE.md", ".claude/commands/add-endpoint.md"]:
        assert "unexported" not in (keyed_nested / rel).read_text(), rel


# The human paths of a member (C70 as amended by coordinate-core#122 and #167), in the order
# the rendered .github/CODEOWNERS lists them; a PyPI member's one manifest is pyproject.toml.
MEMBER_HUMAN_PATHS = [
    "/.github/**",
    "/CLAUDE.md",
    "/.claude/**",
    "/rules/**",
    "/pyproject.toml",
    "/.copier-answers.yml",
]
HUMAN = "jdidaskalu"
# What a file of a repository that works alone names nothing of: the tooling around it, its
# sessions, and its numbered rules and their files (#129).
AROUND_THE_REPOSITORY = re.compile(r"\bcoordinat|\bworkspace|\bsessions?\b|\bC\d+\b", re.I)


def owner_rules(dst: Path) -> list[str]:
    """The rules of a render's ``.github/CODEOWNERS``: its lines but comments and blanks."""
    lines = (dst / ".github/CODEOWNERS").read_text().splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def test_codeowners_names_the_human_for_every_member_path(variant: tuple[str, Path]) -> None:
    """A source's ``.github/CODEOWNERS`` comes from its template: a header of comments that
    says what the file is, names each path it owns and the answer it is rendered from, and
    no tool, rule or file around the repository (#129), then the six human paths, each
    owned by the ``human`` answer, its default ``jdidaskalu`` in every variant. The
    answer's help names each path too."""
    _, dst = variant
    assert (QUESTIONS["human"]["type"], QUESTIONS["human"]["default"]) == ("str", HUMAN)
    rules = owner_rules(dst)
    assert rules == [f"{path} @{HUMAN}" for path in MEMBER_HUMAN_PATHS]
    lines = (dst / ".github/CODEOWNERS").read_text().splitlines()
    head = lines[: lines.index(rules[0])]
    assert head, "a header"
    assert all(line.startswith("#") for line in head), "the header, then the rules"
    header = " ".join(head)
    assert "`human`" in header, "the answer it is rendered from"
    assert not AROUND_THE_REPOSITORY.search(header), AROUND_THE_REPOSITORY.search(header)
    help_text = " ".join(str(QUESTIONS["human"]["help"]).split())
    for path in MEMBER_HUMAN_PATHS:
        name = path.removeprefix("/").removesuffix("**")
        assert f"`{name}`" in header, f"the header names {name}"
        assert f" {name}" in help_text, f"the help names {name}"


# The checks no answer changes, on one render.


CHANGELOG_README = ROOT / "template/changelog/README.md"


def test_a_render_keeps_its_changelog_entries_as_fragments(keyed_nested: Path) -> None:
    """``changelog/`` renders its README alone, the template's file byte for byte, so every
    source gets the same one. It is the template's and updates with it: ``_skip_if_exists``
    anchors the source's README at the root, so the folder's README is no source content."""
    folder = keyed_nested / "changelog"
    assert sorted(path.name for path in folder.iterdir()) == ["README.md"]
    assert (folder / "README.md").read_text() == CHANGELOG_README.read_text()
    protected = skip_matcher(package_dir(VARIANTS["keyed-nested"]))
    assert protected("README.md"), "the source's README"
    assert not protected("changelog/README.md"), "the template's, as every source shares it"


# A repository's decisions (#121): its records in docs/adr/, the index scripts/adr_index.py
# writes from their headers, and its dated reports in docs/reports/. The script and the two
# READMEs are the template's and update with it; the records, the reports and the index
# generated from the records are the source's, the index kept by _skip_if_exists, as are the
# two scripts a source fills. The template keeps the same folders for itself.
ADR_SCRIPT = "scripts/adr_index.py"
ADR_INDEX = ["docs/adr.md", "docs/adr.json"]
ADR_TEMPLATE_FILES = [ADR_SCRIPT, "docs/adr/README.md", "docs/reports/README.md"]
FILLED_SCRIPTS = ["scripts/refresh_reference.py", "scripts/refresh_upstream.py"]


def adr_index(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """``repo``'s own ``scripts/adr_index.py`` as a check runs it: ``python3 -I`` from the
    repository's root, the script finding the repository from its own path."""
    return subprocess.run(
        [sys.executable, "-I", ADR_SCRIPT, *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_render_keeps_its_decisions_and_their_index(keyed_nested: Path) -> None:
    """``docs/adr/`` and ``docs/reports/`` render their READMEs alone, the template's files
    byte for byte, as is the executable script, and the empty index passes ``--check`` run as
    a check runs it. The index is the source's, kept by ``_skip_if_exists`` with the two
    scripts a source fills; the script of the index and the two READMEs are the template's."""
    for folder in ["docs/adr", "docs/reports"]:
        assert sorted(p.name for p in (keyed_nested / folder).iterdir()) == ["README.md"], folder
    for rel in ADR_TEMPLATE_FILES:
        assert (keyed_nested / rel).read_bytes() == (ROOT / "template" / rel).read_bytes(), rel
    assert os.access(keyed_nested / ADR_SCRIPT, os.X_OK), "executable, as its first line says"
    run = adr_index(keyed_nested, "--check")
    assert run.returncode == 0, run.stdout
    assert json.loads((keyed_nested / "docs/adr.json").read_text()) == {"records": []}
    protected = skip_matcher(package_dir(VARIANTS["keyed-nested"]))
    for rel in [*ADR_INDEX, *FILLED_SCRIPTS]:
        assert protected(rel), f"{rel} is the source's"
    for rel in ADR_TEMPLATE_FILES:
        assert not protected(rel), f"{rel} is the template's"


def test_the_index_follows_the_records(keyed_nested: Path, tmp_path: Path) -> None:
    """The rendered script writes the index from the records' headers and ``--check`` judges
    it: a new record leaves the index stale until the script runs. A record whose first line
    does not read ``# ADR-NNNN: <title>`` with its name's number, and a number two records
    take, fail both runs, which name the record and write nothing; a file of another name in
    ``docs/adr/`` is no record."""
    repo = tmp_path / "repo"
    for rel in [ADR_SCRIPT, *ADR_INDEX, "docs/adr/README.md"]:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(keyed_nested / rel, repo / rel)
    (repo / "docs/adr/0001-one-decision.md").write_text(
        "# ADR-0001: One decision\n\n"
        "Status: Accepted · Date: 2026-11-13 · Decided by https://example.org/1\n\n"
        "## Context\n"
    )
    assert adr_index(repo, "--check").returncode == 1, "stale against the new record"
    assert adr_index(repo).returncode == 0
    assert adr_index(repo, "--check").returncode == 0
    (entry,) = json.loads((repo / "docs/adr.json").read_text())["records"]
    assert entry["id"] == "ADR-0001"
    assert entry["path"] == "docs/adr/0001-one-decision.md"
    assert (entry["status"], entry["date"]) == ("Accepted", "2026-11-13")
    assert entry["decided_by"] == "https://example.org/1"
    assert "](adr/0001-one-decision.md)" in (repo / "docs/adr.md").read_text()
    written = {rel: (repo / rel).read_text() for rel in ADR_INDEX}
    for name, title in [("0002-misnumbered.md", "ADR-0003"), ("0001-again.md", "ADR-0001")]:
        (repo / "docs/adr" / name).write_text(f"# {title}: A record\n")
        for args in [(), ("--check",)]:
            run = adr_index(repo, *args)
            assert run.returncode == 1, (name, args)
            assert f"docs/adr/{name}" in run.stdout, (name, args)
        assert {rel: (repo / rel).read_text() for rel in ADR_INDEX} == written, name
        (repo / "docs/adr" / name).unlink()


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


def test_copiers_leftovers_stay_untracked(keyed_nested: Path, tmp_path: Path) -> None:
    """A `.rej` that `copier update` leaves for a hunk it could not apply, and an `.orig`,
    are never committed: the `.gitignore` names both, at any depth."""
    ignored = set((keyed_nested / ".gitignore").read_text().splitlines())
    assert {"*.rej", "*.orig"} <= ignored
    repo = tmp_path / "repo"
    shutil.copytree(keyed_nested, repo)
    git(repo, "init", "-q", "-b", "main")
    (repo / ".github/workflows/ci.yml.rej").write_text("@@ -1 +1 @@\n-a\n+b\n")
    (repo / "pyproject.toml.orig").write_text("[project]\n")
    untracked = git(repo, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert "?? pyproject.toml" in untracked
    assert not [line for line in untracked if line.endswith((".rej", ".orig"))], untracked


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
    mcp = (pkg / "mcp.py").read_text()
    assert "add_options=" in mcp, "core's hooks for a source's options (ADR-0014)"
    assert "tenant_lock" not in mcp, "core 0.3.0's build_server has none"


def test_generated_tests_need_no_key(keyed_nested: Path) -> None:
    """The reachability probe is a plain request: the package's client would send the key."""
    live = (keyed_nested / "tests/test_live.py").read_text()
    assert "httpx.AsyncClient(" in live
    assert "await http.get(BASE_URL)" in live
    assert "follow_redirects=True" in live
    assert "client.request" not in live


# SHA-256 of sdk-core's files the template departs from, at v0.3.0, the core release the
# template adopts: git -C <workspace root>/sdk-core show v0.3.0:<path> | sha256sum (digests,
# not secrets). A render is core's bytes once the template's own lines, named in
# CLAUDE.md's Rules, are taken out. Core's gates.yml is no file of the template's (#99),
# and the PR template links core's definition of done where it copied it (#129).
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
CI_STEPS = (
    "      # Conventions §12: every PR but Dependabot's",
    "      - uses: astral-sh/setup-uv@",
)
PUBLISH_STEP = (
    "      # sdk-template's one step beyond core's file",
    "      - name: Tag the merge commit",
)


def without(text: str, first: str, stop: str) -> str:
    """``text`` without the lines from the one starting ``first`` up to ``stop``."""
    start = text.index(first)
    return text[:start] + text[text.index(stop, start) :]


def test_workflows_are_cores_bytes(keyed_nested: Path) -> None:
    """ci.yml and publish.yml are core's plus ours."""
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


# The changelog step's condition: every pull request but Dependabot's, which writes no
# entry. An adoption's pull request carries one (conventions §15 item 9), and a release's
# changes CHANGELOG.md itself (#136).
CHANGELOG_STEP_RUNS = (
    "github.event_name == 'pull_request' && !startsWith(github.head_ref, 'dependabot/')"
)


def test_ci_reads_the_pull_request_and_runs_once_on_main(keyed_nested: Path) -> None:
    """No push trigger (publish.yml calls it for a release); the two family CI steps."""
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/ci.yml").read_text())
    assert set(workflow[True]) == {"pull_request", "workflow_call"}, "conventions §12"
    steps = steps_of(workflow, "test")
    assert steps[0]["with"] == {"fetch-depth": 0, "persist-credentials": False}
    changelog, cap = steps[1], steps[2]
    assert changelog["name"] == "The changelog has an entry"
    assert changelog["if"] == CHANGELOG_STEP_RUNS, "Dependabot's branch alone (#136)"
    assert cap["name"] == "Fixture files under 256 KiB"
    assert cap["env"]["LEVEL"] == "error", "the cap binds a source from v0.3.0 (ADR-0019)"
    assert "git diff -z --name-only --find-renames=100% --diff-filter=AM" in cap["run"]
    assert "--no-renames" not in cap["run"], "a pure move adds and changes no fixture"
    assert "262144" in cap["run"]


CAP = 262144  # 256 KiB, ADR-0019


def pull_request_step(repo: Path, step: dict[str, object]) -> subprocess.CompletedProcess[str]:
    """The script of a step that reads the pull request, in ``repo``, as GitHub runs a step
    that names no shell (``bash -e``), the pull request's base ``main`` at ``origin/main``."""
    step_env = step["env"]
    assert isinstance(step_env, dict)
    env = {**os.environ, **step_env, "BASE": "main"}
    return subprocess.run(
        ["bash", "-e", "-c", str(step["run"])],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fixture_cap_judges_a_moved_fixture_by_its_content(
    keyed_nested: Path, tmp_path: Path
) -> None:
    """ADR-0019 caps the fixture files a pull request adds or changes. A pure ``git mv`` of
    a fixture over the cap adds and changes no content, so the step passes it (conventions
    §10 keeps such a fixture until a PR re-records it); one moved and grown, or a new one
    over the cap, fails under its new path."""
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/ci.yml").read_text())
    step = steps_of(workflow, "test")[2]
    repo = tmp_path / "source"
    old = repo / "tests/fixtures/get_old"
    old.mkdir(parents=True)
    listed = b"[" + b"0," * (CAP // 2) + b"0]"
    (old / "all.json").write_bytes(listed)
    (old / "one.json").write_bytes(b"[0]")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    def pull_request(branch: str, change: Callable[[Path], None]) -> tuple[int, str]:
        git(repo, "checkout", "-q", "-b", branch, "main")
        git(repo, "mv", "tests/fixtures/get_old", "tests/fixtures/get_new")
        change(repo / "tests/fixtures/get_new")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--no-verify", "-m", branch)
        run = pull_request_step(repo, step)
        assert run.stderr == "", run.stderr
        return run.returncode, run.stdout

    def grow(new: Path) -> None:
        (new / "all.json").write_bytes((new / "all.json").read_bytes() + b"\n")

    def add(new: Path) -> None:
        (new / "one.json").write_bytes(b"[1]")
        (new / "big.json").write_bytes(b"1" * CAP)

    assert pull_request("moved", lambda new: None) == (0, ""), "a pure move passes"
    over = "::error file=tests/fixtures/get_new/{}::{} bytes, over the 256 KiB cap (ADR-0019)\n"
    assert pull_request("grown", grow) == (1, over.format("all.json", len(listed) + 1))
    assert pull_request("added", add) == (1, over.format("big.json", CAP))


# The groups of a changelog fragment, `changelog/<group>-<slug>.md`, in the order the
# release assembles them (changelog/README.md).
CHANGELOG_GROUPS = ("added", "changed", "fixed", "removed", "security", "breaking")
FRAGMENT = re.compile(rf"(?:{'|'.join(CHANGELOG_GROUPS)})-[a-z0-9]+(?:-[a-z0-9]+)*\.md")


def test_the_changelog_step_takes_a_fragment_or_the_changelog(
    keyed_nested: Path, tmp_path: Path
) -> None:
    """Conventions §12: every pull request but a release or Dependabot's carries an entry,
    a fragment ``changelog/<group>-<slug>.md`` it adds or changes, or a change of
    ``CHANGELOG.md``. The folder's README, a file of another name and a fragment deleted
    are none."""
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/ci.yml").read_text())
    step = steps_of(workflow, "test")[1]
    repo = tmp_path / "source"
    (repo / "changelog").mkdir(parents=True)
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n")
    (repo / "changelog/README.md").write_text("# Changelog fragments\n")
    (repo / "changelog/fixed-an-old-bug.md").write_text("- An old fix.\n")
    (repo / "tasks.py").write_text("")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

    def pull_request(branch: str, change: Callable[[Path], None]) -> int:
        git(repo, "checkout", "-q", "-b", branch, "main")
        (repo / "tasks.py").write_text(f"# {branch}\n")
        change(repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--no-verify", "-m", branch)
        run = pull_request_step(repo, step)
        assert run.stderr == "", run.stderr
        assert run.stdout.startswith("::error::") is (run.returncode != 0), run.stdout
        return run.returncode

    def write(rel: str, text: str = "- A change.\n") -> Callable[[Path], None]:
        def change(root: Path) -> None:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)

        return change

    for group in CHANGELOG_GROUPS:
        assert pull_request(group, write(f"changelog/{group}-a-change.md")) == 0, group
    unreleased = "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- A change.\n"
    assert pull_request("unreleased", write("CHANGELOG.md", unreleased)) == 0
    assert pull_request("reworded", write("changelog/fixed-an-old-bug.md", "- A fix.\n")) == 0
    assert pull_request("code", lambda root: None) == 1, "no entry"
    assert pull_request("readme", write("changelog/README.md", "# Fragments\n")) == 1
    for name in ["feature-a-change.md", "added_a_change.md", "Added-a-change.md", "added-.md"]:
        assert pull_request(name, write(f"changelog/{name}")) == 1, name
    assert pull_request("nested", write("changelog/added/a-change.md")) == 1

    def delete(root: Path) -> None:
        (root / "changelog/fixed-an-old-bug.md").unlink()

    assert pull_request("deleted", delete) == 1, "a fragment deleted is no entry"


def test_the_template_keeps_its_changelog_entries_as_fragments() -> None:
    """The template's next release is assembled from ``changelog/``: its README and a
    fragment per change, each named ``<group>-<slug>.md`` and holding one bullet."""
    folder = ROOT / "changelog"
    assert (folder / "README.md").is_file()
    for path in sorted(folder.iterdir()):
        if path.name == "README.md":
            continue
        assert path.is_file(), path.name
        assert FRAGMENT.fullmatch(path.name), path.name
        text = path.read_text()
        assert text.startswith("- "), path.name
        assert len([line for line in text.splitlines() if line.startswith("- ")]) == 1, path.name


def test_the_template_keeps_its_decisions_as_a_render_does() -> None:
    """The template keeps ``docs/adr/``, ``docs/reports/`` and the script of the index for
    itself, the script and the two READMEs byte for byte the files it renders, and its own
    index is current against its own records, run as a check runs it."""
    for rel in ADR_TEMPLATE_FILES:
        assert (ROOT / rel).read_bytes() == (ROOT / "template" / rel).read_bytes(), rel
    assert os.access(ROOT / ADR_SCRIPT, os.X_OK)
    run = adr_index(ROOT, "--check")
    assert run.returncode == 0, run.stdout


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


# /release-prep keeps the source's own checks before a release (#114, #127): the release
# train as `publish.yml` runs it, which tags the merge commit, and nothing on how the
# release's pull request is opened or merged, by whom, or from which branch. A source works
# alone, so it names no tooling around the repository either.
RELEASE_LANDING = re.compile(
    r"\bbranch(?:es)?\b|\b(?:feature|fix|chore)/|\bgh\b|\bmerg(?:e|es|ed|ing)\b(?! commit)"
    r"|\brulesets?\b|\breviewer\b|as the definition of done says|force-push|\bJohannes\b"
    r"|\bcoordinat|\bworkspace\b",
    re.I,
)


def test_release_prep_says_no_way_a_release_lands(variant: tuple[str, Path]) -> None:
    """``/release-prep`` names no branch, no GitHub CLI, no merge but the merge commit the
    release train tags, no reviewer, no person and nothing outside the repository, in every
    render."""
    _, dst = variant
    text = " ".join((dst / ".claude/commands/release-prep.md").read_text().split())
    found = [text[max(m.start() - 40, 0) : m.end() + 40] for m in RELEASE_LANDING.finditer(text)]
    assert not found, "\n".join(found)


def test_release_prep_assembles_the_fragments(keyed_nested: Path) -> None:
    """#130: the release's section takes the fragments under ``changelog/`` with what
    ``## [Unreleased]`` holds, as the rendered ``changelog/README.md`` lays it out."""
    text = " ".join((keyed_nested / ".claude/commands/release-prep.md").read_text().split())
    for name in ["`changelog/`", "`changelog/README.md`", "`## [Unreleased]`"]:
        assert name in text, name
    assert (keyed_nested / "changelog/README.md").is_file()


def test_release_prep_names_what_its_rows_add(variant: tuple[str, Path]) -> None:
    """The names each row's sentence brings: the pending publisher's project, the
    distribution's name in ``pyproject.toml`` (#72); the refresh that gets no pull request
    of its own while its records stay unchanged, ``fetched`` aside (#39); the live run over
    the release's base (#73); ``docs/handover.md`` only as sdk-core's file, which no render
    has (#75); and the update that takes a template release, in a file every source gets
    from the template (#120)."""
    _, dst = variant
    text = " ".join((dst / ".claude/commands/release-prep.md").read_text().split())
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["name"]
    assert f"project name `{project}`" in text, "#72"
    for name in ["`/refresh-reference-data`", "`fetched`"]:
        assert name in text, f"#39: {name}"
    assert "`live.yml`" in text, "#73"
    (local,) = [s for s in re.split(r"(?<=[.:;])\s", text) if "pytest -m live --tb=short" in s]
    assert 0 <= local.find("dispatch") < local.find("pytest -m live"), f"#73: {local}"
    sentences = [s for s in re.split(r"(?<=[.:;])\s", text) if "docs/handover.md" in s]
    assert sentences, "#75"
    assert all("sdk-core" in sentence for sentence in sentences), sentences
    assert not (dst / "docs/handover.md").exists(), "#75"
    assert "copier update --defaults --vcs-ref=<tag>`" in text, "#120"


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


# The commands a render has: the four that work on a source and /release-prep (#120 retired
# the sixth, since a template release is taken with one `copier update`).
RENDERED_COMMANDS = [
    "add-endpoint",
    "record-fixture",
    "refresh-reference-data",
    "refresh-upstream",
    "release-prep",
]
COMMAND_NAMED = re.compile(r"`/([a-z]+(?:-[a-z]+)*)[` ]")


def layout_commands(text: str) -> list[str]:
    """The commands a layout lists after ``.claude/commands/``, a trailing comma carrying
    the list onto the next line."""
    match = re.search(r"^\s*\.claude/commands/[ \t]+((?:[a-z-]+,\s*)*[a-z-]+)", text, re.M)
    assert match, "a layout line lists the commands"
    return re.split(r",\s*", match[1])


def test_every_command_points_at_the_process(keyless_flat: Path) -> None:
    """The definition of done and the review checklist, by URL, instead of repeated text."""
    commands = sorted((keyless_flat / ".claude/commands").glob("*.md"))
    assert [path.stem for path in commands] == RENDERED_COMMANDS, "#120"
    for path in commands:
        flat = " ".join(path.read_text().split())
        for doc in ["definition-of-done.md", "review-checklist.md"]:
            assert SDK_CORE_DOCS + doc in flat, f"{path.name}: {doc}"
        assert "../" not in flat, f"{path.name}: a relative path leaves a worktree"


def test_a_render_names_only_the_commands_it_has(variant: tuple[str, Path]) -> None:
    """#120: every ``/<command>`` a render's files name is one it has, and its
    ``CLAUDE.md`` lists them all in its layout, so a retired command leaves no mention."""
    _, dst = variant
    named: set[str] = set()
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            named |= set(COMMAND_NAMED.findall(path.read_text()))
    assert named <= set(RENDERED_COMMANDS), named - set(RENDERED_COMMANDS)
    assert sorted(layout_commands((dst / "CLAUDE.md").read_text())) == RENDERED_COMMANDS


def test_the_templates_own_files_list_the_rendered_commands() -> None:
    """#120: this README's generated tree and this CLAUDE.md's layout list the commands a
    render has, and neither names a command that neither renders nor this repository has."""
    own = {path.stem for path in (ROOT / ".claude/commands").glob("*.md")}
    for name in ["README.md", "CLAUDE.md"]:
        text = (ROOT / name).read_text()
        assert sorted(layout_commands(text)) == sorted(RENDERED_COMMANDS), name
        named = set(COMMAND_NAMED.findall(text))
        assert named <= set(RENDERED_COMMANDS) | own, f"{name}: {named}"


# What a repository's own Claude settings allow (#127, and the template's own file with
# them, #43): its checks and local git, a deny for what destroys work or reads a secret, and
# no push, no pull request and no merge, which Claude Code then asks the person about.
SETTINGS_CHECKS = {
    "Bash(uv run:*)",
    "Bash(git status:*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git add:*)",
    "Bash(git commit:*)",
}
SETTINGS_DENY = {
    "Bash(git push --force:*)",
    "Bash(git push -f:*)",
    "Bash(git reset --hard:*)",
    "Bash(rm -rf:*)",
    "Bash(gh secret:*)",
    "Read(**/.envrc)",
    "Read(**/.env)",
}


def test_the_settings_allow_no_way_to_a_pull_request(keyed_nested: Path) -> None:
    """A render's settings and this repository's allow the checks and local git and nothing
    that reaches GitHub, deny the same, and name no merge; this repository's allow its own
    proof beside the render's."""
    rendered = json.loads((keyed_nested / ".claude/settings.json").read_text())["permissions"]
    own = json.loads((ROOT / ".claude/settings.json").read_text())["permissions"]
    for name, rules in [("render", rendered), ("template", own)]:
        assert set(rules) == {"allow", "deny"}, name
        assert set(rules["allow"]) >= SETTINGS_CHECKS, name
        assert set(rules["deny"]) >= SETTINGS_DENY, name
        remote = [r for r in rules["allow"] if r.startswith(("Bash(git push", "Bash(gh "))]
        assert not remote, f"{name}: {remote}"
        assert not [r for r in rules["allow"] + rules["deny"] if "merge" in r], name
    assert own["deny"] == rendered["deny"], "one shape (#43)"
    assert set(own["allow"]) - set(rendered["allow"]) == {"Bash(scripts/prove.sh:*)"}
    assert set(rendered["allow"]) <= set(own["allow"])


# The four commands that work on a source (#126, the part of #114 on them) say how the work
# is done and checked, and nothing on how a change lands: no branch, no tool that opens a
# pull request, no merge and no pull request's body laid out. A source works alone, so they
# name no tooling around the repository either.
SOURCE_COMMANDS = [
    "add-endpoint.md",
    "record-fixture.md",
    "refresh-reference-data.md",
    "refresh-upstream.md",
]
LANDING = re.compile(
    r"\bbranch(?:es)?\b|\b(?:feature|fix|chore)/|docs/upstream-|\bgh\b|\bmerg(?:e|es|ing)\b"
    r"|as the definition of done says|\bcoordinat|\bworkspace\b",
    re.I,
)


def test_the_commands_on_a_source_say_no_way_a_change_lands(variant: tuple[str, Path]) -> None:
    """No line of the four commands names a branch, the GitHub CLI, a merge, the definition
    of done as a body to copy, or anything outside the repository, in every render."""
    _, dst = variant
    found = []
    for command in SOURCE_COMMANDS:
        lines = (dst / ".claude/commands" / command).read_text().splitlines()
        for number, line in enumerate(lines, 1):
            if LANDING.search(line):
                found.append(f"{command}:{number}: {line}")
    assert not found, "\n".join(found)


def test_the_commands_on_a_source_ask_for_a_changelog_fragment(keyed_nested: Path) -> None:
    """#130: a change that brings an entry brings it as a fragment under ``changelog/``, as
    the rendered ``changelog/README.md`` lays it out; no command asks for a line under
    Unreleased. A fixture rides with the task it tests, so ``/record-fixture`` asks none."""
    commands = keyed_nested / ".claude/commands"
    for command in SOURCE_COMMANDS:
        text = " ".join((commands / command).read_text().split())
        assert "Unreleased" not in text, command
        named = "`changelog/README.md`" in text and "`changelog/`" in text
        assert named is (command != "record-fixture.md"), command


def test_the_commands_name_wrappers_and_fixtures_as_the_conventions_do(
    keyed_nested: Path,
) -> None:
    """#48, conventions §2 and §10: a wrapper's module and function carry the operation's
    name, its verbatim id kept in ``endpoint=``, and a fixture lives under its wrapper's
    name, ``tests/fixtures/<wrapper>/<case>.json``, as ``/add-endpoint`` hands it on; the
    status table's cell follows what core's family check reads, a comment above the table
    being no part of every README."""
    commands = keyed_nested / ".claude/commands"
    add = " ".join((commands / "add-endpoint.md").read_text().split())
    record = " ".join((commands / "record-fixture.md").read_text().split())
    assert "/api/<wrapper>.py`" in add
    assert "`endpoint=`" in add
    assert "`/record-fixture <wrapper> <case> <parameters>`" in add
    assert "`tests/fixtures/<wrapper>/<case>.json`" in record
    assert '"<wrapper>", "<case>"' in record, "the recording script's fixture_path"
    for name, text in [("add-endpoint.md", add), ("record-fixture.md", record)]:
        assert "<endpoint>" not in text, name
        assert "<operation>.py" not in text, name
    assert "`## Status`" in add
    assert "`Task function`" in add


def test_add_endpoint_checks_the_samples_where_the_source_parses_files(
    variant: tuple[str, Path],
) -> None:
    """ADR-0020, conventions §10: the definition of done's checks of an endpoint hold its
    item for a source that parses files, a sample per file kind under
    ``tests/fixtures/files/<file_kind>/`` with its row in ``tests/fixtures/files/README.md``
    and one live parser test, exactly where ``has_files`` renders ``parse/``."""
    name, dst = variant
    add = " ".join((dst / ".claude/commands/add-endpoint.md").read_text().split())
    for path in ["`tests/fixtures/files/<file_kind>/`", "`tests/fixtures/files/README.md`"]:
        assert (path in add) is has_files(VARIANTS[name]), f"{name}: {path}"


def test_record_fixture_leaves_the_key_to_the_clients_refusal(variant: tuple[str, Path]) -> None:
    """#63: no step reads a key's variable, not even to test that it is set: the client
    refuses an unset key before it sends, with core's ``ConfigError`` naming the variable.
    A source without a key names neither."""
    name, dst = variant
    text = (dst / ".claude/commands/record-fixture.md").read_text()
    keys = key_envs(VARIANTS[name])
    for key in keys:
        assert f"`{key}`" in text, key
        assert f"${key}" not in text, key
        assert f"${{{key}}}" not in text, key
    assert ("`ConfigError`" in text) is bool(keys), name
    assert "[ -n " not in text


def test_the_commands_on_a_source_name_what_their_rows_add(keyed_nested: Path) -> None:
    """The names each row's sentence brings: the second case of a cap above the default,
    whose page keeps its ``next_token`` (#89, ADR-0016 as amended 2026-10-30), a module of
    the source's own beside the rendered tests that ``copier update`` leaves alone (#78), a
    second base's absolute URL (#59), and the fixtures a reference refresh records again,
    with ``fetched`` read from the packaged file (#70)."""
    commands = keyed_nested / ".claude/commands"
    add = " ".join((commands / "add-endpoint.md").read_text().split())
    record = " ".join((commands / "record-fixture.md").read_text().split())
    refresh = " ".join((commands / "refresh-reference-data.md").read_text().split())
    for name in ["`MCP_CAPS`", "`next_token`", "`tests/test_tasks.py`", "`copier update`"]:
        assert name in add, name
    assert "absolute URL" in record
    for name in ["`/record-fixture`", "`fetched`"]:
        assert name in refresh, name


def test_readme_status_table_has_the_columns_the_family_check_reads(keyless_flat: Path) -> None:
    """Core's family check reads the tables under ``## Status`` by their Task function column."""
    readme = (keyless_flat / "README.md").read_text()
    status = readme[readme.index("\n## Status\n") :]
    status = status[: status.index("\n## ", 1)]
    assert "| Upstream operation | Task function | MCP tool | Status |" in status


def test_the_files_a_source_fills_are_one_list(keyless_flat: Path) -> None:
    """The CLAUDE.md names every protected path, in skip order, where it says what a
    template release re-renders; a pattern anchored at the root by its slash is named
    without it."""
    names = [
        f"`{p.removeprefix('src/xippios/{{ package_dir }}/').lstrip('/').replace('/**', '/')}`"
        for p in QUESTIONS["_skip_if_exists"]
    ]
    listing = ", ".join(names[:-1]) + f" and {names[-1]}"
    assert names[-1] == "`CLAUDE.md`", "the facts are the source's"
    claude = (keyless_flat / "CLAUDE.md").read_text()
    assert listing in " ".join(claude.split())


# The render's .github/ (#129): a pull-request template that links sdk-core's definition of
# done where it copied it, the organization's checks called from a workflow of their own,
# and a changelog step that tells a release by no branch name. The live run's
# --assert=plain is pinned with its environment, the owners file's header with its rules.

PR_SECTIONS = ["## Summary", "## Checked", "## Assumptions", "## Decisions taken"]
# What the pull-request template of a repository that works alone leaves to that
# repository's rules: a branch, a tool that opens or merges a pull request, and the
# adoption pull request of the process before with the class that decided its merge.
PR_LANDING = re.compile(
    r"\bbranch(?:es)?\b|\b(?:feature|fix|chore)/|\bgh\b|\bmerg(?:e|es|ed|ing)\b"
    r"|\badoption\b|\bclass\b",
    re.I,
)


def test_the_pr_template_links_the_definition_of_done(keyed_nested: Path) -> None:
    """#107, #52, #82: the template's file, copied as it stands into every source, holds a
    summary, what was checked, the assumptions and the decisions taken, and links sdk-core's
    definition of done where it copied it, so no copy lags; it holds no checklist, names no
    way a change lands and nothing around the repository, and asks for the changelog entry
    as a fragment (#130)."""
    text = (keyed_nested / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
    assert text == (ROOT / "template/.github/PULL_REQUEST_TEMPLATE.md").read_text()
    assert [line for line in text.splitlines() if line.startswith("#")] == PR_SECTIONS
    flat = " ".join(text.split())
    assert SDK_CORE_DOCS + "definition-of-done.md" in flat
    assert "- [ ]" not in text, "no copy of the checklist"
    for pattern in [PR_LANDING, AROUND_THE_REPOSITORY]:
        assert not pattern.search(text), pattern.search(text)
    assert "`changelog/`" in flat
    assert "Unreleased" not in flat


# GitHub starts a caller on these: `edited` because the review reads the title and the
# description and a change of the base arrives as `edited`, `labeled` because a label set
# after the opening makes a release pull request (the README of xippios/.github).
ORG_TRIGGERS = {
    "pull_request": {"types": ["opened", "synchronize", "reopened", "edited", "labeled"]}
}


def test_the_organizations_checks_are_called_from_a_workflow_of_their_own(
    keyed_nested: Path,
) -> None:
    """#129: one workflow, the template's and copied as it stands, calls the organization's
    conventions review and its check of the ADR index as the jobs ``conventions`` and
    ``adr-index``. It reads by default, grants the review what it asks and passes it one
    secret by name; the index check takes no input and no secret and runs the repository's
    own script. It names nothing around the repository."""
    text = (keyed_nested / ".github/workflows" / ORG_CALLER).read_text()
    assert text == (ROOT / "template/.github/workflows" / ORG_CALLER).read_text()
    protected = skip_matcher(package_dir(VARIANTS["keyed-nested"]))
    assert not protected(f".github/workflows/{ORG_CALLER}"), "the template's, updated with it"
    workflow = yaml.safe_load(text)
    assert workflow[True] == ORG_TRIGGERS
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert list(jobs) == ["conventions", "adr-index"]
    review, index = jobs["conventions"], jobs["adr-index"]
    assert review["uses"] == ORG_WORKFLOW.format("conventions")
    asked = {"contents": "read", "pull-requests": "write", "checks": "read"}
    assert review["permissions"] == asked, "its one comment and the head's checks"
    assert review["secrets"] == {"ANTHROPIC_API_KEY": "${{ secrets.ANTHROPIC_API_KEY }}"}
    assert "github.event.label.name == 'release'" in review["if"], "a label: the release's"
    assert index["uses"] == ORG_WORKFLOW.format("adr-index")
    assert index["permissions"] == {"contents": "read"}
    assert index["if"] == "github.event.action != 'labeled'", "a label changes no record"
    for job in [review, index]:
        assert "with" not in job, "the callees take no input"
    assert "secrets" not in index
    assert text.count("secrets.") == 1, "one secret, by name, never inherited"
    assert (keyed_nested / ADR_SCRIPT).is_file(), "the script the index check runs"
    assert not AROUND_THE_REPOSITORY.search(text), AROUND_THE_REPOSITORY.search(text)


# The caller of the retired merge gates as the template rendered it up to v0.3.2, in its
# shape: one workflow of that name with two jobs.
RETIRED_CALLER = """name: gates

on:
  pull_request:

permissions:
  contents: read

jobs:
  merge-class:
    uses: ./.github/workflows/merge-class.yml
  family-review:
    uses: ./.github/workflows/family-review.yml
"""


def test_an_update_replaces_the_retired_caller(template_src: Path, tmp_path: Path) -> None:
    """A source made while the template rendered ``.github/workflows/gates.yml`` loses it at
    ``copier update``, since the template renders it no longer, and gets the caller of the
    organization's checks under a name of its own: GitHub keeps a workflow's state by its
    path, and the sources disabled the old one by hand, so the new one starts enabled."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    workflows = template / "template/.github/workflows"
    (workflows / ORG_CALLER).unlink(missing_ok=True)
    (workflows / "gates.yml").write_text(RETIRED_CALLER)
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "the retired caller")
    git(template, "tag", "v0.0.1")
    (workflows / "gates.yml").unlink()
    shutil.copytree(template_src, template, dirs_exist_ok=True)
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "the organization's checks")
    git(template, "tag", "v0.0.2")
    dst = tmp_path / "repo"
    answers = {**BASE_ANSWERS, **VARIANTS["keyless-flat"]}
    run_copy(str(template), str(dst), data=answers, defaults=True, vcs_ref="v0.0.1", quiet=True)
    assert (dst / ".github/workflows/gates.yml").read_text() == RETIRED_CALLER
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    assert not (dst / ".github/workflows/gates.yml").exists()
    rendered = dst / ".github/workflows" / ORG_CALLER
    assert rendered.read_bytes() == (workflows / ORG_CALLER).read_bytes()


def test_a_release_passes_the_changelog_step_by_its_changelog(
    keyed_nested: Path, tmp_path: Path
) -> None:
    """#136: the changelog step tells a release by no branch name. A release's pull request
    assembles the fragments into ``CHANGELOG.md`` and deletes them: it changes
    ``CHANGELOG.md``, adds no fragment, and passes, whatever its branch."""
    workflow = yaml.safe_load((keyed_nested / ".github/workflows/ci.yml").read_text())
    step = steps_of(workflow, "test")[1]
    assert step["if"] == CHANGELOG_STEP_RUNS
    repo = tmp_path / "source"
    (repo / "changelog").mkdir(parents=True)
    released = "# Changelog\n\n## [0.1.0] - 2026-01-01\n\n- The first release.\n"
    (repo / "CHANGELOG.md").write_text(released)
    (repo / "changelog/README.md").write_text("# Changelog fragments\n")
    (repo / "changelog/added-a-task.md").write_text("- A task.\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "-q", "-b", "the-next-version")
    (repo / "changelog/added-a-task.md").unlink()
    section = "## [0.2.0] - 2026-02-01\n\n### Added\n\n- A task.\n\n"
    (repo / "CHANGELOG.md").write_text(released.replace("## [0.1.0]", section + "## [0.1.0]"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "the release")
    run = pull_request_step(repo, step)
    assert (run.returncode, run.stdout, run.stderr) == (0, "", "")


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
    """uv reads main or a full SHA as one commit; nothing else."""
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


# A line at column 0 of an answers file: a plain key, a colon, then a blank or the end of
# the line.
ANSWER_LINE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*:(?:[ \t].*)?")


def test_answers_file_records_each_answer_on_one_line(variant: tuple[str, Path]) -> None:
    """The answers file's lines at column 0 are comments or plain ``key: value`` lines
    only, one per answer, as the README's question table says, and a question a source
    predates has a literal default, one scalar, which its update records.
    ``source_dependencies`` is a string holding a YAML flow list, so a list of dependencies
    never writes block lines there, and its default, the string ``[]``, is recorded as that
    one quoted scalar; ``gateway``'s default, ``none``, as one plain scalar."""
    name, dst = variant
    text = (dst / ".copier-answers.yml").read_text()
    for line in text.splitlines():
        if line and not line.startswith(("#", " ", "\t")):
            assert ANSWER_LINE.fullmatch(line), line
    question = QUESTIONS["source_dependencies"]
    assert (question["type"], question["default"]) == ("str", "[]")
    raw = (ROOT / "copier.yml").read_text().split("\nsource_dependencies:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert '\n  default: "[]"\n' in block, "one quoted scalar, a literal"
    if not dependencies(VARIANTS[name]):
        assert "\nsource_dependencies: '[]'\n" in text
    # The gateway answer, which every source before it lacks, is free at its default.
    assert (QUESTIONS["gateway"]["type"], QUESTIONS["gateway"]["default"]) == ("str", "none")
    raw = (ROOT / "copier.yml").read_text().split("\ngateway:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: none\n" in block, "one plain scalar, a literal"
    assert f"\ngateway: {gateway_of(VARIANTS[name])}\n" in text
    # has_files likewise: a bool whose default, false, is one plain scalar.
    assert (QUESTIONS["has_files"]["type"], QUESTIONS["has_files"]["default"]) == ("bool", False)
    raw = (ROOT / "copier.yml").read_text().split("\nhas_files:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: false\n" in block, "one plain scalar, a literal"
    assert f"\nhas_files: {str(has_files(VARIANTS[name])).lower()}\n" in text
    # live_secrets as source_dependencies: a string holding a YAML flow list, '[]' at default.
    question = QUESTIONS["live_secrets"]
    assert (question["type"], question["default"]) == ("str", "[]")
    raw = (ROOT / "copier.yml").read_text().split("\nlive_secrets:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert '\n  default: "[]"\n' in block, "one quoted scalar, a literal"
    assert "\nlive_secrets: '[]'\n" in text


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


@pytest.mark.parametrize("login", ["octo-cat", "a" * 39, "A1-b"])
def test_the_human_answer_owns_every_member_path(
    template_src: Path, tmp_path: Path, login: str
) -> None:
    """Another login renders as the owner of each path and is recorded as answered: a
    hyphen, the bound of 39 characters and mixed case among them."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", human=login, **keyed(""))
    assert owner_rules(dst) == [f"{path} @{login}" for path in MEMBER_HUMAN_PATHS]
    assert yaml.safe_load((dst / ".copier-answers.yml").read_text())["human"] == login


@pytest.mark.parametrize(
    "login", ["", "@jdidaskalu", "jd didaskalu", "-jdidaskalu", "jdidaskalu-", "jd--d", "a" * 40]
)
def test_the_human_is_a_github_login(template_src: Path, tmp_path: Path, login: str) -> None:
    """A GitHub login without the ``@``: letters, digits and single hyphens, neither first
    nor last, at most 39 characters; CODEOWNERS adds the ``@`` itself."""
    with pytest.raises(ValueError, match="human"):
        generate(template_src, tmp_path / "repo", source_slug="ex", human=login, **keyed(""))


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
    """An answers file is as copier writes it back, so an adoption that keeps the answers
    changes no line of it but ``_commit``.

    The test re-renders the template at ``_commit`` (by SHA) with the answers less
    ``_commit`` and ``_src_path`` as ``--data-file`` and compares the answers file byte for
    byte; a render from a tagged template must survive that.
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
    mine += ["tests/test_tasks.py", "tests/fixtures/files/README.md", "README.md", "CLAUDE.md"]
    mine += [*FILLED_SCRIPTS, *ADR_INDEX]
    templates = ["tests/conftest.py", f"{pkg}/mcp.py", ".github/CODEOWNERS"]
    templates += [".claude/settings.json", "changelog/README.md", *ADR_TEMPLATE_FILES]
    for rel in [*mine, *templates]:
        (dst / rel).write_text("# edited\n")
    generate(template_src, dst, **answers)
    for rel in mine:
        assert (dst / rel).read_text() == "# edited\n", f"{rel} is the source's"
    for rel in templates:
        assert (dst / rel).read_text() != "# edited\n", f"{rel} is the template's"


def test_an_update_brings_the_index_and_keeps_a_sources_scripts(
    template_src: Path, tmp_path: Path
) -> None:
    """A source made before ``docs/adr/``, by a template whose ``_skip_if_exists`` kept all
    of ``scripts/``, gets the folders, the index and its script at ``copier update``, the
    index current, while the scripts it filled and a script of its own stay as they were:
    the template names the two it renders for a source to fill, and renders no other."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    for rel in [ADR_SCRIPT, *ADR_INDEX, "docs/adr", "docs/reports"]:
        path = template / "template" / rel
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    config = (template / "copier.yml").read_text()
    filled = "".join(f"  - {rel}\n" for rel in FILLED_SCRIPTS)
    index = "".join(f"  - {rel}\n" for rel in ADR_INDEX)
    assert filled in config, "the two scripts a source fills, each by its name"
    assert index in config, "the index"
    config = config.replace(filled, "  - scripts/**\n").replace(index, "")
    (template / "copier.yml").write_text(config)
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "before the ADR folder")
    git(template, "tag", "v0.0.1")
    shutil.copytree(template_src, template, dirs_exist_ok=True)
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "the ADR folder")
    git(template, "tag", "v0.0.2")
    dst = tmp_path / "repo"
    answers = {**BASE_ANSWERS, **VARIANTS["keyless-flat"]}
    run_copy(str(template), str(dst), data=answers, defaults=True, vcs_ref="v0.0.1", quiet=True)
    assert not (dst / ADR_SCRIPT).exists()
    own = dict.fromkeys([*FILLED_SCRIPTS, "scripts/cut_sample.py"], "# the source's\n")
    for rel, text in own.items():
        (dst / rel).write_text(text)
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    for rel, text in own.items():
        assert (dst / rel).read_text() == text, f"{rel} is the source's"
    for rel in ADR_TEMPLATE_FILES:
        assert (dst / rel).read_bytes() == (template_src / "template" / rel).read_bytes(), rel
    run = adr_index(dst, "--check")
    assert run.returncode == 0, run.stdout


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


def new_source_functions() -> str:
    """new-source.sh's human_steps and write_body, as the script defines them."""
    script = (ROOT / "scripts/new-source.sh").read_text()
    start = script.index("human_steps() {")
    return script[start : script.index("\n}\n", script.index("write_body() {")) + 3]


def write_body(tmp_path: Path, pr_template: str) -> subprocess.CompletedProcess[str]:
    """new-source.sh's human_steps and write_body, run on a PR template and an answers file."""
    functions = new_source_functions()
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
        ("## Summary\n\n<!--", "## Summary\n\n-", 'a comment line under "## Summary"'),
        ("## Assumptions\n\n<!--", "## Assumptions\n\n-", 'a comment line under "## Assumptions"'),
    ],
)
def test_new_source_fills_the_pr_template_or_names_what_it_lacks(
    tmp_path: Path, old: str, new: str, missing: str
) -> None:
    """The scaffold PR's body: the PR template with its summary and its assumptions filled
    in; a PR template of another shape stops the script loudly, before anything is created
    on GitHub."""
    run = write_body(
        tmp_path, PR_TEMPLATE.read_text().replace(old, new) if old else PR_TEMPLATE.read_text()
    )
    if not missing:
        assert run.returncode == 0, run.stderr
        body = (tmp_path / "scratch/body.md").read_text()
        headings = [line for line in body.splitlines() if line.startswith("## ")]
        assert headings == PR_SECTIONS, "the PR template's sections, in its order"
        summary = body.split("## Summary\n", 1)[1].split("\n## ", 1)[0]
        assert "Scaffold of `xippios-ex`" in summary
        assert "  - `source_slug: ex`" in body
        assert "_commit" not in body
        return
    assert run.returncode == 1
    assert missing in run.stderr
    assert "Nothing was\ncreated on GitHub; /x/sdk-ex is generated and verified." in run.stderr


@pytest.mark.parametrize(
    ("location", "step"),
    [
        ("query", "2. The key, EX_API_KEY."),
        ("header", "2. The key, EX_API_KEY."),
        ("bearer", "2. The bearer token, EX_API_KEY."),
    ],
)
def test_new_source_names_the_credential_its_location_sends(location: str, step: str) -> None:
    """The human step for the secret names what the variable holds: a bearer answer's
    variable holds a token, not a key (#77)."""
    harness = (
        "set -euo pipefail\n"
        f"slug=ex api_key_env=EX_API_KEY api_key_location={location}\n"
        f"{new_source_functions()}\nhuman_steps\n"
    )
    run = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    (line,) = [line for line in run.stdout.splitlines() if line.startswith("2. ")]
    assert line.startswith(step), run.stdout


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


def test_no_workflow_calls_the_retired_gates() -> None:
    """The merge gates are retired and their reusable workflows are gone (#99): neither this
    repository nor a render carries a caller of them."""
    for workflows in [ROOT / ".github/workflows", ROOT / "template/.github/workflows"]:
        assert not (workflows / "gates.yml").exists(), workflows
        for path in sorted(workflows.iterdir()):
            assert "xippios/sdk-gates/" not in path.read_text(), path


def test_the_templates_own_workflows_are_hardened() -> None:
    """Conventions §13 for this repository's own workflows too: SHA pins with the version
    in a comment, ``contents: read`` at the top, and no checkout keeps its credentials but
    the one in a job that pushes, which says so."""
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for action, comment in workflow_uses(path):
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
    assert "template/CLAUDE.md.jinja" in scanned, "the generated instructions"


# The rule of the retired merge gates: a pull request's merge class, under any of its names
# (`human class`, `class review`), and the auto-merge a session enabled on one. A pull
# request merges under the rulesets of `main`.
MERGE_CLASS = re.compile(
    r"\bmerge[ -]class(?:es)?\b|\b(?:human|review) class\b|\bclass (?:human|review)\b"
    r"|\bauto-merge\b",
    re.I,
)


def test_no_instruction_names_the_merge_class() -> None:
    """This CLAUDE.md and every file the template renders name no merge class and no
    auto-merge; the workflows are core's files and are not read."""
    scanned = set()
    for path in [ROOT / "CLAUDE.md", *sorted((ROOT / "template").rglob("*"))]:
        if not path.is_file() or ".github/workflows" in path.as_posix():
            continue
        scanned.add(path.relative_to(ROOT).as_posix())
        for number, line in enumerate(path.read_text().splitlines(), 1):
            assert not MERGE_CLASS.search(line), f"{path.relative_to(ROOT)}:{number}: {line}"
    renders = {
        "CLAUDE.md",
        "template/.claude/commands/release-prep.md.jinja",
        "template/.github/PULL_REQUEST_TEMPLATE.md",
    }
    assert renders <= scanned, "the files that named it"


# The process before the migration, in the template's own files: the retired gates and
# their switch, the merge classes, the branch names and the PR body of that process, and
# the owners file of its coordination. The renders leave it in steps of their own.
RETIRED_PROCESS = re.compile(
    r"\bsdk-gates\b|\bGATES_CALLER\b|\bgates\.yml\b|\bmerge[ -]class(?:es)?\b"
    r"|\b(?:feature|fix|chore)/|\bdocs/<topic>|definition-of-done checklist"
    r"|as the definition of done says|\bowners\.toml\b",
    re.I,
)
OWN_FILES = ["copier.yml", "README.md", "CLAUDE.md", ".claude", "scripts", ".github"]


def test_the_templates_own_files_name_no_retired_process() -> None:
    """The template's own instructions, scripts and workflows name none of the process
    before the migration (#99); the CHANGELOG is history."""
    scanned, found = set(), []
    for name in OWN_FILES:
        root = ROOT / name
        for path in [root] if root.is_file() else sorted(root.rglob("*")):
            if not path.is_file():
                continue
            scanned.add(path.relative_to(ROOT).as_posix())
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if RETIRED_PROCESS.search(line):
                    found.append(f"{path.relative_to(ROOT)}:{number}: {line}")
    assert not found, "\n".join(found)
    named = {"CLAUDE.md", "README.md", "scripts/new-source.sh", ".claude/commands/new-source.md"}
    assert named <= scanned, "the files that named it"


# A release heading of CHANGELOG.md, as .github/workflows/release.yml finds the top one.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - ", re.M)


def test_the_manifest_names_the_latest_release() -> None:
    """The template's version is its latest release's: the release's pull request sets
    ``version`` in pyproject.toml with the CHANGELOG heading that release.yml tags, so a
    reader of the manifest bumps from the released version, never from 0.1.0 (#101). It
    locks again too: CI's ``uv sync --frozen`` passes on a lock that names the old one."""
    heading = RELEASE_HEADING.search((ROOT / "CHANGELOG.md").read_text())
    assert heading, "CHANGELOG.md has no release heading"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["version"] == heading[1]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    (locked,) = [p["version"] for p in lock["package"] if p["name"] == project["name"]]
    assert locked == project["version"], "uv.lock: run uv lock"
