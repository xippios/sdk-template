"""Generation tests: the family's variants render, pass ruff, and respect skip-if-exists.

Each variant renders once per session, by the fixtures of ``conftest.py`` from the answers
in ``helpers.py``; a check that differs between variants reads every render, a check no
answer changes reads one. The tests assert mechanics only: a file
rendered or not, a name present or absent, no Jinja left, a digest equal, a script's
behaviour. ``scripts/prove.sh`` proves that a render passes its own suite.
"""

import ast
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from copier import run_copy, run_update
from helpers import (
    BASE_ANSWERS,
    CI_STEPS,
    CORE_DEFAULT,
    FAKE_CORE_SHA,
    FETCH_DEPTH,
    GENERAL,
    KEY_AUTHS,
    LAYOUT_FILE,
    LIST_HELPERS,
    NEVER_FILE,
    PINNED,
    PUBLISH_STEP,
    QUESTIONS,
    RECORDER,
    RELEASE_SCRIPTS,
    ROOT,
    TASK_HELPERS,
    VARIANTS,
    dependencies,
    detect_secrets_hook,
    env_vars,
    generate,
    git,
    has_files,
    has_reference_data,
    key_answers,
    key_envs,
    keyed,
    kinds_unnamed,
    live_secrets,
    package_dir,
    ruff,
    skip_matcher,
    tenant_param,
    write_server,
)

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
    "scripts/changelog_assemble.py",
    "scripts/release_prepare.py",
    "docs/upstream/FETCHED.md",
    "docs/adr/README.md",
    "docs/adr.md",
    "docs/adr.json",
    "docs/reports/README.md",
    "docs/layout.md",
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
    ".github/workflows/conventions.yml",
    ".github/workflows/adr-index.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/CODEOWNERS",
    ".claude/settings.json",
    ".claude/rules/never.md",
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
# CLAUDE.md, the commands and sdk-core's documents state (#128). v0.4.1 renders a trigger file
# per check of the organization in place of the one caller of them all (#249).
REMOVED_FILES = [
    "tests/test_layout.py",
    "tests/test_adapters.py",
    "tests/test_tasks_write.py",
    "src/xippios/{pkg}/tasks_write.py",
    "src/xippios/{pkg}/mcp_write.py",
    ".github/workflows/gates.yml",
    ".github/workflows/organization.yml",
    ".claude/family.md",
]
# v0.4.0 renders the write server and its scaffold again, where write_server answers so
# (#174); tests/test_contract.py tests them and the entry points.
WRITE_SERVER_FILES = ["src/xippios/{pkg}/tasks_write.py", "src/xippios/{pkg}/mcp_write.py"]
FAMILY_TEST = "from xippios.core.testing.family import *  # noqa: F403\n"


# The checks every variant runs.

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json"}


def test_layout(variant: tuple[str, Path]) -> None:
    """Every file at the import path's directories, no ``__init__.py`` at a namespace level
    (sdk-core ADR-0006), none of the removed files, one read server and no core pin."""
    name, dst = variant
    answers = VARIANTS[name]
    pkg = package_dir(answers)
    for rel in [*(f"src/xippios/{pkg}/{part}" for part in PACKAGE_FILES), *REPOSITORY_FILES]:
        if has_reference_data(answers) or not re.search(r"params|enums|reference", rel):
            assert (dst / rel).is_file(), rel
    for rel in REMOVED_FILES:
        if not (write_server(answers) and rel in WRITE_SERVER_FILES):
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
    if not write_server(answers):
        expected_scripts = {f"xippios-{slug}-mcp": f"xippios.{dotted}.mcp:run"}
        assert pyproject["project"]["scripts"] == expected_scripts
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
    assert answers["api_key_env"] == key_answers(expected)["api_key_env"]
    assert answers["source_dependencies"] == expected.get("source_dependencies", "[]")
    assert yaml.safe_load(answers["source_dependencies"]) == dependencies(expected)
    assert answers["live_secrets"] == expected.get("live_secrets", "[]"), "the default included"
    assert yaml.safe_load(answers["live_secrets"]) == live_secrets(expected)
    assert answers["has_files"] is has_files(expected), "recorded, the default included"
    computed = ["package_dir", "tool_prefix", "live_schedule", "depends_on", "key_envs"]
    for derived in [*computed, "live_secret_names"]:
        assert derived not in answers, f"{derived}: derived, never recorded"
    for gone in ["source_pkg", "domain_topic", "needs_write_tools", *CLIENT_ANSWERS, *GONE]:
        assert gone not in answers, f"{gone}: no question asks it"


def test_no_jinja_left_behind(variant: tuple[str, Path]) -> None:
    """Workflow files carry GitHub's own ${{ }}, and the release scripts, copied verbatim,
    the braces an f-string doubles (#247); nothing else may, and nothing else in them."""
    _, dst = variant
    for path in dst.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text()
        rel = path.relative_to(dst).as_posix()
        assert "{%" not in text, path
        if ".github/workflows" in str(path):
            assert not re.search(r"(?<!\$)\{\{", text), f"{path}: only ${{{{ }}}} may remain"
        elif rel in RELEASE_SCRIPTS:
            assert path.read_bytes() == (ROOT / "template" / rel).read_bytes(), path
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
    """sdk-core ADR-0035: core's plugin pins the key it reads from ``ENV_VARS``, the keys of the
    source packages it depends on beside it (sdk-core ADR-0021), so neither the conftest nor
    ``pyproject.toml`` names a variable, and only a source with a key says so in its conftest's
    comment (row 61 d). No placeholder fixture, constant, list or test of the source's own."""
    name, dst = variant
    keys = key_envs(VARIANTS[name])
    conftest = (dst / "tests/conftest.py").read_text()
    code = [line for line in conftest.splitlines() if line and not line.startswith("#")]
    if tenant_param(VARIANTS[name]):  # the strip of the other tenants, test_contract.py's
        code = [line for line in code if "keep_reserved_tenants" not in line]
        code = [line for line in code if not line.startswith("from xippios.")]
    assert code == ['pytest_plugins = ["xippios.core.testing.plugin"]']
    assert ("ENV_VARS" in conftest) is bool(keys)
    assert "xippios_placeholder_key_envs" not in conftest
    ini = tomllib.loads((dst / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert "xippios_placeholder_key_envs" not in ini, "core's plugin reads ENV_VARS"
    assert "placeholder" not in (dst / "tests/test_tasks.py").read_text()


# The six answers that acted at generation alone, read by the scaffold's _client.py and
# CLAUDE.md, which no update renders again: a new source's first pull request fills the base
# URL, the auth and the pace, as it fills tasks.py (#301).
CLIENT_ANSWERS = [
    "api_base_url",
    "api_key_location",
    "api_key_name",
    "rate_limit_per_minute",
    "rate_limit_burst",
    "rate_limit_provenance",
]
# The three answers that one publisher, one source and one login needed, which leave the
# questions: the gateway goes to its publisher's shared package (#302), the credential of
# tenants without a key to the source's live_secrets, and the human is a constant (#301).
GONE = ["gateway", "tenant_credential_env", "human"]
# The scaffold's stand-ins in the place the source fills: a host that never resolves
# (RFC 6761), and the pace and burst that the questions took by default.
PLACEHOLDER_BASE_URL = 'BASE_URL = "https://example.invalid"\n'
PLACEHOLDER_PACE = "RATE_LIMIT = RateLimit(per_minute=60, burst=1)\n"


def test_no_question_asks_what_the_client_fills() -> None:
    """#301: no question asks the base URL, how the key is sent or the pace, nor a host, so
    a second host stays a constant of the source's own ``_client.py`` (#172)."""
    questions = [name for name in QUESTIONS if not name.startswith("_")]
    assert [name for name in CLIENT_ANSWERS if name in questions] == []
    hosts = [name for name in questions if "host" in name or ("url" in name and "base" in name)]
    assert hosts == []


def test_the_client_leaves_base_url_and_pace_to_the_source(variant: tuple[str, Path]) -> None:
    """#301, sdk-core ADR-0033 decision 1: the scaffold's ``_client.py`` holds a stand-in for
    the base URL and the pace, which the source's first pull request sets, and the facts of
    ``CLAUDE.md`` leave the base URL and the pace, with where it comes from, a comment each
    to fill; a quota's policy pointed at (sdk-core ADR-0037)."""
    name, dst = variant
    answers = VARIANTS[name]
    client = (dst / f"src/xippios/{package_dir(answers)}/_client.py").read_text()
    assert PLACEHOLDER_BASE_URL in client
    assert PLACEHOLDER_PACE in client
    assert "QuotaPolicy" in client
    claude = (dst / "CLAUDE.md").read_text().splitlines()
    for fact in ["API base URL", "Rate limit"]:
        (row,) = [line for line in claude if line.startswith(f"| {fact} | ")]
        assert row.startswith(f"| {fact} | <!-- "), row


def test_add_endpoint_states_one_limiter_per_host(variant: tuple[str, Path]) -> None:
    """#172, conventions §2 and §6: ``/add-endpoint`` states the rule in one paragraph, the
    one that names ``RateLimit``: it names ``_client.py``, where a second host's client and
    pace go, ``classify``, whose path checks name a second base on the first host,
    ``docs/upstream/``, which names a mirror's host beside its canonical one, and
    ``CLAUDE.md``, where the host's row goes. The rendered ``CLAUDE.md`` restates it no
    longer, since the conventions hold it (#300)."""
    name, dst = variant
    rel = ".claude/commands/add-endpoint.md"
    names = ["`_client.py`", "`classify`", "`docs/upstream/`", "`CLAUDE.md`"]
    (rule,) = [block for block in blocks((dst / rel).read_text()) if "`RateLimit`" in block]
    for named in ["conventions §2", "§6", *names]:
        assert named in rule, f"{name}: {rel}: {named}"
    assert "`RateLimit`" not in (dst / "CLAUDE.md").read_text(), name


def test_add_endpoint_names_the_layout_a_source_edits(keyed_nested: Path) -> None:
    """#233, #300: a service's module, where operation ids repeat across services, is laid
    out in ``docs/layout.md``, the file a source edits, which ``/add-endpoint`` names; no
    sentence of it places the Layout in ``CLAUDE.md``, which only imports the file."""
    text = " ".join((keyed_nested / ".claude/commands/add-endpoint.md").read_text().split())
    assert f"`{LAYOUT_FILE}`" in text
    assert "Layout in `CLAUDE.md`" not in text


def blocks(text: str) -> list[str]:
    """``text`` cut into its paragraphs, list items and numbered steps, whitespace folded."""
    parts = re.split(r"\n\s*\n|\n(?=\s*(?:- |\d+\. ))", text)
    return [" ".join(part.split()) for part in parts]


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


def test_no_question_asks_a_gateway_and_no_render_names_one(variant: tuple[str, Path]) -> None:
    """#302: the gateway question leaves with its branch, so no question asks for the
    gateway, the credential of tenants without a key or the human (#301), and no file of a
    render names ``xippios.core.data_gov``, its ``Gateway`` or api.data.gov: a source behind
    the gateway imports it from its publisher's shared package in a file of its own."""
    assert [name for name in GONE if name in QUESTIONS] == []
    _, dst = variant
    for path in sorted(dst.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text()
            named = [name for name in ["data_gov", "Gateway", "api.data.gov"] if name in text]
            assert not named, (path, named)


def test_core_dependency_is_one_minor(variant: tuple[str, Path]) -> None:
    """Conventions §12: one core minor, the extras likewise; a source package depended on
    bound to its minor the same way, ``~=X.Y.0`` (sdk-core ADR-0021), in no extra."""
    name, dst = variant
    assert CORE_DEFAULT == "0.5.0", "the core release the template adopts, its verbatim files'"
    version = str(VARIANTS[name].get("core_version", CORE_DEFAULT))
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]
    depended = [f"xippios-{d['name']}~={d['minor']}.0" for d in dependencies(VARIANTS[name])]
    assert project["dependencies"] == [f"xippios-core~={version}", *depended]
    assert project["optional-dependencies"] == {
        extra: [f"xippios-core[{extra}]~={version}"] for extra in ["mcp", "http", "testing"]
    }


def assert_the_isort_groups(dst: Path, answers: dict[str, object]) -> None:
    """#317: ruff's isort groups name the package's own import path first-party and core's and
    each dependency's third-party, a dependency's the slug with dots, as ``import_path``'s
    default, so ruff sorts a dependency's import with core's, never with the package's own."""
    own = "xippios." + package_dir(answers).replace("/", ".")
    depended = ["xippios." + d["name"].replace("-", ".") for d in dependencies(answers)]
    isort = tomllib.loads((dst / "pyproject.toml").read_text())["tool"]["ruff"]["lint"]["isort"]
    assert isort["known-first-party"] == [own]
    assert isort["known-third-party"] == ["xippios.core", *depended]
    third = "".join(f"import {name}\n" for name in sorted(["xippios.core", *depended]))
    probe = f"src/xippios/{package_dir(answers)}/probe.py"
    args = ("check", "--select", "I", "--stdin-filename", probe, "-")
    result = ruff(dst, *args, stdin=f"{third}\nimport {own}\n")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ruffs_isort_groups_name_each_dependency(variant: tuple[str, Path]) -> None:
    """#317: a source's render, nested with two dependencies or without one."""
    name, dst = variant
    assert_the_isort_groups(dst, VARIANTS[name])


def test_the_general_shapes_isort_groups_name_core(general: tuple[str, Path]) -> None:
    """#317: a render of the general shape without a dependency (ADR-0003)."""
    name, dst = general
    assert_the_isort_groups(dst, GENERAL[name])


@pytest.mark.parametrize("base", ["keyless-flat", "general-nested"])
def test_a_dependents_isort_groups_name_its_dependency(
    template_src: Path, tmp_path: Path, base: str
) -> None:
    """#317: a flat source with a dependency, and the general shape with one, whose
    ``pyproject.toml`` is the repository's once rendered."""
    answers = {**VARIANTS, **GENERAL}[base] | {"source_dependencies": DEPENDS_ON_BASE}
    dst = generate(template_src, tmp_path / "repo", **answers)
    assert_the_isort_groups(dst, answers)


FILES_TABLE = "| File | Release | URL | Bytes | sha256 | Fetched | Kept |"


def test_has_files_renders_the_parsers_and_the_samples_table(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0020: a source that parses the files it downloads gets ``parse/``, a package of
    one docstring, and ``tests/fixtures/files/README.md``, the samples' provenance table,
    both skip-listed, and its CLAUDE.md names them in a Files row; every other source
    renders none of it, a retrieval-only one included (row 57). This README's tree lays
    both out for every source that parses files (#300)."""
    name, dst = variant
    answers = VARIANTS[name]
    parses, pkg = has_files(answers), package_dir(answers)
    parse = dst / "src/xippios" / pkg / "parse"
    samples = dst / "tests/fixtures/files/README.md"
    assert parse.exists() is parses
    assert samples.exists() is parses
    claude = (dst / "CLAUDE.md").read_text().splitlines()
    assert len([line for line in claude if line.startswith("| Files | ")]) == parses
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
# The trigger files of the organization's checks (#249), each named as the workflow of
# xippios/.github it calls: their jobs call those at `@main`, the one reference to another
# repository that is not pinned (conventions §13).
TRIGGER_FILES = ["conventions.yml", "adr-index.yml"]
ORG_WORKFLOW = "xippios/.github/.github/workflows/{}.yml@main"


def test_workflow_actions_are_pinned_by_sha(variant: tuple[str, Path]) -> None:
    """ci.yml, publish.yml, live.yml and, where rendered, siblings.yml pin every action to a
    commit, its version in a comment (conventions §13); live.yml and siblings.yml take
    ci.yml's pins. The trigger files of the organization's checks call them at ``@main``."""
    _, dst = variant
    workflows = dst / ".github/workflows"
    rendered = sorted(path.name for path in workflows.glob("*.yml"))
    always = [*CORE_WORKFLOWS, *TRIGGER_FILES]
    assert rendered in [sorted(always), sorted([*always, "siblings.yml"])]
    for rel in rendered:
        uses = workflow_uses(workflows / rel)
        assert uses, rel
        for action, comment in uses:
            if action.startswith("./"):
                continue
            if rel in TRIGGER_FILES:
                assert re.fullmatch(r"xippios/\.github/\.github/workflows/[\w-]+\.yml@main", action)
                assert not comment, f"{rel}: {action}{comment}"
                continue
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"{rel}: {action}"
            assert re.fullmatch(r" # v\d+(\.\d+)*", comment), f"{rel}: {action}{comment}"
    for rel in set(rendered) & {"live.yml", "siblings.yml"}:
        assert set(workflow_uses(workflows / rel)) <= set(workflow_uses(workflows / "ci.yml"))


# A YAML comment opens a line or follows a blank; the one a workflow keeps is the version
# after a pinned action (https://github.com/xippios/.github/issues/111).
YAML_COMMENT = re.compile(r"(?:^|\s)#")
PINNED_USES = re.compile(r"\s+(?:- )?uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+(?:\.\d+)*")


def test_the_templates_workflows_carry_no_comment(variant: tuple[str, Path]) -> None:
    """https://github.com/xippios/.github/issues/111, #265: ``live.yml`` and, where it
    renders, ``siblings.yml``, the workflows that are the template's own, carry no comment
    but the version after a pinned action, whatever the answers; the README says what each
    checks, when it runs, what it is handed and what switches it. ``ci.yml`` and
    ``publish.yml`` keep sdk-core's bytes."""
    _, dst = variant
    workflows = dst / ".github/workflows"
    assert (workflows / "live.yml").is_file()
    for name in ["live.yml", "siblings.yml"]:
        path = workflows / name
        for line in path.read_text().splitlines() if path.is_file() else []:
            if YAML_COMMENT.search(line):
                assert PINNED_USES.fullmatch(line), f"{name}: {line}"


SIBLINGS_SCRIPT = (
    ROOT / "template/.github/{% if '.' in import_path or depends_on %}scripts{% endif %}"
)


def test_siblings_check_renders_where_the_import_path_nests(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0006's sibling proof is the template's (T10): siblings.yml and the script it
    runs render, byte for byte and executable, only where the import path nests or the source
    declares a source package it depends on (sdk-core ADR-0021), outside the skip-listed paths so
    that a source's copy is trusted when identical to the render; a visible job, `ci` never
    aggregates it (ci.yml stays core's)."""
    name, dst = variant
    answers = VARIANTS[name]
    rendered = "/" in package_dir(answers) or bool(dependencies(answers))
    assert (dst / ".github/workflows/siblings.yml").is_file() is rendered
    assert (dst / ".github/scripts").exists() is rendered, "no empty directory where flat"
    if rendered:
        assert_the_sibling_check(dst, package_dir(answers))


def test_a_flat_source_with_a_dependency_has_the_sibling_check(
    template_src: Path, tmp_path: Path
) -> None:
    """sdk-core ADR-0021: the check installs a declared dependency beside the wheel, so a flat
    source that declares one renders it too (sdk-eurostat's shape with a dependency)."""
    answers = {**VARIANTS["keyless-flat"], "source_dependencies": DEPENDS_ON_BASE}
    dst = generate(template_src, tmp_path / "repo", **answers)
    assert_the_sibling_check(dst, package_dir(answers))


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
    source has one, and the answer is recorded on one line at column 0, a quoted scalar.
    ``/record-fixture``'s step 1 names them beside the key, in the same order (#300)."""
    dst = generate(
        template_src,
        tmp_path / "repo",
        source_slug="ex",
        live_secrets=LIVE_SECRETS,
        **keyed(key),
    )
    assert_the_live_env(dst, [key] if key else [], ["A_B", "C_D"])
    assert f"\nlive_secrets: '{LIVE_SECRETS}'\n" in (dst / ".copier-answers.yml").read_text()
    named = [key] if key else []
    step = (dst / ".claude/commands/record-fixture.md").read_text().split("\n2. ")[0]
    assert "`" + "` and `".join([*named, "A_B", "C_D"]) + "`" in step


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
    """sdk-core ADR-0021 decision 5: a dependent releases after the packages it depends on, which
    /release-prep names in step 1 only where a dependency is declared, citing conventions §12,
    the section that holds the rule at core 0.5.0 (#300)."""
    name, dst = variant
    text = (dst / ".claude/commands/release-prep.md").read_text()
    depended = dependencies(VARIANTS[name])
    assert ("sdk-core ADR-0021 decision 5" in text) is bool(depended)
    for dependency in depended:
        assert f"`xippios-{dependency['name']}`" in text, dependency
    cited = [s for s in sentences(text) if "sdk-core ADR-0021 decision 5" in s]
    assert all("conventions §12" in s and "§15" not in s for s in cited), cited


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


def test_claude_md_holds_the_facts_and_imports_the_layout(variant: tuple[str, Path]) -> None:
    """The source's CLAUDE.md links the README's documents in its intro, names the Never
    file there, and imports one file, its layout (#128, #233), which names its own import
    path and the provider level where it nests; it says nothing of the key's ini option,
    which the conventions hold (#300), and holds a "Depends on" row naming each bound only
    where it declares a dependency (sdk-core ADR-0021)."""
    name, dst = variant
    answers = VARIANTS[name]
    slug, pkg = answers["source_slug"], package_dir(answers)
    claude = (dst / "CLAUDE.md").read_text()
    title, intro = claude.split("\n\n")[:2]
    assert title.startswith(f"# sdk-{slug} "), title
    assert intro.startswith(f"`xippios-{slug}`"), intro
    assert "(README.md#documents)" in intro, "the README's section, linked"
    assert f"`{NEVER_FILE}`" in intro, "named, never imported: Claude Code loads it"
    imports = [line for line in claude.splitlines() if line.startswith("@")]
    assert imports == [f"@{LAYOUT_FILE}"], "the layout alone"
    layout = (dst / LAYOUT_FILE).read_text()
    assert f"`xippios.{pkg.replace('/', '.')}`" in layout
    if "/" in pkg:
        assert f"`src/xippios/{pkg.rsplit('/', 1)[0]}/`" in layout, "the provider level"
    assert "xippios_placeholder_key_envs" not in claude, "the conventions' (#300)"
    rows = [line for line in claude.splitlines() if line.startswith("| Depends on | ")]
    depended = [f"`xippios-{d['name']}~={d['minor']}.0`" for d in dependencies(answers)]
    assert len(rows) == bool(depended)
    for bound in depended:
        assert bound in rows[0], bound
    assert "../" not in claude, "a relative path leaves the repository (worktree, GitHub)"
    assert len(claude) < 40_000, "Claude Code cuts a file that loads on demand"


def test_the_depends_on_row_says_what_each_kind_of_dependency_serves(
    render: Callable[[str], Path],
) -> None:
    """The answers do not tell a source package from a publisher's shared package, so the
    source's CLAUDE.md says what each kind serves in its "Depends on" row (#335): a source
    package's task layer by sdk-core ADR-0021 and a shared package's public names by sdk-core
    ADR-0065, decision 3, each kind with its record."""
    claude = (render("dependency") / "CLAUDE.md").read_text()
    (row,) = [line for line in claude.splitlines() if line.startswith("| Depends on | ")]
    assert kinds_unnamed(row) == [], row


def test_the_question_of_dependencies_names_each_kind() -> None:
    """The help of ``source_dependencies`` says what each kind of dependency serves, each kind
    with its record of sdk-core, as the "Depends on" row of a render does (#335)."""
    help_text = QUESTIONS["source_dependencies"]["help"]
    assert kinds_unnamed(help_text) == [], help_text


def test_generated_tree_names_no_source_and_no_workspace_file(variant: tuple[str, Path]) -> None:
    """Nothing source-specific is scaffolded (sdk-core ADR-0031), nor a workspace-local
    reference."""
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
    keyless render's trailing brace). The packages depended on are named (sdk-core ADR-0021)."""
    name, dst = variant
    readme = (dst / "README.md").read_text()
    block = readme.split("```json\n", 1)[1].split("```", 1)[0]
    (server,) = json.loads(block)["mcpServers"].values()
    names = [entry[0].replace("<NAME>", "ACME") for entry in env_vars(VARIANTS[name])]
    assert list(server.get("env", {})) == names
    for dependency in dependencies(VARIANTS[name]):
        assert f"`xippios-{dependency['name']}`" in readme
    (args,) = [line for line in block.splitlines() if '"args"' in line]
    assert args.rstrip().endswith(("]", "],")), args


# The render's documents and instructions (#128). The README lists the repository's
# documents under `## Documents`, each by its file on GitHub, and links nothing relative,
# since PyPI shows it with no repository around it. The CLAUDE.md links that section instead
# of repeating it, says what the package wraps, its commands and its specifics, imports its
# layout and states no rule the conventions hold (#300), and names nothing around the
# repository, nor does its layout or any file under .claude/, the Never file among them.
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
SECRET_SUFFIXES = ["`_API_KEY`", "`_TOKEN`", "`_SECRET`"]
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


def secrecy_rule(never: str) -> str:
    """The rule of the Never file on what is never read or printed, its lines joined."""
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
    """The CLAUDE.md, its layout and every file under ``.claude/`` name no tooling, session,
    claim, numbered rule or pull request's class around the repository, and what a session
    loads at launch, the CLAUDE.md, the layout it imports and the Never file, no branch, no
    GitHub CLI, no merge, no reviewer and no person; no ``.claude/family.md`` is left."""
    _, dst = variant
    found = []
    claude = dst / "CLAUDE.md"
    loaded = [claude, dst / LAYOUT_FILE, dst / NEVER_FILE]
    paths = [*loaded[:2], *sorted(p for p in (dst / ".claude").rglob("*") if p.is_file())]
    assert loaded[2] in paths, "the Never file stands under .claude/"
    for path in paths:
        patterns = [AROUND, CHANGE_LANDING] if path in loaded else [AROUND]
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
    """#82, #169: the Never file's secrecy rule names each credential variable of the source,
    its keys and its dependencies' (none in a keyless render), and the endings of every other
    credential's variable that sdk-core's conventions §7 and review checklist name."""
    name, dst = variant
    rule = secrecy_rule((dst / NEVER_FILE).read_text())
    for variable in [*key_envs(VARIANTS[name]), *live_secrets(VARIANTS[name])]:
        assert f"`{variable}`" in rule, variable
    for suffix in SECRET_SUFFIXES:
        assert suffix in rule, suffix


# The pattern of the tenants' keys in a secrecy rule, `<PREFIX>_<NAME>_<FIELD>`.
TENANT_PATTERN = re.compile(r"`[A-Z0-9_]+_<NAME>_[A-Z0-9_]+`")


@pytest.mark.parametrize("key", ["", "EX_API_KEY"])
def test_the_secrecy_rule_names_the_tenants_pattern_only_with_their_key(
    template_src: Path, tmp_path: Path, key: str
) -> None:
    """#301: the tenants' variables derive from the key answer alone, so the Never file's
    secrecy rule names the pattern ``<PREFIX>_<NAME>_API_KEY`` only where the tenants hold the
    key. A multi-tenant source whose tenants hold another credential answers no key, and the
    template knows no variable of its tenants: its rule names none, the file being the
    template's, which the source cannot correct, and names its live secrets beside the
    endings ``_API_KEY``, ``_TOKEN`` and ``_SECRET``, which cover the rest."""
    dst = generate(
        template_src,
        tmp_path / "repo",
        source_slug="ex",
        tenant_param="org",
        has_reference_data=False,
        live_secrets=LIVE_SECRETS,
        **keyed(key),
    )
    rule = secrecy_rule((dst / NEVER_FILE).read_text())
    assert TENANT_PATTERN.findall(rule) == (["`EX_<NAME>_API_KEY`"] if key else [])
    for name in ["A_B", "C_D"]:
        assert f"`{name}`" in rule, name
    for suffix in SECRET_SUFFIXES:
        assert suffix in rule, suffix


@pytest.mark.parametrize("key", ["", "EX_API_KEY"])
def test_claude_md_names_the_live_secrets(template_src: Path, tmp_path: Path, key: str) -> None:
    """#108, #82: the variables ``live_secrets`` names stand in the live run's paragraph of
    the CLAUDE.md after the key, in the answer's order, and in the Never file's secrecy rule
    beside the key."""
    dst = generate(
        template_src,
        tmp_path / "repo",
        source_slug="ex",
        live_secrets=LIVE_SECRETS,
        **keyed(key),
    )
    claude = (dst / "CLAUDE.md").read_text()
    names = [*([key] if key else []), "A_B", "C_D"]
    rule = secrecy_rule((dst / NEVER_FILE).read_text())
    (live,) = [p for p in claude.split("\n\n") if p.startswith("`.github/workflows/live.yml`")]
    live = " ".join(live.split())
    for name in names:
        assert f"`{name}`" in rule, name
    places = [live.find(f"`{name}`") for name in names]
    assert -1 not in places, live
    assert places == sorted(places), "the keys first, then the answer's order"


def claude_section(claude: str, heading: str) -> str:
    """The text of a CLAUDE.md's ``## <heading>``, up to the next heading."""
    return claude.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def readme_tree() -> str:
    """The tree of the family's files under this README's ``## What gets generated``."""
    readme = (ROOT / "README.md").read_text()
    return readme.split("\n## What gets generated\n", 1)[1].split("```", 2)[1]


def test_this_readme_lays_out_every_file_a_render_holds(variant: tuple[str, Path]) -> None:
    """#300, #135, #145: the family's files are described once, in this README's tree, so
    each file a render holds stands there by its name, a command by its own, the decisions'
    and the changelog's files, the release scripts, every workflow, the Never file and the
    layout among them; the render describes them nowhere (#233)."""
    _, dst = variant
    tree = readme_tree()
    caches = {".ruff_cache", "__pycache__"}
    missing = []
    for path in sorted(dst.rglob("*")):
        rel = path.relative_to(dst)
        if not path.is_file() or caches & set(rel.parts):
            continue
        name = path.stem if rel.parent.as_posix() == ".claude/commands" else path.name
        if not re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", tree):
            missing.append(rel.as_posix())
    assert missing == []


# The sections a render's CLAUDE.md keeps, in their order, before the source's specifics:
# the rules of `## Code rules`, `## When something is unclear` and `## Never` are the
# conventions', the last in the Never file (#300).
CLAUDE_SECTIONS = ["What this package wraps", "Layout", "Commands", "Template updates"]
# The names the offline paragraphs of `## Commands` gave the plugin, which conventions §10
# and sdk-core ADR-0035 hold.
OFFLINE_NAMES = ["`rate_limited`", "`network`", "xippios_placeholder_key_envs"]
COPIER_YML = "https://github.com/xippios/sdk-template/blob/main/copier.yml"
TEMPLATE_TREE = "https://github.com/xippios/sdk-template/blob/main/README.md#what-gets-generated"


def test_claude_md_restates_no_rule_the_conventions_hold(variant: tuple[str, Path]) -> None:
    """#300: the rendered CLAUDE.md keeps what the package wraps, its layout, its commands,
    how a template release reaches it and its specifics, in that order. ``## Code rules``,
    ``## When something is unclear`` and ``## Never`` leave it, and so do the offline
    paragraphs of ``## Commands``, with the plugin's names, and the two file lists of
    ``## Template updates``: the section names ``_skip_if_exists`` of the template's
    ``copier.yml``, linked, and none of the paths it holds, nor a list of the files an
    update writes again."""
    name, dst = variant
    pkg = package_dir(VARIANTS[name])
    claude = (dst / "CLAUDE.md").read_text()
    headings = [line[3:] for line in claude.splitlines() if line.startswith("## ")]
    assert headings[:-1] == CLAUDE_SECTIONS, headings
    assert headings[-1].endswith(" specifics"), headings
    commands = claude_section(claude, "Commands")
    assert [offline for offline in OFFLINE_NAMES if offline in commands] == []
    updates = " ".join(claude_section(claude, "Template updates").split())
    assert "`_skip_if_exists`" in updates
    assert f"({COPIER_YML})" in updates, "the list stands in the template's questions"
    spans = set(re.findall(r"`([^`]+)`", updates))
    protected = {
        p.removeprefix("src/xippios/{{ package_dir }}/").lstrip("/").replace("/**", "/")
        for p in QUESTIONS["_skip_if_exists"]
    }
    assert sorted(spans & protected) == [], "the files a source fills"
    package = dst / "src/xippios" / pkg
    rendered = [s for s in spans if (dst / s).is_file() or (package / s).is_file()]
    assert len(rendered) <= 4, f"no list of the files an update writes again: {rendered}"


def test_the_never_file_is_the_templates_and_loads_by_its_place(variant: tuple[str, Path]) -> None:
    """#300: the nine rules of the former ``## Never`` stand in ``.claude/rules/never.md``,
    the template's file, which every update writes again. Claude Code loads each markdown
    file of ``.claude/rules/`` that has no ``paths`` frontmatter at launch, with the
    priority of ``.claude/CLAUDE.md``, so no line of the source's CLAUDE.md, which no update
    writes, imports it: the CLAUDE.md names it, and the test above holds that it imports the
    layout alone."""
    name, dst = variant
    never = (dst / NEVER_FILE).read_text()
    assert never.split("\n\n", 1)[0] == "# Never", "a title, no frontmatter"
    rules = never.split("\n- ")[1:]
    assert len(rules) == 9, rules
    assert [rule for rule in rules if not rule.startswith("Never ")] == []
    assert not [line for line in never.splitlines() if line.startswith("@")], "no import"
    assert not skip_matcher(package_dir(VARIANTS[name]))(NEVER_FILE), "the template's"


def test_the_layout_is_the_sources_and_holds_no_family_tree(variant: tuple[str, Path]) -> None:
    """#233, #300: ``docs/layout.md``, which the CLAUDE.md imports, is the source's once
    rendered, so an update creates it where the repository has none and never writes it
    again, and holds what the source adds to the family's tree: a render, which has added
    nothing, holds no tree, links this README's tree of the family's files and imports
    nothing, and the CLAUDE.md's Layout holds no tree either."""
    name, dst = variant
    assert skip_matcher(package_dir(VARIANTS[name]))(LAYOUT_FILE), "the source's"
    layout = (dst / LAYOUT_FILE).read_text()
    assert layout.startswith("# "), "a title, no frontmatter"
    assert TEMPLATE_TREE in " ".join(layout.split())
    assert "```" not in layout, "the family's tree stands in the template's README"
    assert not [line for line in layout.splitlines() if line.startswith("@")], "no import"
    assert "```" not in claude_section((dst / "CLAUDE.md").read_text(), "Layout")


def test_claude_md_takes_a_release_with_copier(keyed_nested: Path) -> None:
    """#130: a template release is taken with one ``copier update`` at its tag. The rule
    on a change's changelog fragment is conventions §12's and the pull-request template's,
    which the CLAUDE.md restates no longer (#300)."""
    claude = " ".join((keyed_nested / "CLAUDE.md").read_text().split())
    command = "`uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=<tag>`"
    assert command in claude
    assert "`changelog/README.md`" not in claude


def commit_rule(claude: str) -> str:
    """The sentence of a CLAUDE.md that names Conventional Commits, its lines joined."""
    flat = " ".join(claude.split())
    (rule,) = [s for s in re.split(r"(?<=\.) ", flat) if "Conventional Commits" in s]
    return rule


def test_the_templates_claude_md_says_which_commits_follow_conventional_commits(
    keyed_nested: Path,
) -> None:
    """#149: the rule on Conventional Commits binds a pull request's own commits, and the
    template's CLAUDE.md says so where it states it. A render states the rule in no file
    that Claude Code loads, since conventions §13 holds it (#300)."""
    assert "a pull request's own commits" in commit_rule((ROOT / "CLAUDE.md").read_text())
    for rel in ["CLAUDE.md", LAYOUT_FILE, NEVER_FILE]:
        assert "Conventional Commits" not in (keyed_nested / rel).read_text(), rel


# A citation of a decision record by its bare number, which a source keeps for its own.
BARE_ADR = re.compile(r"(?<!sdk-core )\bADR-\d{4}\b")


def test_the_render_cites_sdk_cores_records_as_sdk_cores(variant: tuple[str, Path]) -> None:
    """#152: a source cites its own records as ``ADR-NNNN`` (its ``docs/adr/README.md``), so
    its CLAUDE.md, its layout, its Never file and its README cite each of sdk-core's as
    ``sdk-core ADR-NNNN``."""
    _, dst = variant
    assert "cited as `ADR-NNNN`" in " ".join((dst / "docs/adr/README.md").read_text().split())
    for rel in ["CLAUDE.md", LAYOUT_FILE, NEVER_FILE, "README.md"]:
        flat = " ".join((dst / rel).read_text().split())
        assert BARE_ADR.findall(flat) == [], rel
    never = " ".join((dst / NEVER_FILE).read_text().split())
    assert "sdk-core ADR-0001" in never, "the adapters register the tasks"


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


# The paths that steer a source, in the order the rendered .github/CODEOWNERS lists them; a
# source's one manifest is pyproject.toml. No `/rules/**`, a path no source has (#152).
MEMBER_HUMAN_PATHS = [
    "/.github/**",
    "/CLAUDE.md",
    "/.claude/**",
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
    """#301: a source's ``.github/CODEOWNERS`` is the template's file, copied as it stands:
    a header of comments that says what the file is and names each path it owns, and no
    tool, rule or file around the repository (#129), then the five paths that steer it,
    each owned by the human, ``jdidaskalu``, a constant that no question asks. It names no
    ``rules/``, which no source has (#152)."""
    _, dst = variant
    assert "human" not in QUESTIONS
    source = ROOT / "template/.github/CODEOWNERS"
    assert (dst / ".github/CODEOWNERS").read_bytes() == source.read_bytes()
    rules = owner_rules(dst)
    assert rules == [f"{path} @{HUMAN}" for path in MEMBER_HUMAN_PATHS]
    lines = source.read_text().splitlines()
    head = lines[: lines.index(rules[0])]
    assert head, "a header"
    assert all(line.startswith("#") for line in head), "the header, then the rules"
    header = " ".join(head)
    assert not AROUND_THE_REPOSITORY.search(header), AROUND_THE_REPOSITORY.search(header)
    for path in MEMBER_HUMAN_PATHS:
        name = path.removeprefix("/").removesuffix("**")
        assert f"`{name}`" in header, f"the header names {name}"
    assert "rules/" not in header


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
# The one version of the script that the organization's repositories carry byte for byte
# (#246): a copy edited here would write another index than theirs, and the organization's
# check adr-index runs each repository's own copy. Its next version changes this digest.
# pragma: allowlist nextline secret
ADR_SCRIPT_SHA256 = "14f262d22cafd2ff92d4bbcce6e8f51143774d1f35e6c56890ef825261f63cab"
# A line of docs/adr.md that lists a record opens with the anchor a citation links to,
# docs/adr.md#0014 for ADR-0014.
ADR_LINE = re.compile(r'^- <a id="(\d{4})"></a>\[ADR-\1\]\(adr/\1-.+\.md\): ')


def adr_lines(repo: Path) -> list[str]:
    """The lines of ``repo``'s ``docs/adr.md`` that list a record, in their order."""
    text = (repo / "docs/adr.md").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.startswith("- ")]


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


def test_the_index_anchors_each_record_and_lists_the_superseded_last(
    keyed_nested: Path, tmp_path: Path
) -> None:
    """#246: each line of ``docs/adr.md`` that the rendered script writes opens with its
    record's anchor, ``<a id="NNNN"></a>``, so ``docs/adr.md#NNNN`` lands on the record; the
    records in force come first, each part in the order of its number, and ``docs/adr.json``
    keeps the order of the numbers."""
    repo = tmp_path / "repo"
    for rel in [ADR_SCRIPT, *ADR_INDEX, "docs/adr/README.md"]:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(keyed_nested / rel, repo / rel)
    statuses = {
        "0001-first.md": "Superseded by ADR-0003 · Date: 2026-11-01",
        "0002-second.md": "Accepted · Date: 2026-11-02",
        "0003-third.md": "Accepted · Date: 2026-11-03 · Supersedes ADR-0001",
    }
    for name, status in statuses.items():
        title = f"# ADR-{name[:4]}: Record {name[:4]}"
        (repo / "docs/adr" / name).write_text(f"{title}\n\nStatus: {status}\n\n## Context\n")
    assert adr_index(repo).returncode == 0
    lines = adr_lines(repo)
    anchors = [found.group(1) for line in lines if (found := ADR_LINE.match(line))]
    assert len(anchors) == len(lines), lines
    assert anchors == ["0002", "0003", "0001"], "in force first, then the superseded"
    records = json.loads((repo / "docs/adr.json").read_text())["records"]
    assert [r["id"] for r in records] == ["ADR-0001", "ADR-0002", "ADR-0003"]
    assert adr_index(repo, "--check").returncode == 0


def test_the_index_script_is_the_organizations_one_version() -> None:
    """#246: this repository's script and the one it renders are the bytes that the
    organization's repositories share, executable, and the ruff of both leaves the file alone
    (https://github.com/xippios/sdk-core/issues/357)."""
    for path in [ROOT / ADR_SCRIPT, ROOT / "template" / ADR_SCRIPT]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == ADR_SCRIPT_SHA256, path
        assert os.access(path, os.X_OK), path
    ruff_here = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["ruff"]
    assert ADR_SCRIPT in ruff_here["extend-exclude"]


def test_pyproject_tooling(keyed_nested: Path) -> None:
    """mypy covers scripts/, the index script and the release scripts among them, which ruff
    leaves alone (#246, #247); record_property raises no warning; the sdist ships no tests."""
    tool = tomllib.loads((keyed_nested / "pyproject.toml").read_text())["tool"]
    assert tool["mypy"]["files"] == ["src", "tests", "scripts"]
    assert tool["ruff"]["extend-exclude"] == ["docs", ".claude", ADR_SCRIPT, *RELEASE_SCRIPTS]
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


def test_upstream_snapshot_is_kept_byte_for_byte(keyed_nested: Path) -> None:
    """Git never converts line endings under docs/upstream/: upstream files may carry CRLF."""
    assert (keyed_nested / ".gitattributes").read_text() == "docs/upstream/** -text\n"


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
    """sdk-core ADR-0038: per-tool caps live next to the tasks as MCP_CAPS; core reads them
    from the tasks module (sdk-core ADR-0063, decision 7). sdk-core ADR-0040 decision 4:
    beside them ``BULK_TASKS``, empty in the scaffold, names the Python-only tasks; the
    adapters pass ``tool_functions(tasks)``, which skips those names (row 64)."""
    pkg = keyed_nested / "src/xippios" / package_dir(VARIANTS["keyed-nested"])
    assert "ToolSet.from_tasks(SOURCE, tasks," in (pkg / "mcp.py").read_text()
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
    assert "tool_functions(tasks)" in (pkg / "http.py").read_text(), "the list mcp.py serves"
    mcp = (pkg / "mcp.py").read_text()
    assert "getattr(" not in mcp, "core reads the tasks module (sdk-core ADR-0063)"
    assert "tenant_lock" not in mcp, "core 0.3.0's build_server has none"


@pytest.mark.parametrize("name", ["keyed-nested", "keyless-flat"])
def test_the_live_tests_hold_no_probe_of_the_base_url(
    name: str, render: Callable[[str], Path]
) -> None:
    """sdk-core#477: the live probe of upstream's base URL leaves the scaffold with its two
    imports, ``httpx`` and the client's ``BASE_URL`` and ``config``, since core's family
    check and each task's smoke test hold what it held."""
    live = ast.parse((render(name) / "tests/test_live.py").read_text())
    functions = [n.name for n in live.body if isinstance(n, ast.AsyncFunctionDef | ast.FunctionDef)]
    assert functions == []
    modules = {n.module for n in live.body if isinstance(n, ast.ImportFrom)}
    plain = {alias.name for n in live.body if isinstance(n, ast.Import) for alias in n.names}
    assert "httpx" not in plain
    assert not {m for m in modules if m and m.endswith("._client")}


# SHA-256 of sdk-core's files the template departs from, at its tag v0.5.0, the core release
# the template adopts: git -C <workspace root>/sdk-core show v0.5.0:<path> | sha256sum
# (digests, not secrets). A render is core's bytes once the
# template's own lines, named in CLAUDE.md's Rules, are taken out. Core's gates.yml is no
# file of the template's (#99), and the PR template links core's definition of done where it
# copied it (#129). The files a render copies whole are pinned in test_core_adoption.py.
CORE_EXTENDED = {
    # pragma: allowlist nextline secret
    ".github/workflows/ci.yml": "152473f8f17f61b7e137da200c0afc5355261b335b6a3e684bb82a8c217deaf2",
    ".github/workflows/publish.yml": (
        # pragma: allowlist nextline secret
        "1063f6ac5d6c6841e3bd78b9fd9302da12c4942f62c548c2c7185083e900c80c"
    ),
}


def without(text: str, first: str, stop: str) -> str:
    """``text`` without the lines from the one starting ``first`` up to ``stop``."""
    start = text.index(first)
    return text[:start] + text[text.index(stop, start) :]


def test_workflows_are_cores_bytes(keyed_nested: Path) -> None:
    """ci.yml and publish.yml are core's plus ours, and neither carries a comment but the
    version after a pinned action, as core's bytes carry none (conventions §13, #312)."""
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
    for text in [ci, publish]:
        comments = [
            line
            for line in text.splitlines()
            if line.lstrip().startswith("#") or (" # " in line and "uses: " not in line)
        ]
        assert comments == [], comments


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
    assert cap["env"] == {"BASE": "${{ github.base_ref }}"}, "no LEVEL: an error since v0.3.0"
    assert "::error file=" in cap["run"], "the cap binds a source (sdk-core ADR-0040)"
    assert "git diff -z --name-only --find-renames=100% --diff-filter=AM" in cap["run"]
    assert "--no-renames" not in cap["run"], "a pure move adds and changes no fixture"
    assert "262144" in cap["run"]


CAP = 262144  # 256 KiB, sdk-core ADR-0040


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
    """sdk-core ADR-0040 caps the fixture files a pull request adds or changes. A pure ``git mv`` of
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
    over = (
        "::error file=tests/fixtures/get_new/{}::{} bytes,"
        " over the 256 KiB cap (sdk-core ADR-0040)\n"
    )
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
    lines = adr_lines(ROOT)
    assert lines, "the template keeps a record"
    assert all(ADR_LINE.match(line) for line in lines), "each line opens with its anchor (#246)"


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
    from the template (#120). A render without reference data, a multi-tenant one (#301),
    names no refresh."""
    name, dst = variant
    text = " ".join((dst / ".claude/commands/release-prep.md").read_text().split())
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["name"]
    assert f"project name `{project}`" in text, "#72"
    for named in ["`/refresh-reference-data`", "`fetched`"]:
        assert (named in text) is has_reference_data(VARIANTS[name]), f"#39: {named}"
    assert "`live.yml`" in text, "#73"
    (local,) = [s for s in re.split(r"(?<=[.:;])\s", text) if "pytest -m live --tb=short" in s]
    assert 0 <= local.find("dispatch") < local.find("pytest -m live"), f"#73: {local}"
    sentences = [s for s in re.split(r"(?<=[.:;])\s", text) if "docs/handover.md" in s]
    assert sentences, "#75"
    assert all("sdk-core" in sentence for sentence in sentences), sentences
    assert not (dst / "docs/handover.md").exists(), "#75"
    assert "copier update --defaults --vcs-ref=<tag>`" in text, "#120"


# The line that xippios-core's testing plugin prints after a run of the live tests, from core
# 0.4.1 on (sdk-core#335, `_LiveRequests.line` in xippios/core/testing/plugin.py): the count
# of the requests the run sent, which a release cites (#237).
LIVE_COUNT = "`requests sent by the live run: <n>`"

# What an adoption's changelog entry names as it stands after the adoption, changed or not
# (conventions §15 item 9, sdk-core#355).
ITEM_9 = ["core bound", "template's tag", "conventions' version"]


def sentences(text: str) -> list[str]:
    """``text``, its whitespace joined, cut after each full stop that ends a sentence."""
    return re.split(r"(?<=\.)\s", " ".join(text.split()))


def test_release_prep_cites_the_count_that_core_prints(variant: tuple[str, Path]) -> None:
    """#237: ``/release-prep`` takes the count of the live run's requests from the line that
    core's testing plugin prints in the log of ``live.yml``, and the header of
    ``tests/test_live.py`` points to that line and the command."""
    _, dst = variant
    text = (dst / ".claude/commands/release-prep.md").read_text()
    (count,) = [s for s in sentences(text) if LIVE_COUNT in s]
    assert "`live.yml`" in count, count
    header = ast.get_docstring(ast.parse((dst / "tests/test_live.py").read_text()))
    assert header is not None
    flat = " ".join(header.split())
    assert LIVE_COUNT.replace("`", "``") in flat
    assert "``/release-prep``" in flat


def test_an_adoptions_entry_names_the_three_versions(variant: tuple[str, Path]) -> None:
    """#251, sdk-core#355: wherever the render cites conventions §15 item 9, in
    ``/release-prep``, the sentence names the three versions as they stand after the
    adoption and the fragment's groups; ``ci.yml`` carries no comment that cites it (#312)."""
    _, dst = variant
    ci = (dst / ".github/workflows/ci.yml").read_text()
    assert "item 9" not in ci
    text = (dst / ".claude/commands/release-prep.md").read_text()
    for where, read in [("release-prep.md", text)]:
        cited = [s for s in sentences(read) if "item 9" in s]
        assert cited, where
        for sentence in cited:
            for name in ITEM_9:
                assert name in sentence, (where, name, sentence)
    (cited,) = [s for s in sentences(text) if "item 9" in s]
    assert "`breaking`" in cited, cited
    assert "`changed`" in cited, cited


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
    """Conventions §3, sdk-core ADR-0041, ADR-0031 and ADR-0062: value lists, id lists and
    tables are declared alike, one ``Listed`` each in the lists of ``LISTS``, core's one
    ``Lists``, and core's frame fetches them into ``PackagedList`` files, records under
    upstream's names, and renders ``enums.py`` formatted by ruff; ``--render-only``
    re-renders from the packaged files, as an adoption does. ``params.py`` names the lists
    core's loader reads, which the declaration holds as ``packaged``."""
    pkg = keyless_flat / "src/xippios" / package_dir(VARIANTS["keyless-flat"])
    script = ast.parse((keyless_flat / "scripts/refresh_reference.py").read_text())
    assert assigned(script) == {"LISTS"}
    declared = [n.value for n in script.body if isinstance(n, ast.Assign)]
    assert isinstance(declared[0], ast.Call)
    assert ast.unparse(declared[0].func) == "Lists"
    assert {k.arg for k in declared[0].keywords} == {
        "package",
        "lists",
        "packaged",
        "client",
        "quota_header",
    }
    (main,) = [n for n in script.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert ast.unparse(main.body[-1]) == "return run(LISTS, argv)"
    assert not {"ID_LISTS", "TABLES"} & assigned(script), "one Listed per list of any shape"
    imported = {
        alias.name
        for node in script.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {"Lists", "run", "PACKAGE", "PACKAGED_LISTS"} <= imported
    assert not {"PackagedList", "render_enums", "id_name_pairs"} & imported, "core's frame"
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


def commands_of(answers: dict[str, object]) -> list[str]:
    """The commands a variant renders: all of them, ``/refresh-reference-data`` where it
    packages reference data."""
    listed = has_reference_data(answers)
    return [name for name in RENDERED_COMMANDS if listed or name != "refresh-reference-data"]


def layout_commands(text: str) -> list[str]:
    """The commands a layout lists after ``.claude/commands/``, a trailing comma carrying
    the list onto the next line."""
    match = re.search(r"^\s*\.claude/commands/[ \t]+((?:[a-z-]+,\s*)*[a-z-]+)", text, re.M)
    assert match, "a layout line lists the commands"
    return re.split(r",\s*", match[1])


def test_every_command_points_at_the_process(keyless_flat: Path) -> None:
    """The definition of done and the review checklist, by URL, and the conventions, by
    section, instead of repeated text (#300)."""
    commands = sorted((keyless_flat / ".claude/commands").glob("*.md"))
    assert [path.stem for path in commands] == RENDERED_COMMANDS, "#120"
    for path in commands:
        flat = " ".join(path.read_text().split())
        for doc in ["definition-of-done.md", "review-checklist.md"]:
            assert SDK_CORE_DOCS + doc in flat, f"{path.name}: {doc}"
        assert "conventions §" in flat, f"{path.name}: the conventions by section"
        assert "../" not in flat, f"{path.name}: a relative path leaves a worktree"


def test_a_render_names_only_the_commands_it_has(variant: tuple[str, Path]) -> None:
    """#120: every ``/<command>`` a render's files name is one it has, so a retired command
    leaves no mention; a render without reference data, a multi-tenant one (#301), has no
    ``/refresh-reference-data``. This README's tree lists them all, as the test below holds,
    and the render's layout no longer does (#300)."""
    name, dst = variant
    rendered = commands_of(VARIANTS[name])
    named: set[str] = set()
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            named |= set(COMMAND_NAMED.findall(path.read_text()))
    assert named <= set(rendered), named - set(rendered)
    assert sorted(path.stem for path in (dst / ".claude/commands").glob("*.md")) == rendered


def test_the_templates_own_files_list_the_rendered_commands() -> None:
    """#120: this README's generated tree lists the commands a render has, once, since this
    CLAUDE.md cites the tree (#300), and neither names a command that neither renders nor
    this repository has."""
    own = {path.stem for path in (ROOT / ".claude/commands").glob("*.md")}
    readme = (ROOT / "README.md").read_text()
    assert sorted(layout_commands(readme)) == sorted(RENDERED_COMMANDS)
    claude = (ROOT / "CLAUDE.md").read_text()
    layout = re.search(r"^\s*\.claude/commands/[ \t]", claude, re.M)
    assert layout is None, "CLAUDE.md cites the README's tree and lists no command"
    for name in ["README.md", "CLAUDE.md"]:
        named = set(COMMAND_NAMED.findall((ROOT / name).read_text()))
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
    name, dst = variant
    found = []
    rendered = commands_of(VARIANTS[name])
    for command in [command for command in SOURCE_COMMANDS if command[:-3] in rendered]:
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
    """sdk-core ADR-0020, conventions §10: the definition of done's checks of an endpoint hold its
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
    The variables of ``live_secrets`` stand beside the key (#300). A source without a
    credential names neither."""
    name, dst = variant
    text = (dst / ".claude/commands/record-fixture.md").read_text()
    keys = key_envs(VARIANTS[name]) + live_secrets(VARIANTS[name])
    for key in keys:
        assert f"`{key}`" in text, key
        assert f"${key}" not in text, key
        assert f"${{{key}}}" not in text, key
    assert ("`ConfigError`" in text) is bool(keys), name
    assert "[ -n " not in text


def test_the_commands_on_a_source_name_what_their_rows_add(keyed_nested: Path) -> None:
    """The names each row's sentence brings: the second case of a cap above the default,
    whose page keeps its ``next_token`` (#89, sdk-core ADR-0038, decision 4), a module of
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


def test_add_endpoint_names_cores_helpers_where_a_task_meets_them(
    variant: tuple[str, Path],
) -> None:
    """#270, #250, sdk-core#483: ``/add-endpoint`` names each helper of core 0.5.0 that a new
    task meets, and every sentence that names ``UnknownCode`` hands the refusal to the
    ``check`` of the list's declaration, ``PackagedList.codes(...)``, so no step tells a task
    to raise it by hand. A variant that packages no reference data, a multi-tenant one
    (#301), names neither, as ``tests/test_reference_data.py`` holds of every render that
    packages none."""
    name, dst = variant
    listed = has_reference_data(VARIANTS[name])
    add = (dst / ".claude/commands/add-endpoint.md").read_text()
    flat = " ".join(add.split())
    expected = (LIST_HELPERS if listed else []) + TASK_HELPERS
    assert [helper for helper in expected if helper not in flat] == [], name
    cited = [sentence for sentence in sentences(add) if "`UnknownCode`" in sentence]
    assert bool(cited) is listed, name
    for sentence in cited:
        assert "`PackagedList.codes(" in sentence, sentence
        assert "check(" in sentence, sentence


def test_add_endpoint_ends_its_list_of_helpers_on_a_full_stop(variant: tuple[str, Path]) -> None:
    """Finding 3 of #327: the list of core's helpers in ``/add-endpoint`` ends on a full stop
    in every render, with reference data or without, and each item before the last on a
    semicolon."""
    name, dst = variant
    text = (dst / ".claude/commands/add-endpoint.md").read_text()
    block = text.split("it takes core's helper and writes none by hand:\n")[1].split("\n\n")[0]
    items = [" ".join(item.split()) for item in re.split(r"\n   - ", "\n" + block)[1:]]
    assert len(items) > 1, (name, block)
    assert [item[-1] for item in items] == [";"] * (len(items) - 1) + ["."], (name, items)


def test_add_endpoint_has_a_wrapper_return_an_answer(variant: tuple[str, Path]) -> None:
    """#333, sdk-core's ``docs/handover.md`` at core 0.5.0, What a source does by hand, item
    1: the one sentence of ``/add-endpoint`` that names ``get_answer`` has the wrapper return
    an ``Answer``, the value it derives from the payload as ``Answer(value, ...)``, and cites
    conventions §4 and §6, with no models returned through ``xippios.core.parse``; the one
    that names the task's ``ResultMeta`` names the ``retrieved_at`` that the ``Answer``
    carries."""
    name, dst = variant
    add = sentences((dst / ".claude/commands/add-endpoint.md").read_text())
    (reads,) = [sentence for sentence in add if "`get_answer`" in sentence]
    for named in ["`Answer`", "`Answer(value, answer.retrieved_at)`", "conventions §4", "§6"]:
        assert named in reads, f"{name}: {named}: {reads}"
    assert "xippios.core.parse" not in reads, (name, reads)
    (meta,) = [sentence for sentence in add if "`ResultMeta`" in sentence]
    for named in ["`retrieved_at`", "`Answer`"]:
        assert named in meta, f"{name}: {named}: {meta}"


def test_record_fixture_takes_cores_recorder(variant: tuple[str, Path]) -> None:
    """#270, sdk-core#483: ``/record-fixture`` names the source's rewrite step, the recorder
    and the one send that writes nothing under their plain names, and what a source's own
    capture of a task's exchanges builds and writes them with (sdk-core ADR-0066); it
    builds no client for one exchange, since core's send is one whatever the client's
    retry, names the recorder's refusal of a 1xx or a 3xx, and says that a source with a
    recorder of its own records with it (#300)."""
    name, dst = variant
    record = " ".join((dst / ".claude/commands/record-fixture.md").read_text().split())
    assert [helper for helper in RECORDER if helper not in record] == [], name
    assert "`scripts/record_fixture.py`" in record, name
    assert "max_attempts" not in record, name
    assert "1xx" in record, name
    assert "3xx" in record, name


def test_record_fixture_names_the_rewrite_type_and_redacted(variant: tuple[str, Path]) -> None:
    """#271, conventions §10: ``/record-fixture`` names ``Rewrite``, the type of the source's
    step that ``xippios.core.testing`` exports, and cites conventions §10 where it says that
    the step writes ``REDACTED`` for a field of a request (#300)."""
    name, dst = variant
    said = sentences((dst / ".claude/commands/record-fixture.md").read_text())
    assert [s for s in said if "`Rewrite`" in s and "`xippios.core.testing`" in s], name
    assert [s for s in said if "`REDACTED`" in s and "conventions §10" in s], name


def test_record_fixture_checks_every_file_of_a_tasks_recording(variant: tuple[str, Path]) -> None:
    """Findings 1 and 2 of #278: the credential grep of ``/record-fixture`` names each file
    that a task's recording writes, ``<case>.json`` and ``<case>_<k>.json`` under the task's
    name (conventions §10)."""
    name, dst = variant
    record = (dst / ".claude/commands/record-fixture.md").read_text()
    spans = re.findall(r"`(grep -niE [^`]*)`", " ".join(record.split()))
    task_files = ["tests/fixtures/<task>/<case>.json", "tests/fixtures/<task>/<case>_*.json"]
    assert [span for span in spans if all(path in span for path in task_files)], (name, spans)


# The names that xippios-core 0.5.0 retired or that its family check no longer reads, which
# the commands named up to the template's 0.4.1 (sdk-core#483): the recorder's sync twins and
# the recording of a task, the cut of a JSON object by its key, the readers of JSON beside
# get_answer, the walks of a page, the reader of a time without a zone, the exemptions of a
# code's name and of a tenant, the readers of the built-answer check, the declaration of a
# snapshot's credentials and the bound on a preview's reads. The refresh's reader of a shared
# document left its name, load_json, for read_json in core 0.5.0, while xippios.core still
# exports load_json as the reader of a packaged file, so no test bars it (finding 4 of #327).
RETIRED_CORE_NAMES = [
    "record_sync",
    "send_once_sync",
    "record_task",
    "array_key",
    "spared_end",
    "mount_fixture",
    "get_json",
    "decode_json",
    "paginate_",
    "naive_time",
    "UNNAMED_CODES",
    "NO_TENANT_TASKS",
    "READERS",
    "Credentials(",
    "preview_reads",
]


def test_the_commands_name_no_retired_name_of_core(variant: tuple[str, Path]) -> None:
    """#300, sdk-core#483: the commands cite core 0.5.0, so none names a name that core
    retired or no longer reads, in every render."""
    _, dst = variant
    found = []
    for path in sorted((dst / ".claude/commands").glob("*.md")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            found += [f"{path.name}:{number}: {n}" for n in RETIRED_CORE_NAMES if n in line]
    assert not found, "\n".join(found)


def test_readme_status_table_has_the_columns_the_family_check_reads(keyless_flat: Path) -> None:
    """Core's family check reads the tables under ``## Status`` by their Task function column."""
    readme = (keyless_flat / "README.md").read_text()
    status = readme[readme.index("\n## Status\n") :]
    status = status[: status.index("\n## ", 1)]
    assert "| Upstream operation | Task function | MCP tool | Status |" in status


# The render's .github/ (#129): a pull-request template that links sdk-core's definition of
# done where it copied it, the organization's checks called from a trigger file each (#249),
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


# GitHub starts the review's trigger file on these: `edited` because the review reads the
# title and the description and a change of the base arrives as `edited`, a push to `main`
# and a dispatch for the review of a range. Never `labeled`: GitHub reports a head's checks
# from its newest run, and a label set at the opening started a run that skipped the review
# (#152). The check of the ADR index reads no title, so an edit does not start it.
CONVENTIONS_EVENTS = {
    "pull_request": {"types": ["opened", "synchronize", "reopened", "edited"]},
    "push": {"branches": ["main"]},
    "workflow_dispatch": None,
}
ADR_INDEX_EVENTS = {"pull_request": {"types": ["opened", "synchronize", "reopened"]}}
# What the review asks of its caller, its one comment and the head's checks, and the review
# of a range the issues beside them.
REVIEW_PERMISSIONS = {"contents": "read", "pull-requests": "write", "checks": "read"}
RANGE_PERMISSIONS = {**REVIEW_PERMISSIONS, "issues": "read"}
# The key by name, never inherited, and no read token's line, as the README of
# xippios/.github has a repository that reads no private document take the file
# (https://github.com/xippios/.github/issues/149).
REVIEW_SECRETS = {"ANTHROPIC_API_KEY": "${{ secrets.ANTHROPIC_API_KEY }}"}
# The review's switch, in each job's condition beside the event, as the README of
# xippios/.github lays out the trigger files: on `off` neither job calls its workflow.
CONVENTIONS_SWITCH = "vars.WORKFLOW_CONVENTIONS != 'off'"
# The title form of a release pull request, which the callee's own condition knows and the
# README of xippios/.github lays out: the trigger file names none (#152).
RELEASE_TITLE_FORM = re.compile(r"<version>|\btitled\b", re.I)


def assert_a_trigger_file(dst: Path, name: str) -> Any:
    """A trigger file of the render, which it returns parsed: the template's bytes, outside
    the skip-listed paths, free of comments, reading by default, its jobs giving the
    workflows they call no input, and naming no title form and nothing around the
    repository."""
    text = (dst / ".github/workflows" / name).read_text()
    assert text == (ROOT / "template/.github/workflows" / name).read_text()
    protected = skip_matcher(package_dir(VARIANTS["keyed-nested"]))
    assert not protected(f".github/workflows/{name}"), "the template's, updated with it"
    assert [line for line in text.splitlines() if line.lstrip().startswith("#")] == []
    assert not RELEASE_TITLE_FORM.search(text), RELEASE_TITLE_FORM.search(text)
    assert not AROUND_THE_REPOSITORY.search(text), AROUND_THE_REPOSITORY.search(text)
    workflow = yaml.safe_load(text)
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert "with" not in job, "the callees take no input"
    return workflow


def test_the_review_has_a_trigger_file_of_its_own(keyed_nested: Path) -> None:
    """#249: ``conventions.yml``, titled ``Conventions``, in the form the README of
    xippios/.github shows. On a pull request its job ``conventions`` calls the review against
    the documents the README lists, and on a push to ``main`` or a dispatch its job ``range``
    calls the review of a range, so the checks keep the names the rulesets match,
    ``conventions / conventions`` and ``range / range``. Each job's condition holds the event
    and the switch ``WORKFLOW_CONVENTIONS``, and each passes the key alone by name (#282)."""
    workflow = assert_a_trigger_file(keyed_nested, "conventions.yml")
    assert workflow["name"] == "Conventions"
    assert workflow[True] == CONVENTIONS_EVENTS  # YAML 1.1 reads the key `on` as a boolean
    jobs = workflow["jobs"]
    assert list(jobs) == ["conventions", "range"], "the job ids name the checks"
    review, span = jobs["conventions"], jobs["range"]
    assert review["if"] == f"github.event_name == 'pull_request' && {CONVENTIONS_SWITCH}"
    assert span["if"] == f"github.event_name != 'pull_request' && {CONVENTIONS_SWITCH}"
    assert review["uses"] == ORG_WORKFLOW.format("conventions")
    assert span["uses"] == ORG_WORKFLOW.format("conventions-range")
    assert review["permissions"] == REVIEW_PERMISSIONS
    assert span["permissions"] == RANGE_PERMISSIONS
    for job in [review, span]:
        assert job["secrets"] == REVIEW_SECRETS, "by name, never inherited"


def test_the_adr_index_has_a_trigger_file_of_its_own(keyed_nested: Path) -> None:
    """#249: ``adr-index.yml``, titled ``ADR index``, calls the check of the ADR index as the
    job ``adr-index``, so the check stays ``adr-index / adr-index``, on a pull request's
    opening, push and reopening. Its job holds no condition, since the workflow it calls
    reads the switch ``WORKFLOW_ADR_INDEX`` itself, and passes no secret; the check runs the
    render's own script."""
    workflow = assert_a_trigger_file(keyed_nested, "adr-index.yml")
    assert workflow["name"] == "ADR index"
    assert workflow[True] == ADR_INDEX_EVENTS
    assert workflow["jobs"] == {"adr-index": {"uses": ORG_WORKFLOW.format("adr-index")}}
    assert (keyed_nested / ADR_SCRIPT).is_file(), "the script the check runs"


# Each workflow's title, by the organization's one rule: the same for a trigger file and the
# workflow it calls (https://github.com/xippios/.github/issues/111). publish.yml takes
# `Publish` with sdk-core's bytes at v0.4.1 (https://github.com/xippios/sdk-core/issues/407).
WORKFLOW_TITLES = {
    "ci.yml": "CI",
    "publish.yml": "Publish",
    "live.yml": "Live tests",
    "siblings.yml": "Siblings",
    "conventions.yml": "Conventions",
    "adr-index.yml": "ADR index",
}
# The workflows a variable switches on their one job, on unless it is `off`, the
# repository's value over the organization's; CI and the release train carry none.
SWITCHED = {"live.yml": "WORKFLOW_LIVE", "siblings.yml": "WORKFLOW_SIBLINGS"}


def test_each_workflow_has_its_title_and_its_switch(variant: tuple[str, Path]) -> None:
    """#249: every workflow of a render takes its title by the organization's rule, and
    ``live.yml`` and ``siblings.yml`` hold their switch in their one job's condition, so a
    variable ``WORKFLOW_LIVE`` of ``off`` skips the live tests and the check reports as
    skipped; ``ci.yml`` and ``publish.yml`` hold none and always run."""
    _, dst = variant
    for path in sorted((dst / ".github/workflows").glob("*.yml")):
        text = path.read_text()
        workflow = yaml.safe_load(text)
        assert workflow["name"] == WORKFLOW_TITLES[path.name], path.name
        if path.name in SWITCHED:
            (job,) = workflow["jobs"].values()
            assert job["if"] == f"vars.{SWITCHED[path.name]} != 'off'", path.name
            assert text.count("WORKFLOW_") == 1, path.name
        elif path.name not in TRIGGER_FILES:
            assert "WORKFLOW_" not in text, f"{path.name} always runs"


# The switch of each workflow that has one, by its file, the two trigger files' among them,
# whose called workflows read it (https://github.com/xippios/.github/issues/111).
SWITCHES = {
    **SWITCHED,
    "conventions.yml": "WORKFLOW_CONVENTIONS",
    "adr-index.yml": "WORKFLOW_ADR_INDEX",
}


def readme_workflows(readme: str) -> dict[str, str]:
    """The paragraphs of a README's ``## Workflows``, each by the workflow file it opens with:
    a paragraph that opens with none, or a file named twice, fails."""
    section = readme.split("\n## Workflows\n", 1)[1].split("\n## ", 1)[0]
    found: dict[str, str] = {}
    for block in [" ".join(block.split()) for block in section.split("\n\n") if block.strip()]:
        opening = re.match(r"`([a-z-]+\.yml)`", block)
        assert opening, block
        assert opening[1] not in found, opening[1]
        found[opening[1]] = block
    return found


def test_the_readme_says_what_each_workflow_does(variant: tuple[str, Path]) -> None:
    """#308: the render's README holds ``## Workflows``, one paragraph for each workflow it
    renders, as the organization's rule asks: what it checks, when it runs, what the calling
    file hands over and what switches it (https://github.com/xippios/.github/issues/111).
    Each names its switch where it has one and none where it always runs, each variable a
    step is handed from a secret or the job's token, and ``live.yml``'s the time its
    schedule sets."""
    _, dst = variant
    readme = (dst / "README.md").read_text()
    assert readme.count("\n## Workflows\n") == 1
    paragraphs = readme_workflows(readme)
    workflows = dst / ".github/workflows"
    assert sorted(paragraphs) == sorted(path.name for path in workflows.glob("*.yml"))
    for file, paragraph in paragraphs.items():
        switch = {SWITCHES[file]} if file in SWITCHES else set()
        assert set(re.findall(r"WORKFLOW_[A-Z_]+", paragraph)) == switch, file
        workflow = yaml.safe_load((workflows / file).read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                for variable, value in step.get("env", {}).items():
                    if "secrets." in str(value) or "github.token" in str(value):
                        assert f"`{variable}`" in paragraph, (file, variable)
    live = yaml.safe_load((workflows / "live.yml").read_text())
    (schedule,) = live[True]["schedule"]  # YAML 1.1 reads the key `on` as a boolean
    minute, hour = schedule["cron"].split()[:2]
    assert f"{int(hour):02d}:{int(minute):02d} UTC" in paragraphs["live.yml"]


def test_the_readme_promises_no_field_that_core_leaves_optional(
    variant: tuple[str, Path],
) -> None:
    """#300: the README's first paragraph names the metadata every response carries, which
    holds neither ``published_at`` nor ``vintage``: core's ``ResultMeta`` leaves both to the task
    that knows them."""
    _, dst = variant
    readme = (dst / "README.md").read_text()
    lead = readme.split("\n## ", 1)[0]
    assert "published_at" not in lead
    assert "vintage" not in lead
    assert "retrieved_at" in lead


def test_the_templates_own_pull_requests_trigger_the_organizations_checks() -> None:
    """#151, #249: this repository triggers the organization's checks on its own pull
    requests from the files it renders into a source, byte for byte, so a pull request of
    the template reports ``conventions / conventions`` and ``adr-index / adr-index`` beside
    ``ci``, and the index check runs its own script. The caller of them all is gone from
    both, or each check would run twice."""
    workflows = ROOT / ".github/workflows"
    for name in TRIGGER_FILES:
        own = workflows / name
        assert own.is_file(), f"the template's own {name}"
        assert own.read_bytes() == (ROOT / "template/.github/workflows" / name).read_bytes()
    for folder in [workflows, ROOT / "template/.github/workflows"]:
        assert not (folder / "organization.yml").exists(), folder
    assert os.access(ROOT / ADR_SCRIPT, os.X_OK), "the script the index check runs"


# The callers of the organization's checks that the template rendered before, in their
# shape: the retired merge gates' up to v0.3.2, one workflow of that name with two jobs, and
# the one caller of the organization's checks up to v0.4.0.
RETIRED_CALLERS = {
    "gates.yml": """name: gates

on:
  pull_request:

permissions:
  contents: read

jobs:
  merge-class:
    uses: ./.github/workflows/merge-class.yml
  family-review:
    uses: ./.github/workflows/family-review.yml
""",
    "organization.yml": """name: Organization

on:
  pull_request:
    types: [opened, synchronize, reopened, edited]

permissions:
  contents: read

jobs:
  conventions:
    uses: xippios/.github/.github/workflows/conventions.yml@main
  adr-index:
    uses: xippios/.github/.github/workflows/adr-index.yml@main
""",
}


@pytest.mark.parametrize("retired", list(RETIRED_CALLERS))
def test_an_update_replaces_the_retired_caller(
    template_src: Path, tmp_path: Path, retired: str
) -> None:
    """A source made while the template rendered a caller it renders no longer loses it at
    ``copier update`` and gets the trigger files in its place, so each check runs once: the
    merge gates' ``gates.yml``, which the sources disabled by hand, and ``organization.yml``,
    the caller of the organization's checks up to v0.4.0 (#249). GitHub keeps a workflow's
    state by its path, so the trigger files start enabled."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    workflows = template / "template/.github/workflows"
    for name in TRIGGER_FILES:
        (workflows / name).unlink()
    (workflows / retired).write_text(RETIRED_CALLERS[retired])
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "the retired caller")
    git(template, "tag", "v0.0.1")
    (workflows / retired).unlink()
    shutil.copytree(template_src, template, dirs_exist_ok=True)
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "the trigger files")
    git(template, "tag", "v0.0.2")
    dst = tmp_path / "repo"
    answers = {**BASE_ANSWERS, **VARIANTS["keyless-flat"]}
    run_copy(str(template), str(dst), data=answers, defaults=True, vcs_ref="v0.0.1", quiet=True)
    assert (dst / ".github/workflows" / retired).read_text() == RETIRED_CALLERS[retired]
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    assert not (dst / ".github/workflows" / retired).exists()
    for name in TRIGGER_FILES:
        rendered = dst / ".github/workflows" / name
        assert rendered.read_bytes() == (workflows / name).read_bytes()


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


def test_a_keyed_client_leaves_its_auth_to_the_source(
    keyed_nested: Path, keyless_flat: Path
) -> None:
    """#301: no answer says how the key is sent, so a keyed source's ``_client.py`` imports
    no auth of core's, builds its client without one and exports no ``auth``, which the
    source's first pull request passes, as the comment above the client shows; a keyless
    client has none and declares no ``API_KEY_ENV``, which it never reads (#300)."""
    keyed_client = (keyed_nested / "src/xippios/usda/nass/_client.py").read_text()
    keyless = (keyless_flat / "src/xippios/eurostat/_client.py").read_text()
    for client in [keyed_client, keyless]:
        (core,) = [
            node
            for node in ast.parse(client).body
            if isinstance(node, ast.ImportFrom) and node.module == "xippios.core"
        ]
        assert not KEY_AUTHS & {alias.name for alias in core.names}
        assert "\nclient = AsyncClient(config)\n" in client
        assert '"auth"' not in client
    assert "# auth = " in keyed_client, "the place the source fills"
    assert "Auth" not in keyless
    assert "API_KEY_ENV" not in keyless


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
    one quoted scalar."""
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
    if not live_secrets(VARIANTS[name]):
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
    """sdk-core ADR-0021: each entry names another source by its slug, neither this one nor core and
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


def test_the_sibling_check_names_the_declared_dependencies(render: Callable[[str], Path]) -> None:
    """The script reads the source packages a render depends on from ``pyproject.toml``,
    every ``xippios-*`` but core in ``[project] dependencies`` (sdk-core ADR-0021), to install and
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
    """sdk-core ADR-0006 and ``import_path``'s help: a single-API provider whose slug carries a
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
    """A source's files survive a re-render; the template's own are rendered again. The
    conftest and the secrets baseline are the source's from 0.5.0 on, so an update merges no
    line of the template's into a source's own there, and so is the layout, while the Never
    file is the template's (#300, #233).

    The slug ends in -api, so the package itself is .../api/: the patterns name the package
    directory, and its mcp.py is the template's while its api/ is the source's, as are the
    parsers' package and the samples' table that has_files renders (sdk-core ADR-0020).
    """
    answers = {"source_slug": "ex-api", "has_files": True, **keyed("")}
    dst = generate(template_src, tmp_path / "repo", **answers)
    pkg = "src/xippios/ex/api"
    names = ["tasks.py", "_client.py", "errors.py", "__init__.py", "api/__init__.py"]
    mine = [f"{pkg}/{n}" for n in [*names, "parse/__init__.py"]]
    mine += ["tests/test_tasks.py", "tests/fixtures/files/README.md", "README.md", "CLAUDE.md"]
    mine += ["tests/conftest.py", ".secrets.baseline", LAYOUT_FILE, *FILLED_SCRIPTS, *ADR_INDEX]
    templates = [f"{pkg}/mcp.py", ".github/CODEOWNERS", NEVER_FILE]
    templates += [".claude/settings.json", "changelog/README.md", *ADR_TEMPLATE_FILES]
    for rel in [*mine, *templates]:
        (dst / rel).write_text("# edited\n")
    generate(template_src, dst, **answers)
    for rel in mine:
        assert (dst / rel).read_text() == "# edited\n", f"{rel} is the source's"
    for rel in templates:
        assert (dst / rel).read_text() != "# edited\n", f"{rel} is the template's"


def test_an_update_leaves_a_deleted_stub_deleted(template_src: Path, tmp_path: Path) -> None:
    """#300: a source deletes ``errors.py`` or ``enums.py`` where it never filled it, and an
    update of copier 9.19.1 to a release that renders the stub as before brings neither back,
    since it applies the source's deletion over the new render."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    git(template, "init", "-q", "-b", "main")
    for tag in ["v0.0.1", "v0.0.2"]:
        (template / "RELEASE").write_text(f"{tag}\n")
        git(template, "add", "-A")
        git(template, "commit", "-q", "--no-verify", "-m", tag)
        git(template, "tag", tag)
    answers = VARIANTS["keyless-flat"]
    data = {**BASE_ANSWERS, **answers}
    dst = tmp_path / "repo"
    run_copy(str(template), str(dst), data=data, defaults=True, vcs_ref="v0.0.1", quiet=True)
    stubs = [f"src/xippios/{package_dir(answers)}/{name}" for name in ["errors.py", "enums.py"]]
    for rel in stubs:
        (dst / rel).unlink()
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source that deleted two stubs")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    assert [rel for rel in stubs if (dst / rel).exists()] == []


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
    template_src: Path, tmp_path: Path
) -> None:
    """sdk-core ADR-0032: usda-psd, usda-esr and usda-gats share one key and one gateway quota;
    their nightly runs never start together, and a render keeps a repository's time."""
    shared = {"source_slug": "usda-psd", **keyed("DATA_GOV_API_KEY")}
    starts = {"usda-psd": live_start(generate(template_src, tmp_path / "usda-psd", **shared))}
    for slug in ["usda-esr", "usda-gats"]:
        dst = generate(template_src, tmp_path / slug, **{**shared, "source_slug": slug})
        starts[slug] = live_start(dst)
    assert len(set(starts.values())) == 3, starts
    again = generate(template_src, tmp_path / "again", **shared)
    assert live_start(again) == starts["usda-psd"], "stable across renders"


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


# The names of the retired process, built from parts, so that a search of this repository
# for them, as a release's proof runs one, finds none in this file either.
GATES_REPOSITORY = "sdk" + "-gates"
GATES_SWITCH = "GATES" + "_CALLER"
RETIRED_SCRIPT = "new" + "-source"
RETIRED_COMMAND = "adopt" + "-release"


def test_no_workflow_calls_the_retired_gates() -> None:
    """The merge gates are retired and their reusable workflows are gone (#99): neither this
    repository nor a render carries a caller of them."""
    for workflows in [ROOT / ".github/workflows", ROOT / "template/.github/workflows"]:
        assert not (workflows / "gates.yml").exists(), workflows
        for path in sorted(workflows.iterdir()):
            assert f"xippios/{GATES_REPOSITORY}/" not in path.read_text(), path


def test_the_templates_own_workflows_are_hardened() -> None:
    """Conventions §13 for this repository's own workflows too: SHA pins with the version
    in a comment, but the organization's checks, called at ``@main``, ``contents: read``
    at the top, and no checkout keeps its credentials but the one in a job that pushes,
    whose reason the README's release section gives (#307)."""
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for action, comment in workflow_uses(path):
            if path.name in TRIGGER_FILES:
                assert re.fullmatch(r"xippios/\.github/\.github/workflows/[\w-]+\.yml@main", action)
                assert not comment, f"{path.name}: {action}{comment}"
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


def test_the_templates_own_workflows_carry_no_comment() -> None:
    """https://github.com/xippios/.github/issues/111, #307: this repository's own workflows
    carry no comment but the version after a pinned action, as the ones it renders as its
    own; its README says what each does."""
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for line in path.read_text().splitlines():
            if YAML_COMMENT.search(line):
                assert PINNED_USES.fullmatch(line), f"{path.name}: {line}"


def test_the_readme_says_what_the_release_run_does() -> None:
    """#307: the README's release section names ``release.yml`` and says what its header
    said before: how a run that failed is finished and a tag on the wrong commit mended, by
    GitHub's two re-runs, and why its one checkout keeps its credentials."""
    readme = (ROOT / "README.md").read_text()
    section = readme.split("\n## Releasing the template\n", 1)[1].split("\n## ", 1)[0]
    for name in [
        "`.github/workflows/release.yml`",
        '"Re-run failed jobs"',
        '"Re-run all jobs"',
        "`persist-credentials: false`",
    ]:
        assert name in section, name


PROVE = ROOT / "scripts/prove.sh"
# A proof that --all starts, as it names it, and one that failed.
PROOF_STARTED = re.compile(r"^==> proof (\d+) of (\d+): scripts/prove\.sh(.*)$", re.MULTILINE)
PROOF_FAILED = re.compile(r"^failed: scripts/prove\.sh(.*)$", re.MULTILINE)


def test_ci_proves_every_shape_by_one_call() -> None:
    """T11, #304: the required ``ci`` job runs the proofs once, by ``scripts/prove.sh --all``
    after the tests, so a proof that fails blocks the merge, and a shape added or removed
    changes the list in ``scripts/``, never the workflow."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    (job,) = workflow["jobs"].values()
    assert job["name"] == "ci", "the check the org ruleset requires"
    runs = [str(step.get("run", "")) for step in job["steps"]]
    proofs = [run for run in runs if "prove" in run]
    assert proofs == ["scripts/prove.sh --all"]
    assert runs.index("uv run pytest") < runs.index(proofs[0])


def run_every_proof(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """``prove.sh --all`` from a copy of the script alone, in a folder without the template,
    so that each proof it starts fails at once: what --all does with the proofs' outcomes."""
    scripts = tmp_path / "bare/scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(PROVE, scripts / "prove.sh")
    env = {**os.environ, "TMPDIR": str(tmp_path)}
    return subprocess.run(
        [str(scripts / "prove.sh"), "--all", *args], capture_output=True, text=True, env=env
    )


def test_prove_all_runs_every_shape_and_fails_where_one_fails(tmp_path: Path) -> None:
    """#304: ``--all`` starts one proof for each shape that ``scripts/prove.sh`` takes by its
    flag, the keyed nested one with no flag and the keyless nested one again with
    ``-d has_files=true`` (sdk-core ADR-0020), each once and in a process of its own; it goes
    on after a proof that failed, names each that failed and fails itself."""
    flags = re.findall(r"^\s+(--[\w-]+)\) shape=", PROVE.read_text(), re.MULTILINE)
    assert "--keyless" in flags, "the shapes' flags as the parser reads them"
    run = run_every_proof(tmp_path)
    assert run.returncode == 1, run.stdout + run.stderr
    started = PROOF_STARTED.findall(run.stdout)
    count = len(started)
    assert [(int(n), int(of)) for n, of, _ in started] == [(n, count) for n in range(1, count + 1)]
    shapes = [shape.strip() for _, _, shape in started]
    assert len(set(shapes)) == count, shapes
    assert {shape.split(" ")[0] for shape in shapes} == {"", *flags}
    assert "--keyless-nested -d has_files=true" in shapes
    assert [shape.strip() for shape in PROOF_FAILED.findall(run.stderr)] == shapes


@pytest.mark.parametrize("given", [["--keyless"], ["-d", "has_files=true"], ["--dest", "x"]])
def test_prove_all_takes_no_shape_answer_or_destination(tmp_path: Path, given: list[str]) -> None:
    """#304: ``--all`` proves the list as it stands, each shape in a folder of its own, so it
    refuses a shape's flag, an answer and a destination before it starts a proof."""
    run = run_every_proof(tmp_path, *given)
    assert run.returncode == 2, run.stdout + run.stderr
    assert run.stderr.startswith("error: --all takes "), run.stderr
    assert not PROOF_STARTED.search(run.stdout)


# The core reference that scripts/prove.sh passes when it is given none, and its line in the
# script's usage.
CORE_REF_DEFAULT = re.compile(r'^core_ref="([^"]*)"', re.MULTILINE)


def test_the_proofs_install_the_core_release_from_pypi() -> None:
    """#355: xippios-core 0.5.0, ``core_version``'s default, is on PyPI, so every proof
    installs that release with no pin of a core commit: ``scripts/prove.sh`` passes an
    empty ``core_git_ref`` unless ``--core-ref`` names one, and its usage says so. A later
    package that proves on a candidate of core sets the default and this test together."""
    text = PROVE.read_text()
    assert CORE_REF_DEFAULT.findall(text) == [""]
    assert '--core-ref REF     sdk-core commit to depend on, main or a full SHA; default ""' in text


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


# The rule of the retired merge gates: the class that decided a pull request's merge, under
# any of its names (`human class`, `class review`), and the auto-merge a session enabled on
# one. A pull request merges under the rulesets of `main`.
MERGE_CLASS = re.compile(
    r"\bmerge[ -]class(?:es)?\b|\b(?:human|review) class\b|\bclass (?:human|review)\b"
    r"|\bauto-merge\b",
    re.I,
)


def test_no_instruction_names_the_merge_class() -> None:
    """This CLAUDE.md and every file the template renders name no class of a merge and no
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
# their switch, the classes of a merge, the branch names and the PR body of that process,
# the owners file of its coordination, and the script and the commands that made a source
# and adopted a release by it, with the pull request they opened. The renders leave it in
# steps of their own.
RETIRED_PROCESS = re.compile(
    rf"\b{GATES_REPOSITORY}\b|\b{GATES_SWITCH}\b|\bgates\.yml\b|\bmerge[ -]class(?:es)?\b"
    r"|\b(?:feature|fix|chore)/|\bdocs/<topic>|definition-of-done checklist"
    r"|as the definition of done says|\bowners\.toml\b"
    rf"|\b{RETIRED_SCRIPT}\b|\b{RETIRED_COMMAND}\b|\bgh (?:pr|repo) create\b",
    re.I,
)
OWN_FILES = ["copier.yml", "README.md", "CLAUDE.md", ".claude", "scripts", ".github"]


def test_the_templates_own_files_name_no_retired_process() -> None:
    """The template's own instructions, scripts and workflows name none of the process
    before the migration (#99), and neither the script that made a source nor its command
    is left: ``copier copy`` generates one, as the README says (#119). The CHANGELOG is
    history."""
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
    named = {"CLAUDE.md", "README.md", "scripts/prove.sh"}
    assert named <= scanned, "the files that named it"
    assert not (ROOT / f"scripts/{RETIRED_SCRIPT}.sh").exists()
    assert not (ROOT / f".claude/commands/{RETIRED_SCRIPT}.md").exists()


# What stands around a repository that works alone, by the words a comment used for it: a
# session, the workspace, and the maintainer by name where the role is meant (#150).
AROUND_BY_NAME = re.compile(r"\bsessions?\b|\bworkspaces?\b|\bJohannes\b", re.I)
# The two files that keep such words for now: the owners file, which the tool around the
# template writes, and the render's publish.yml, sdk-core's bytes until
# https://github.com/xippios/sdk-core/issues/215.
AROUND_BY_NAME_KEPT = {".github/CODEOWNERS", "template/.github/workflows/publish.yml"}


def test_the_templates_files_say_what_stands_around_them_in_their_own_words() -> None:
    """#150: the template's own files and every file it renders say what they mean in the
    repository's own words, the maintainer, a sibling's checkout beside the repository, a
    source that fills a file, never a session, the workspace or a person's name."""
    scanned, found = set(), []
    for name in [*OWN_FILES, "template"]:
        root = ROOT / name
        for path in [root] if root.is_file() else sorted(root.rglob("*")):
            rel = path.relative_to(ROOT).as_posix()
            if not path.is_file() or rel in AROUND_BY_NAME_KEPT:
                continue
            scanned.add(rel)
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if AROUND_BY_NAME.search(line):
                    found.append(f"{rel}:{number}: {line}")
    assert not found, "\n".join(found)
    named = {
        "copier.yml",
        ".github/workflows/release.yml",
        "template/.github/{% if '.' in import_path or depends_on %}scripts{% endif %}"
        "/check-siblings.sh",
    }
    assert named <= scanned, "the files that named it"


# A release heading of CHANGELOG.md, as .github/workflows/release.yml finds the top one.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - ", re.M)


def test_the_manifest_names_the_latest_release() -> None:
    """The template's version is its latest release's: the release's pull request sets
    ``version`` in pyproject.toml with the CHANGELOG heading that release.yml tags, so a
    reader of the manifest bumps from the released version, never from 0.1.0 (#101). It
    locks again too, and CI syncs with ``--locked``, which fails on a lock that names the
    old one: ``--frozen`` passes it, and the next ``uv run`` writes the lock again before
    the suite reads it."""
    heading = RELEASE_HEADING.search((ROOT / "CHANGELOG.md").read_text())
    assert heading, "CHANGELOG.md has no release heading"
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["project"]["version"] == heading[1]
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    (job,) = workflow["jobs"].values()
    runs = [str(step.get("run", "")) for step in job["steps"]]
    syncs = [run for run in runs if run.startswith("uv sync")]
    assert syncs == ["uv sync --locked"], "a stale uv.lock fails CI's first step"


# The template's own README and CLAUDE.md (#119, #144, #146). The README lists the documents
# a change of the template follows under `## Documents`, in the form a render's README takes,
# and says how a source is generated: with copier alone, its call run here on the working
# tree. The CLAUDE.md links that section, its layout names the repository's own files, and
# neither names anything around the repository.
TEMPLATE_DOCUMENTS = ["docs/adr.md", "changelog/README.md"]
TEMPLATE_URL = "https://github.com/xippios/sdk-template.git"


def test_the_templates_own_readme_lists_its_documents() -> None:
    """This README's ``## Documents`` lists sdk-core's conventions, ADR index, definition of
    done and review checklist, then this repository's ADR index and changelog rules, each as
    ``- <repository>: [<path>](<its file on GitHub>) — <what it is>``; its own are files
    here."""
    readme = (ROOT / "README.md").read_text()
    assert readme.count("\n## Documents\n") == 1
    expected = [("sdk-core", path) for path in CORE_DOCUMENTS]
    expected += [("sdk-template", path) for path in TEMPLATE_DOCUMENTS]
    assert documents(readme) == expected
    for path in TEMPLATE_DOCUMENTS:
        assert (ROOT / path).is_file(), path


def test_the_templates_own_instructions_name_nothing_around_the_repository() -> None:
    """This README and this CLAUDE.md name no tooling, session, claim or numbered rule around
    the repository, nor ``.claude/family.md``, which no render has any more; the CLAUDE.md
    links the README's documents instead of repeating them and names no branch, no GitHub
    CLI, no merge, no reviewer and no person."""
    readme = (ROOT / "README.md").read_text()
    claude = (ROOT / "CLAUDE.md").read_text()
    found = []
    for name, text, patterns in [
        ("README.md", readme, [AROUND]),
        ("CLAUDE.md", claude, [AROUND, CHANGE_LANDING]),
    ]:
        for number, line in enumerate(text.splitlines(), 1):
            if "family.md" in line or any(pattern.search(line) for pattern in patterns):
                found.append(f"{name}:{number}: {line}")
    assert not found, "\n".join(found)
    assert "(README.md#documents)" in claude, "the README's section, linked"
    for repository, path in documents(readme):
        url = f"https://github.com/xippios/{repository}/blob/main/{path}"
        assert url not in claude, url
    assert "https://github.com/xippios/sdk-core/tree/" not in claude


def margin_entries(claude: str) -> list[str]:
    """The paths at the left margin of a CLAUDE.md's Layout block, several on a line where
    commas join them."""
    block = claude.split("\n## Layout\n", 1)[1].split("```\n", 2)[1]
    entries = []
    for line in block.splitlines():
        if not line[:1].strip():
            continue
        words = line.split()
        while words:
            word = words.pop(0)
            entries.append(word.rstrip(","))
            if not word.endswith(","):
                break
    return entries


def test_the_templates_own_layout_names_its_files() -> None:
    """Each path at the left margin of this CLAUDE.md's layout is one the repository has, and
    every file of its own scripts, workflows, Claude settings, tests and docs stands there,
    by its path or its folder's, so a file that leaves takes its entry along."""
    entries = margin_entries((ROOT / "CLAUDE.md").read_text())
    assert [entry for entry in entries if not (ROOT / entry).exists()] == []
    unnamed = []
    for folder in ["scripts", ".github/workflows", ".claude", "tests", "docs"]:
        for path in sorted((ROOT / folder).rglob("*")):
            rel = path.relative_to(ROOT)
            if not path.is_file() or "__pycache__" in rel.parts:
                continue
            folders = {f"{parent.as_posix()}/" for parent in rel.parents if parent.name}
            if not ({rel.as_posix()} | folders) & set(entries):
                unnamed.append(rel.as_posix())
    assert unnamed == []


def readme_copy_call() -> list[str]:
    """The README's ``copier copy`` call, its continued lines joined, as the shell splits it."""
    readme = (ROOT / "README.md").read_text()
    blocks = re.findall(r"```bash\n(.*?)```", readme, re.S)
    commands = [line for block in blocks for line in block.replace("\\\n", " ").splitlines()]
    (call,) = [line for line in commands if "copier copy" in line.split("#", 1)[0]]
    return shlex.split(call, comments=True)


def test_the_readme_generates_a_source_with_copier_alone(
    template_src: Path, tmp_path: Path
) -> None:
    """#119: a source is generated with ``copier copy`` from this repository's GitHub URL at
    its latest tag, which no ``--vcs-ref`` names, so no release rewrites the call; it passes
    ``--defaults`` and an answer for each question that has no default. Run as the README
    writes it, but on the working tree, it renders a source whose answers file records each
    answer it gave."""
    call = readme_copy_call()
    copy = call.index("copy")
    assert call[copy - 1] == "copier", call
    args = iter(call[copy + 1 :])
    flags, answers, positional = [], {}, []
    for arg in args:
        if arg in ("-d", "--data"):
            key, value = next(args).split("=", 1)
            answers[key] = value
        elif arg.startswith("-"):
            flags.append(arg)
        else:
            positional.append(arg)
    assert flags == ["--defaults"], "the latest tag: no --vcs-ref"
    src, dst = positional
    assert src == TEMPLATE_URL
    assert dst == f"sdk-{answers['source_slug']}"
    asked = [
        name
        for name, question in QUESTIONS.items()
        if not name.startswith("_")
        and question.get("when") is not False
        and "default" not in question
    ]
    assert set(asked) <= set(answers), set(asked) - set(answers)
    repo = tmp_path / dst
    run_copy(str(template_src), str(repo), data=answers, defaults=True, quiet=True)
    recorded = yaml.safe_load((repo / ".copier-answers.yml").read_text())
    for key, value in answers.items():
        assert str(recorded[key]) == value, key


def readme_bash_lines(word: str) -> list[list[str]]:
    """The lines of the README's ``bash`` blocks that run ``copier <word>``, as the shell
    splits them, their comments dropped."""
    readme = (ROOT / "README.md").read_text()
    blocks = re.findall(r"```bash\n(.*?)```", readme, re.S)
    commands = [line for block in blocks for line in block.replace("\\\n", " ").splitlines()]
    calls = [shlex.split(line, comments=True) for line in commands]
    return [call for call in calls if f"copier {word}" in " ".join(call)]


def test_the_readme_shows_a_sources_hand_edits_before_its_update(
    template_src: Path, tmp_path: Path
) -> None:
    """#152: before an update a source compares its ``main`` with a render of the tag it
    records, with the README's ``copier recopy`` in a clean checkout: the diff is the
    source's own lines in the template's files, which the update carries on, and leaves
    the files the source fills. The README names ``has_files`` among the answers to check."""
    (call,) = readme_bash_lines("recopy")
    recopy = call.index("recopy")
    assert call[recopy - 1] == "copier", call
    assert sorted(call[recopy + 1 :]) == ["--defaults", "--overwrite", "--vcs-ref=:current:"]
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "a release")
    git(template, "tag", "v0.0.1")
    dst = tmp_path / "repo"
    answers = {**BASE_ANSWERS, **VARIANTS["keyless-flat"]}
    run_copy(str(template), str(dst), data=answers, defaults=True, vcs_ref="v0.0.1", quiet=True)
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source")
    edited = ".claude/commands/add-endpoint.md"
    for rel in [edited, "CLAUDE.md"]:
        with (dst / rel).open("a") as file:
            file.write("\nA line of the source's own.\n")
    git(dst, "commit", "-q", "--no-verify", "-a", "-m", "its own lines")
    copier = [sys.executable, "-m", "copier", *call[recopy:], "--quiet"]
    subprocess.run(copier, cwd=dst, capture_output=True, text=True, check=True)
    assert git(dst, "diff", "--name-only").split() == [edited]
    assert git(dst, "status", "--porcelain", "--untracked-files=all").split() == ["M", edited]
    readme = (ROOT / "README.md").read_text()
    updating = readme.split("\n## Updating generated repositories\n", 1)[1].split("\n## ", 1)[0]
    assert "`has_files`" in updating, "an answer the update keeps, a wrong one included"
