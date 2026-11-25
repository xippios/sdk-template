"""The general part of a repository without tasks and servers, the template's second shape
(ADR-0003): what its render holds and leaves out, the answers it asks and records, the
manifest that is the repository's once rendered, the repository's name, the client file of a
package that holds a key, and the commands and documents it renders without a source's steps.

Each test reads the renders of ``conftest.py``, the general shape's two and a source's, or
renders a template snapshot of its own, and asserts mechanics: a file rendered or not, an
answer recorded or not, a name present or absent, what an update writes. ``scripts/prove.sh``
proves the two renders with their checks.
"""

import ast
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
    BUILT_ANSWERS,
    BUILT_ANSWERS_LINE,
    GENERAL,
    QUESTIONS,
    RELEASE_SCRIPTS,
    ROOT,
    VARIANTS,
    assigned,
    copier_patterns,
    entries,
    env_vars,
    generate,
    git,
    key_answers,
    keyed,
    module,
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

# The seven questions of an upstream and of the package contract's variants, which the general
# shape does not answer, and the answers it records: the shape, the repository's name, the key
# its package holds, empty where it holds none (sdk-core#538), and the six that every
# repository of the family answers.
SOURCE_QUESTIONS = [
    "upstream_url",
    "upstream_docs_url",
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
    "api_key_env",
    "core_version",
    "core_git_ref",
    "source_dependencies",
}
# The client file of a package that holds a key (sdk-core#538), at the import path's
# directories: its key in ENV_VARS, and no client of the template's.
CLIENT_FILE = "src/xippios/{pkg}/_client.py"
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


def holds_a_key(name: str) -> bool:
    """Whether a render's package holds a key, by its answer (sdk-core#538)."""
    return bool(key_answers(GENERAL[name]).get("api_key_env"))


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
    the client file and core's built-answer check where the package holds a key
    (sdk-core#538, #351), and one test of the package's own; no client, task, server, fixture
    or live workflow."""
    name, dst = general
    pkg = package_dir(GENERAL[name])
    expected = [path.format(pkg=pkg) for path in GENERAL_FILES]
    if "/" in pkg:
        expected += SIBLING_FILES
    if holds_a_key(name):
        expected += [CLIENT_FILE.format(pkg=pkg), BUILT_ANSWERS]
    assert rendered_files(dst) == sorted(expected)
    empty = [p for p in dst.rglob("*") if p.is_dir() and not any(p.iterdir())]
    assert empty == [], "no directory of a source's file is left empty"


def test_the_shape_leaves_out_the_27_files_of_a_source(render: Callable[[str], Path]) -> None:
    """ADR-0003: one list of ``_exclude`` names the files the general shape leaves out, each a
    file or a directory that a source's render holds, so a step that renames one of them
    changes the list; a source's render excludes nothing. A package that holds a key keeps
    ``_client.py`` and ``tests/test_built_answers.py`` alone of them (sdk-core#538, #351)."""
    pkg = package_dir(VARIANTS["keyed-nested"])
    left_out = copier_patterns("_exclude", pkg, "general")
    assert len(left_out) == 27, left_out
    kept = ["/" + CLIENT_FILE.format(pkg=pkg), "/" + BUILT_ANSWERS]
    keyed_left_out = copier_patterns("_exclude", pkg, "general", "EXAMPLE_API_KEY")
    assert sorted([*keyed_left_out, *kept]) == sorted(left_out)
    assert copier_patterns("_exclude", pkg, "source") == []
    assert copier_patterns("_exclude", pkg, "source", "EXAMPLE_API_KEY") == []
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
    seven questions of an upstream are a source's and the repository's name the general
    shape's, each by its ``when``, while both shapes ask the key, empty by default
    (sdk-core#538); 16 answers are recorded and 10 computed."""
    names = [name for name in QUESTIONS if not name.startswith("_")]
    assert names[0] == "shape"
    shape = QUESTIONS["shape"]
    assert (shape["choices"], shape["default"]) == (["source", "general"], "source")
    for name in SOURCE_QUESTIONS:
        assert QUESTIONS[name]["when"] == "{{ shape == 'source' }}", name
    assert QUESTIONS["repository_name"]["when"] == "{{ shape == 'general' }}"
    assert QUESTIONS["repository_name"]["default"] == "sdk-{{ source_slug }}"
    assert "when" not in QUESTIONS["api_key_env"]
    assert QUESTIONS["api_key_env"]["default"] == ""
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


def test_a_package_that_holds_a_key_declares_it_in_its_client(general: tuple[str, Path]) -> None:
    """sdk-core#538: a package that holds a key renders ``_client.py``, which declares
    ``ENV_VARS`` with that key, imports ``EnvVar`` alone and holds no client of the template's,
    and which the repository fills, under ``_skip_if_exists``; the Never file names the key as
    the package's credential. A package that holds none renders no ``_client.py``."""
    name, dst = general
    answers = GENERAL[name]
    pkg = package_dir(answers)
    if not holds_a_key(name):
        assert not (dst / CLIENT_FILE.format(pkg=pkg)).exists()
        return
    key = str(answers["api_key_env"])
    assert entries(dst, answers) == env_vars(answers) == [(key, True, True)]
    tree = module(dst, answers, "_client.py")
    imports = [ast.unparse(n) for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)]
    assert imports == ["from xippios.core import EnvVar"]
    assert ast.literal_eval(assigned(tree, "__all__")) == ["API_KEY_ENV", "ENV_VARS"]
    assert skip_matcher(pkg, "general")(CLIENT_FILE.format(pkg=pkg)), "the repository's"
    assert f"`{key}`" in (dst / ".claude/rules/never.md").read_text()


def test_a_package_that_holds_a_key_collects_the_built_answer_check(
    general: tuple[str, Path],
) -> None:
    """#351: a package that holds a key, and so renders ``_client.py``, builds HTTP answers in
    its tests, which conventions §12 binds a shared package to mark by §10 (sdk-core
    ADR-0064): its render collects core's built-answer check by the one line a source's does,
    ``tests/test_built_answers.py`` whole, the repository's under ``_skip_if_exists``. A
    package that holds none renders no such module."""
    name, dst = general
    if not holds_a_key(name):
        assert not (dst / BUILT_ANSWERS).exists()
        return
    assert (dst / BUILT_ANSWERS).read_text() == BUILT_ANSWERS_LINE + "\n"
    assert skip_matcher(package_dir(GENERAL[name]), "general")(BUILT_ANSWERS), "the repository's"


# A dependency that holds a key, as a source's answer writes it (sdk-core ADR-0021).
KEYED_DEPENDENCY = '[{name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (
            "EXAMPLE_API_KEY",
            [("EXAMPLE_API_KEY", True, True), ("EXAMPLE_KEYED_API_KEY", True, True)],
        ),
        ("", None),
    ],
)
def test_the_packages_own_key_decides_its_client(
    template_src: Path,
    tmp_path: Path,
    key: str,
    expected: list[tuple[str, bool, bool]] | None,
) -> None:
    """sdk-core#538: the package's own key decides whether ``_client.py`` renders, and its
    ``ENV_VARS`` names the keys of the source packages it depends on after its own, as a
    source's does; a package that holds no key renders none, whatever its dependencies hold.
    The file passes ruff with several entries too."""
    answers = {**GENERAL["general-nested"], "source_dependencies": KEYED_DEPENDENCY, **keyed(key)}
    dst = generate(template_src, tmp_path / "repo", **answers)
    if expected is None:
        assert not (dst / CLIENT_FILE.format(pkg=package_dir(answers))).exists()
        return
    assert entries(dst, answers) == env_vars(answers) == expected
    for args in [("check", "."), ("format", "--check", ".")]:
        result = ruff(dst, *args)
        assert result.returncode == 0, result.stdout + result.stderr


def test_a_dependent_general_render_cites_section_12_for_its_release(
    template_src: Path, tmp_path: Path
) -> None:
    """#300: the general shape's ``/release-prep`` names the packages a dependent releases
    after, citing conventions §12, the section that holds the rule at core 0.5.0."""
    answers = {**GENERAL["general-nested"], "source_dependencies": KEYED_DEPENDENCY}
    dst = generate(template_src, tmp_path / "repo", **answers)
    release = " ".join((dst / ".claude/commands/release-prep.md").read_text().split())
    assert "`xippios-example-keyed`" in release
    assert "(sdk-core ADR-0021 decision 5, conventions §12)" in release


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
    for rel in ANSWERED_FILES + ([CLIENT_FILE] if holds_a_key(name) else []):
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
