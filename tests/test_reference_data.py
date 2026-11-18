"""Reference data: the answer that renders the scaffold or leaves it out, and the refresh
script that sends each request once, counts what it sent and takes ``--only`` (#40, #64).

``scripts/prove.sh`` runs the rendered script itself, on core, against answers it replays.
"""

import ast
import re
import shutil
from pathlib import Path

import pytest
from copier import run_copy, run_update
from helpers import BASE_ANSWERS, QUESTIONS, ROOT, VARIANTS, generate, git, package_dir, ruff

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
# How a render names the scaffold: a file, the folder, the script, the command, an import.
NAMED = re.compile(
    r"params\.py|enums\.py|\breference/|refresh_reference|refresh-reference-data"
    r"|\bxippios\.[\w.]+\.(?:params|enums)\b"
)


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
    variant renders the scaffold whole and records the answer."""
    name, dst = variant
    question = QUESTIONS["has_reference_data"]
    assert (question["type"], question["default"]) == ("bool", True)
    raw = (ROOT / "copier.yml").read_text().split("\nhas_reference_data:\n", 1)[1]
    block = raw[: re.search(r"^\S", raw, re.MULTILINE).start()]
    assert "\n  default: true\n" in block, "one plain scalar, a literal"
    assert "\nhas_reference_data: true\n" in (dst / ".copier-answers.yml").read_text()
    for rel in paths(SCAFFOLD, VARIANTS[name]):
        assert (dst / rel).exists(), f"{name}: {rel}"


def test_a_source_without_reference_data_renders_none_of_it(without_reference: Path) -> None:
    """#40: ``has_reference_data: false`` renders none of the scaffold, no file of the render
    names it, and the generated code stays lint and format clean."""
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


def test_the_refresh_sends_each_request_once_and_takes_only(keyed_nested: Path) -> None:
    """#64: the rendered script runs the package's client with ``RetryPolicy(max_attempts=1)``
    and its own ``observe`` hook, which counts what it sends; ``--only`` and
    ``--render-only`` are choices of one group; its examples name wrappers in snake case,
    as ``/add-endpoint`` names them."""
    text = (keyed_nested / "scripts/refresh_reference.py").read_text()
    script = ast.parse(text)
    calls = [node for node in ast.walk(script) if isinstance(node, ast.Call)]
    assert "RetryPolicy(max_attempts=1)" in [ast.unparse(call) for call in calls]
    (configured,) = [call for call in calls if ast.unparse(call.func) == "replace"]
    assert {keyword.arg for keyword in configured.keywords} == {"retry", "observe"}
    options = {
        ast.literal_eval(call.args[0]): ast.unparse(call.func.value)
        for call in calls
        if isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument"
    }
    assert set(options) == {"--only", "--render-only"}
    (group,) = set(options.values())
    groups = [
        target.id
        for node in ast.walk(script)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func).endswith(".add_mutually_exclusive_group")
        for target in node.targets
        if isinstance(target, ast.Name)
    ]
    assert groups == [group], "one choice of the two"
    wrappers = re.findall(r"\bapi\.(\w+)", text)
    assert wrappers, "the examples name wrappers"
    assert [name for name in wrappers if not re.fullmatch(r"[a-z][a-z0-9_]*", name)] == []
