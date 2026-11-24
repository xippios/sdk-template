"""Reference data: the answer that renders the scaffold or leaves it out, the refresh script
on core's frame, which sends each request once, counts what it sent and takes ``--only``
(#40, #64, #239), and the live comparison that ``tests/test_live.py`` collects (#252).

``scripts/prove.sh`` runs the rendered script itself, on core, against answers it replays.
"""

import ast
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from copier import run_copy, run_update
from helpers import (
    BASE_ANSWERS,
    LIST_HELPERS,
    QUESTIONS,
    ROOT,
    TASK_HELPERS,
    VARIANTS,
    generate,
    git,
    has_reference_data,
    package_dir,
    ruff,
)

# The scaffold of a source that packages reference data, ``{pkg}`` its package directory:
# the lists, their enums, the packaged files, the script that fetches them and its command.
SCAFFOLD = [
    "src/xippios/{pkg}/params.py",
    "src/xippios/{pkg}/enums.py",
    "src/xippios/{pkg}/reference",
    "scripts/refresh_reference.py",
    ".claude/commands/refresh-reference-data.md",
]
# Its four files under _skip_if_exists, the ones sdk-cashctrl deleted
# (https://github.com/xippios/sdk-cashctrl/pull/14).
FILLED = [
    "src/xippios/{pkg}/params.py",
    "src/xippios/{pkg}/enums.py",
    "src/xippios/{pkg}/reference/README.md",
    "scripts/refresh_reference.py",
]
# How a render names the scaffold: a file, the folder, the script, the command, an import,
# or the words, as the code rule on what the tasks call did (#243) and /add-endpoint's
# lookups did, and core's names that read a packaged list or refuse a code it lacks, which
# /add-endpoint gives a task only where there is a list (#250, #270), and the live
# comparison of the packaged lists that tests/test_live.py collects and declares (#252).
NAMED = re.compile(
    r"params\.py|enums\.py|\breference/|refresh_reference|refresh-reference-data"
    r"|\bxippios\.[\w.]+\.(?:params|enums)\b|\breference data\b|\breference lookups?\b"
    r"|\bPackaged(?:List|Codes)\b|\bnames_codes\b|\bUnknownCode\b"
    r"|\bxippios\.core\.testing\.live\b|\bLIVE_LISTS\b|\bNO_LIVE_LIST\b"
)
# What a module's top level must not call: the family check loads tests/test_live.py to read
# its declarations and fails one that skips, fails or exits at its import (sdk-core ADR-0055).
STOPS = {"pytest.skip", "pytest.importorskip", "pytest.fail", "pytest.exit", "sys.exit", "exit"}
# The variants that package reference data: every one but the multi-tenant ones (#301).
LISTED = [name for name, answers in VARIANTS.items() if has_reference_data(answers)]


def paths(rels: list[str], answers: dict[str, object]) -> list[str]:
    return [rel.format(pkg=package_dir(answers)) for rel in rels]


@pytest.fixture(scope="module")
def without_reference(template_src: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The keyed nested render of a source that packages no reference data."""
    dst = tmp_path_factory.mktemp("without-reference") / "repo"
    return generate(template_src, dst, **VARIANTS["keyed-nested"], has_reference_data=False)


def test_the_answer_is_true_unless_a_source_says_otherwise(variant: tuple[str, Path]) -> None:
    """``has_reference_data`` is a bool whose default, true, is one plain scalar, so every
    source that predates the question takes it on update and keeps its scaffold; each
    variant renders the scaffold whole and records the answer, but a multi-tenant one, which
    answers false (#301) and renders none of it."""
    name, dst = variant
    question = QUESTIONS["has_reference_data"]
    assert (question["type"], question["default"]) == ("bool", True)
    raw = (ROOT / "copier.yml").read_text().split("\nhas_reference_data:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: true\n" in block, "one plain scalar, a literal"
    listed = has_reference_data(VARIANTS[name])
    recorded = f"\nhas_reference_data: {'true' if listed else 'false'}\n"
    assert recorded in (dst / ".copier-answers.yml").read_text()
    for rel in paths(SCAFFOLD, VARIANTS[name]):
        assert (dst / rel).exists() is listed, f"{name}: {rel}"


@pytest.mark.parametrize("name", ["tenants", "tenants-keyless"])
def test_a_multi_tenant_source_packages_no_reference_data(
    template_src: Path, tmp_path: Path, name: str
) -> None:
    """#301: the reference scaffold's refresh fetches through the one client of a source
    with one tenant, so copier refuses a multi-tenant source that answers true, the default,
    rather than render a script that imports no client."""
    answers = {**VARIANTS[name], "has_reference_data": True}
    with pytest.raises(ValueError, match="has_reference_data"):
        generate(template_src, tmp_path / "repo", **answers)


def test_a_source_without_reference_data_renders_none_of_it(without_reference: Path) -> None:
    """#40: ``has_reference_data: false`` renders none of the scaffold, no file of the render
    names it, its CLAUDE.md's code rules among them (#243), and the generated code stays
    lint and format clean."""
    dst = without_reference
    rendered = [rel for rel in paths(SCAFFOLD, VARIANTS["keyed-nested"]) if (dst / rel).exists()]
    assert rendered == []
    assert "\nhas_reference_data: false\n" in (dst / ".copier-answers.yml").read_text()
    named = []
    for path in sorted(dst.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(dst).parts:
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if NAMED.search(line):
                    named.append(f"{path.relative_to(dst)}:{number}: {line}")
    assert not named, "\n".join(named)
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr


def test_add_endpoint_without_reference_data_exempts_a_countrys_codes(
    without_reference: Path,
) -> None:
    """#270, sdk-core ADR-0056: with no packaged list to name a country's codes by,
    ``/add-endpoint`` hands such a parameter to ``UNNAMED_CODES``, the exemption that core's
    family check reads, and names core's other helpers as every render does; the test
    above holds that it names none of ``LIST_HELPERS``."""
    add = (without_reference / ".claude/commands/add-endpoint.md").read_text()
    flat = " ".join(add.split())
    assert [helper for helper in TASK_HELPERS if helper not in flat] == []
    assert [helper for helper in LIST_HELPERS if helper in flat] == []


def test_an_update_brings_no_reference_scaffold_back(template_src: Path, tmp_path: Path) -> None:
    """#40: copier recreates a file under ``_skip_if_exists`` that a source deleted, so a
    source that deleted the scaffold gets some of it back at an update (copier 9.19.1 the
    script, whose pattern names no answer). With the answer false, the update leaves all
    of it out, and so does every later one, which reads the recorded answer."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    git(template, "init", "-q", "-b", "main")
    for tag in ["v0.0.1", "v0.0.2", "v0.0.3"]:
        (template / "RELEASE").write_text(f"{tag}\n")
        git(template, "add", "-A")
        git(template, "commit", "-q", "--no-verify", "-m", tag)
        git(template, "tag", tag)
    answers = VARIANTS["keyless-flat"]
    dst = tmp_path / "repo"
    data = {**BASE_ANSWERS, **answers}
    run_copy(str(template), str(dst), data=data, defaults=True, vcs_ref="v0.0.1", quiet=True)
    for rel in paths(FILLED, answers):
        (dst / rel).unlink()
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source that packages no reference data")
    unanswered = tmp_path / "unanswered"
    shutil.copytree(dst, unanswered)
    run_update(str(unanswered), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    back = [rel for rel in paths(FILLED, answers) if (unanswered / rel).exists()]
    assert back, "without the answer, the update brings back what the source deleted"
    # A source that kept the scaffold, a line of its own in params.py and a packaged list of
    # its own beside the rendered files: the answer deletes what the template rendered, the
    # source's lines in it included, and leaves the source's own file for it to delete.
    kept = tmp_path / "kept"
    run_copy(str(template), str(kept), data=data, defaults=True, vcs_ref="v0.0.1", quiet=True)
    pkg = kept / "src/xippios" / package_dir(answers)
    with (pkg / "params.py").open("a") as params:
        params.write('UNITS = "unit"\n')
    (pkg / "reference/unit.json").write_text("{}\n")
    git(kept, "init", "-q", "-b", "main")
    git(kept, "add", "-A")
    git(kept, "commit", "-q", "--no-verify", "-m", "a source with a list of its own")
    run_update(
        str(kept),
        data={"has_reference_data": False},
        defaults=True,
        overwrite=True,
        vcs_ref="v0.0.2",
        quiet=True,
    )
    assert [rel for rel in paths(FILLED, answers) if (kept / rel).exists()] == []
    assert (pkg / "reference/unit.json").read_text() == "{}\n", "the source's own file"
    scaffold = paths(SCAFFOLD, answers)
    run_update(
        str(dst),
        data={"has_reference_data": False},
        defaults=True,
        overwrite=True,
        vcs_ref="v0.0.2",
        quiet=True,
    )
    assert [rel for rel in scaffold if (dst / rel).exists()] == []
    assert "\nhas_reference_data: false\n" in (dst / ".copier-answers.yml").read_text()
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "the answer")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.3", quiet=True)
    assert [rel for rel in scaffold if (dst / rel).exists()] == [], "the recorded answer"


def test_the_readme_names_the_scaffold_with_its_answer() -> None:
    """This README's generated tree names each path of the scaffold on a line that names
    ``has_reference_data``, so no line lists one among the files every render has."""
    readme = (ROOT / "README.md").read_text()
    tree = readme.split("\n## What gets generated\n", 1)[1].split("```", 2)[1]
    scaffold = re.compile(r"\bparams\b|\benums\b|\breference/|refresh.reference")
    unqualified = [
        line
        for line in tree.splitlines()
        if scaffold.search(line) and "has_reference_data" not in line
    ]
    assert unqualified == []


def identifiers(tree: ast.Module) -> set[str]:
    """Every name ``tree`` reads, assigns, imports or takes as an attribute."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            found |= {alias.name for alias in node.names}
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
    return found


@pytest.mark.parametrize("name", LISTED)
def test_the_refresh_runs_on_cores_frame(name: str, render: Callable[[str], Path]) -> None:
    """#64, #239, sdk-core ADR-0051: the rendered script declares its lists in ``LISTS``
    and hands them to core's frame, ``xippios.core.refresh.run``, with the package, the
    lists it ships, the package's one client, which its fetches go through, and the quota
    header. The frame sends each request once and counts it, one that fails in transport
    too, and takes ``--only`` and ``--render-only``, so the script keeps no retry, meter,
    option or write of its own, and no branch of a multi-tenant source, which packages no
    reference data (#301). Its examples name wrappers in snake case, as ``/add-endpoint``
    names them."""
    text = (render(name) / "scripts/refresh_reference.py").read_text()
    script = ast.parse(text)
    frame = [
        alias.name
        for node in script.body
        if isinstance(node, ast.ImportFrom) and node.module == "xippios.core.refresh"
        for alias in node.names
    ]
    assert frame == ["Listed", "run"]
    (call,) = [
        node
        for node in ast.walk(script)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "run"
    ]
    assert [ast.unparse(argument) for argument in call.args] == ["LISTS", "argv"]
    assert {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords} == {
        "package": "PACKAGE",
        "packaged": "PACKAGED_LISTS",
        "client": "client",
        "quota_header": "QUOTA_HEADER",
    }
    assert {"DEMO", "client_for", "fetches", "sys"} & identifiers(script) == set()
    own = {"RetryPolicy", "replace", "observe", "argparse", "render_enums", "PackagedList"}
    assert own & identifiers(script) == set(), "core's frame does them"
    wrappers = re.findall(r"\bapi\.(\w+)", text)
    assert wrappers, "the examples name wrappers"
    assert [name for name in wrappers if not re.fullmatch(r"[a-z][a-z0-9_]*", name)] == []


@pytest.mark.parametrize("name", LISTED)
def test_the_live_tests_collect_cores_comparison(name: str, render: Callable[[str], Path]) -> None:
    """#252, sdk-core ADR-0055: the rendered ``tests/test_live.py`` collects core's nightly
    comparison of the packaged lists by one star import of ``xippios.core.testing.live``,
    with ``LIVE_LISTS`` and ``NO_LIVE_LIST`` declared empty at its top level, where core's
    family check reads them, and its top level skips, fails and exits nowhere. A render
    without reference data collects none of it, as ``NAMED`` holds."""
    tree = ast.parse((render(name) / "tests/test_live.py").read_text())
    stars = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and [alias.name for alias in node.names] == ["*"]
    ]
    assert stars == ["xippios.core.testing.live"]
    declared = {
        node.target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    }
    assert {name: declared.get(name) for name in ["LIVE_LISTS", "NO_LIVE_LIST"]} == {
        "LIVE_LISTS": {},
        "NO_LIVE_LIST": {},
    }
    stops = [
        ast.unparse(node)
        for statement in tree.body
        if not isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        for node in ast.walk(statement)
        if isinstance(node, ast.Call) and ast.unparse(node.func) in STOPS
    ]
    assert stops == [], "the family check imports the module offline"


def test_the_command_names_what_a_new_list_declares(keyless_flat: Path) -> None:
    """#252, sdk-core ADR-0051 and ADR-0055: ``/refresh-reference-data`` declares a new
    list as a ``Listed`` of the script's ``LISTS``, names it in ``PACKAGED_LISTS`` and
    gives it its entry in ``LIVE_LISTS`` or ``NO_LIVE_LIST`` of ``tests/test_live.py``,
    which core's family check holds; the 0.4.0 script's dicts are gone."""
    text = (keyless_flat / ".claude/commands/refresh-reference-data.md").read_text()
    for name in ["Listed", "LISTS", "PACKAGED_LISTS", "LIVE_LISTS", "NO_LIVE_LIST"]:
        assert f"`{name}`" in text, name
    assert "`tests/test_live.py`" in text
    assert [name for name in ["ID_LISTS", "TABLES"] if f"`{name}`" in text] == []
