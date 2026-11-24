"""The general part of a repository without tasks and servers, the template's second shape
(ADR-0003): what its render holds and leaves out, the answers it asks and records, the
manifest that is the repository's once rendered, the repository's name, and the commands and
documents it renders without a source's steps.

Each test reads the renders of ``conftest.py``, the general shape's two and a source's, or
renders a template snapshot of its own, and asserts mechanics: a file rendered or not, an
answer recorded or not, a name present or absent, what an update writes. ``scripts/prove.sh``
proves the two renders with their checks.
"""

import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from copier import run_copy, run_update
from helpers import (
    BASE_ANSWERS,
    GENERAL,
    QUESTIONS,
    RELEASE_SCRIPTS,
    ROOT,
    VARIANTS,
    copier_patterns,
    git,
    package_dir,
    ruff,
    skip_matcher,
)

# What the general shape renders: the general part of a repository around a package with its
# version, and one test of the package's own; the sibling check where the import path nests.
GENERAL_FILES = [
    ".claude/commands/release-prep.md",
    ".claude/rules/never.md",
    ".claude/settings.json",
    ".copier-answers.yml",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/adr-index.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/conventions.yml",
    ".github/workflows/publish.yml",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".python-version",
    ".secrets.baseline",
    "CHANGELOG.md",
    "CLAUDE.md",
    "LICENSE",
    "README.md",
    "changelog/README.md",
    "docs/adr.json",
    "docs/adr.md",
    "docs/adr/README.md",
    "docs/layout.md",
    "docs/reports/README.md",
    "pyproject.toml",
    "scripts/adr_index.py",
    "scripts/changelog_assemble.py",
    "scripts/release_prepare.py",
    "src/xippios/{pkg}/__init__.py",
    "src/xippios/{pkg}/_version.py",
    "src/xippios/{pkg}/py.typed",
    "tests/conftest.py",
    "tests/test_package.py",
]
SIBLING_FILES = [".github/scripts/check-siblings.sh", ".github/workflows/siblings.yml"]

# The eight questions of an upstream and of the package contract's variants, which the general
# shape does not answer, and the answers it records: the shape, the repository's name and the
# six that every repository of the family answers.
SOURCE_QUESTIONS = [
    "upstream_url",
    "upstream_docs_url",
    "api_key_env",
    "write_server",
    "tenant_param",
    "live_secrets",
    "has_files",
    "has_reference_data",
]
GENERAL_ANSWERS = {
    "shape",
    "source_slug",
    "repository_name",
    "import_path",
    "source_name",
    "core_version",
    "core_git_ref",
    "source_dependencies",
}
# The files the general shape renders whose text the answers write for the repository: none
# names an upstream, since the package wraps none.
ANSWERED_FILES = [
    "README.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    ".claude/commands/release-prep.md",
    ".claude/rules/never.md",
    "docs/layout.md",
    "src/xippios/{pkg}/__init__.py",
    "tests/conftest.py",
]


def answers_of(name: str) -> dict[str, object]:
    return {**BASE_ANSWERS, **{**VARIANTS, **GENERAL}[name]}


def repository(name: str) -> str:
    answers = answers_of(name)
    return str(answers.get("repository_name", f"sdk-{answers['source_slug']}"))


def rendered_files(dst: Path) -> list[str]:
    caches = {".ruff_cache", "__pycache__"}
    return sorted(
        p.relative_to(dst).as_posix()
        for p in dst.rglob("*")
        if p.is_file() and not caches & set(p.relative_to(dst).parts)
    )


def test_the_general_shape_renders_the_general_part_alone(general: tuple[str, Path]) -> None:
    """#302: the render holds CI, the publish workflow, the organization's two checks, the
    changelog with its scripts, the decision records' files and ``/release-prep`` around a
    package with its version and ``py.typed``, the sibling check where the import path nests,
    and one test of the package's own; no client, task, server, fixture or live workflow."""
    name, dst = general
    pkg = package_dir(GENERAL[name])
    expected = [path.format(pkg=pkg) for path in GENERAL_FILES]
    if "/" in pkg:
        expected += SIBLING_FILES
    assert rendered_files(dst) == sorted(expected)
    empty = [p for p in dst.rglob("*") if p.is_dir() and not any(p.iterdir())]
    assert empty == [], "no directory of a source's file is left empty"


def test_the_shape_leaves_out_the_27_files_of_a_source(render: Callable[[str], Path]) -> None:
    """ADR-0003: one list of ``_exclude`` names the files the general shape leaves out, each a
    file or a directory that a source's render holds, so a step that renames one of them
    changes the list; a source's render excludes nothing."""
    pkg = package_dir(VARIANTS["keyed-nested"])
    left_out = copier_patterns("_exclude", pkg, "general")
    assert len(left_out) == 27, left_out
    assert copier_patterns("_exclude", pkg, "source") == []
    held: set[str] = set()
    for name in ["keyed-nested", "dependency", "tenants"]:
        dst = render(name)
        own = package_dir(VARIANTS[name])
        held |= {
            f.replace(f"src/xippios/{own}/", f"src/xippios/{pkg}/") for f in rendered_files(dst)
        }
    for pattern in left_out:
        path = pattern.lstrip("/")
        assert [f for f in held if f == path or f.startswith(path + "/")], pattern


def test_the_general_shape_records_no_answer_of_an_upstream(general: tuple[str, Path]) -> None:
    """#302: the questions of an upstream are hidden by their condition, so copier records none
    of them, and the render records the shape, the repository's name and the six answers
    every repository of the family gives."""
    name, dst = general
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert {key for key in answers if not key.startswith("_")} == GENERAL_ANSWERS
    assert answers["shape"] == "general"
    assert answers["repository_name"] == repository(name)


def test_a_source_records_the_shape_at_its_default(variant: tuple[str, Path]) -> None:
    """#302: each source records the new answer at its default, as ``write_server`` and
    ``has_files`` came, and no repository's name, which is ``sdk-<slug>`` for a source."""
    _, dst = variant
    answers = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert answers["shape"] == "source"
    assert "repository_name" not in answers
    assert set(SOURCE_QUESTIONS) <= set(answers)


def test_the_questions_take_the_shape_as_their_condition() -> None:
    """ADR-0003: the shape is a choice of two names, ``source`` by default, asked first; the
    eight questions of an upstream are a source's and the repository's name the general
    shape's, each by its ``when``; 16 answers are recorded and 10 computed."""
    names = [name for name in QUESTIONS if not name.startswith("_")]
    assert names[0] == "shape"
    shape = QUESTIONS["shape"]
    assert (shape["choices"], shape["default"]) == (["source", "general"], "source")
    for name in SOURCE_QUESTIONS:
        assert QUESTIONS[name]["when"] == "{{ shape == 'source' }}", name
    assert QUESTIONS["repository_name"]["when"] == "{{ shape == 'general' }}"
    assert QUESTIONS["repository_name"]["default"] == "sdk-{{ source_slug }}"
    computed = [name for name in names if QUESTIONS[name].get("when") is False]
    assert (len(names) - len(computed), len(computed)) == (16, 10)


def test_the_repository_name_reaches_the_urls_and_the_publisher(general: tuple[str, Path]) -> None:
    """#302: the package's three URLs, the trusted publisher that ``/release-prep`` names and
    the README's links name the repository by its answer, and no URL names an upstream."""
    name, dst = general
    repo = repository(name)
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]
    urls = project["urls"]
    assert sorted(urls) == ["Changelog", "Homepage", "Issues"]
    home = f"https://github.com/xippios/{repo}"
    assert [url for url in urls.values() if not url.startswith(home)] == []
    release = (dst / ".claude/commands/release-prep.md").read_text()
    assert f"repository `{repo}`" in " ".join(release.split())
    links = re.findall(r"https://github\.com/xippios/([\w-]+)/", (dst / "README.md").read_text())
    assert set(links) == {"sdk-core", repo}
    assert (dst / "CLAUDE.md").read_text().startswith(f"# {repo} ")


def test_the_manifest_holds_no_server_and_is_the_repositorys(general: tuple[str, Path]) -> None:
    """#302: the general shape's ``pyproject.toml`` declares no entry point and no server's
    extra, takes ``source_name`` as its description, and is the repository's once rendered,
    under ``_skip_if_exists``, while a source's stays the template's."""
    name, dst = general
    project = tomllib.loads((dst / "pyproject.toml").read_text())["project"]
    assert "scripts" not in project
    assert sorted(project["optional-dependencies"]) == ["testing"]
    assert project["description"] == GENERAL[name]["source_name"]
    pkg = package_dir(GENERAL[name])
    assert skip_matcher(pkg, "general")("pyproject.toml")
    assert not skip_matcher(pkg, "source")("pyproject.toml")
    assert skip_matcher(pkg, "general")("tests/test_package.py"), "the repository's own test"


def test_an_update_never_writes_the_general_shapes_manifest(
    template_src: Path, tmp_path: Path
) -> None:
    """#302: an update of a repository of the general shape keeps its ``pyproject.toml``, its
    own lines in it included, and takes no line the template adds there, while it writes the
    template's files as for a source."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    git(template, "init", "-q", "-b", "main")
    git(template, "add", "-A")
    git(template, "commit", "-q", "--no-verify", "-m", "a release")
    git(template, "tag", "v0.0.1")
    dst = tmp_path / "repo"
    answers = answers_of("general-flat")
    run_copy(str(template), str(dst), data=answers, defaults=True, vcs_ref="v0.0.1", quiet=True)
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a repository")
    own = '\n[project.scripts]\nexample-tool = "xippios.example.cli:main"\n'
    with (dst / "pyproject.toml").open("a") as file:
        file.write(own)
    git(dst, "commit", "-q", "--no-verify", "-a", "-m", "its own script")
    manifest = (dst / "pyproject.toml").read_text()
    new = "# A line of the template's next release.\n"
    for rel in ["template/pyproject.toml.jinja", "template/.github/workflows/ci.yml"]:
        with (template / rel).open("a") as file:
            file.write(new)
    git(template, "commit", "-q", "--no-verify", "-a", "-m", "the next release")
    git(template, "tag", "v0.0.2")
    run_update(str(dst), defaults=True, vcs_ref="v0.0.2", overwrite=True, quiet=True)
    assert (dst / "pyproject.toml").read_text() == manifest
    assert (dst / ".github/workflows/ci.yml").read_text().endswith(new), "the template's file"
    status = git(dst, "status", "--porcelain").split()
    assert sorted(status) == sorted(["M", ".copier-answers.yml", "M", ".github/workflows/ci.yml"])


# A numbered step of a command, at the start of its line.
STEP = re.compile(r"^(\d+)\. ", re.MULTILINE)


def test_release_prep_has_no_step_of_a_source(
    general: tuple[str, Path], keyed_nested: Path
) -> None:
    """#302: the general shape's ``/release-prep`` renders without the steps that take a pin
    out by the template's answers, refresh reference data and cite a live run, since its
    manifest is its own and it has neither lists nor ``live.yml``; its steps are numbered
    from 1, as a source's nine are."""
    _, dst = general
    release = (dst / ".claude/commands/release-prep.md").read_text()
    assert [int(n) for n in STEP.findall(release)] == list(range(1, 7))
    for absent in ["live.yml", "core_git_ref", "/refresh-reference-data", "has_reference_data"]:
        assert absent not in release, absent
    source = (keyed_nested / ".claude/commands/release-prep.md").read_text()
    assert [int(n) for n in STEP.findall(source)] == list(range(1, 10))


def test_the_general_render_names_no_upstream(general: tuple[str, Path]) -> None:
    """#302: nothing the answers write for a repository of the general shape calls its
    package a source of an upstream: its README, CLAUDE.md, changelog, commands, rules,
    layout, package and conftest name no upstream, and its Never file keeps the rules that
    hold without one."""
    name, dst = general
    pkg = package_dir(GENERAL[name])
    for rel in ANSWERED_FILES:
        text = (dst / rel.format(pkg=pkg)).read_text()
        assert "upstream" not in text.lower(), rel
    never = (dst / ".claude/rules/never.md").read_text()
    rules = never.split("\n- ")[1:]
    assert len(rules) == 4, rules
    for absent in ["mcp.py", "fixture", "docs/upstream"]:
        assert absent not in never, absent


def test_the_general_render_is_lint_clean_and_free_of_jinja(general: tuple[str, Path]) -> None:
    """The render passes ruff and its format check, and holds no Jinja: only the workflows'
    ``${{ }}`` and the release scripts' doubled braces, copied verbatim, remain."""
    _, dst = general
    check = ruff(dst, "check", ".")
    assert check.returncode == 0, check.stdout + check.stderr
    fmt = ruff(dst, "format", "--check", ".")
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr
    for rel in rendered_files(dst):
        text = (dst / rel).read_text()
        assert "{%" not in text, rel
        if not rel.startswith(".github/workflows/") and rel not in RELEASE_SCRIPTS:
            assert "{{" not in text, rel


def test_the_package_test_reads_the_package_and_its_distribution(
    general: tuple[str, Path],
) -> None:
    """#302: the one test the shape renders imports the package and compares its version with
    its distribution's, a module of the repository's own under ``_skip_if_exists``; the
    render's own suite runs it, as ``scripts/prove.sh`` does."""
    name, dst = general
    test = (dst / "tests/test_package.py").read_text()
    import_path = package_dir(GENERAL[name]).replace("/", ".")
    assert f"import xippios.{import_path}\n" in test
    assert f'version("xippios-{GENERAL[name]["source_slug"]}")' in test


@pytest.mark.parametrize("name", list(VARIANTS))
def test_a_source_renders_no_package_test(name: str, render: Callable[[str], Path]) -> None:
    """A source's render holds no ``tests/test_package.py``: its tests are core's family check
    and the tasks' own."""
    assert not (render(name) / "tests/test_package.py").exists()


def test_this_readme_lays_out_the_general_shape(general: tuple[str, Path]) -> None:
    """#300, #302: the files of a repository of the general shape are described once, in this
    README: each file the render holds stands by its name in the tree of a source's files or
    in the section of the general shape."""
    _, dst = general
    readme = (ROOT / "README.md").read_text()
    tree = readme.split("\n## What gets generated\n", 1)[1].split("\n## ", 1)[0]
    missing = []
    for rel in rendered_files(dst):
        stem = Path(rel).stem if rel.startswith(".claude/commands/") else Path(rel).name
        if not re.search(rf"(?<![\w.-]){re.escape(stem)}(?![\w-])", tree):
            missing.append(rel)
    assert missing == []
    assert "### The general part of a repository" in tree
