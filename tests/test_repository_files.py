"""The repository's small files of a render: the scaffold's changelog entry, the attributes
and the ignores git reads, the samples' provenance table, and the minor the sibling check
reads from the wheel's version.

Each test reads the renders of ``conftest.py`` or runs a piece of a template file, and asserts
mechanics: a line present or absent, a column counted, what git or bash does with the file.
The sibling check's outcomes need PyPI, so ``scripts/prove.sh`` runs them.
"""

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from helpers import ROOT, VARIANTS, dependencies, git, has_files

# A dependency's item in the scaffold's entry: the package, the release its bound starts at,
# and the bound, as pyproject.toml declares it.
DEPENDENCY_ITEM = re.compile(r"^- .*`(xippios-[a-z0-9-]+)` (\d+\.\d+\.\d+) \(`~=([\d.]+)`\)", re.M)


def test_the_scaffold_entry_names_each_dependencys_release_and_bound(
    variant: tuple[str, Path],
) -> None:
    """#53: a dependent's CHANGELOG names the release of each source package it depends on
    (sdk-core ADR-0021 decision 4), so the scaffold's entry under Added names each with its bound,
    in the order of the answer, as ``pyproject.toml`` declares it; a source with no dependency
    names none."""
    name, dst = variant
    changelog = (dst / "CHANGELOG.md").read_text()
    unreleased = changelog.split("## [Unreleased]\n", 1)[1].split("\n## [", 1)[0]
    added = unreleased.split("### Added\n", 1)[1].split("\n### ", 1)[0]
    minors = [(f"xippios-{d['name']}", d["minor"]) for d in dependencies(VARIANTS[name])]
    expected = [(package, f"{minor}.0", f"{minor}.0") for package, minor in minors]
    assert DEPENDENCY_ITEM.findall(added) == expected
    assert DEPENDENCY_ITEM.findall(changelog) == expected, "under Added alone"
    pyproject = (dst / "pyproject.toml").read_text()
    for package, _, bound in expected:
        assert f'"{package}~={bound}",' in pyproject


SNAPSHOT_LINE = "docs/upstream/** -text"
SAMPLES_LINE = "tests/fixtures/files/** -text"


def test_git_keeps_the_samples_byte_for_byte_where_the_source_parses_files(
    variant: tuple[str, Path], tmp_path: Path
) -> None:
    """#62: a sample under ``tests/fixtures/files/`` is cut byte for byte, its sha256 in its
    provenance row (sdk-core ADR-0020 decision 6), so ``.gitattributes`` unsets ``text`` for the
    samples where ``has_files`` is true, as for the snapshot: a CRLF sample added under
    ``core.autocrlf`` keeps its CRLF in the index. A render without ``has_files`` keeps the
    snapshot's line alone."""
    name, dst = variant
    parses = has_files(VARIANTS[name])
    lines = (dst / ".gitattributes").read_text().splitlines()
    assert lines == [SNAPSHOT_LINE, *([SAMPLES_LINE] if parses else [])]
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(dst / ".gitattributes", repo / ".gitattributes")
    git(repo, "init", "-q", "-b", "main")
    sample = "tests/fixtures/files/report_txt/latest.txt"
    (repo / sample).parent.mkdir(parents=True)
    (repo / sample).write_bytes(b"Commodity,Value\r\nWheat,1\r\n")
    git(repo, "-c", "core.autocrlf=true", "add", sample)
    (eol,) = git(repo, "ls-files", "--eol", "--", sample).splitlines()
    assert eol.split()[0] == ("i/crlf" if parses else "i/lf"), eol


def test_the_render_ignores_its_local_files(keyed_nested: Path, tmp_path: Path) -> None:
    """#84: ``.local/`` holds what a source keeps for its operator alone, such as a curated
    list, a probe cache or a report, and is never committed: the ``.gitignore`` names it, and
    git lists no file under it as untracked."""
    assert ".local/" in (keyed_nested / ".gitignore").read_text().splitlines()
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(keyed_nested / ".gitignore", repo / ".gitignore")
    git(repo, "init", "-q", "-b", "main")
    (repo / ".local/probe").mkdir(parents=True)
    (repo / ".local/probe/accounts.json").write_text("[]\n")
    (repo / "notes.md").write_text("kept\n")
    untracked = git(repo, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert "?? notes.md" in untracked
    assert not [line for line in untracked if ".local" in line], untracked


def pipe_rows(text: str) -> list[list[str]]:
    """The cells of each line of a Markdown pipe table in ``text``."""
    rows = [line.strip() for line in text.splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]


def test_the_samples_table_says_what_each_sample_keeps(render: Callable[[str], Path]) -> None:
    """#168: a sample's row says what of the file the sample keeps, a sample a script wrote
    from a file over the cap among them (sdk-core ADR-0020, amendment 2026-11-18, point d): the
    skeleton's table ends in that column, ``Kept``, and each of its lines has the header's
    cells."""
    dst = render("dependency")
    header, *rows = pipe_rows((dst / "tests/fixtures/files/README.md").read_text())
    assert header[-1] == "Kept"
    assert [len(row) for row in rows] == [len(header)] * len(rows)
    assert len(rows) == 2, "the rule and the placeholder row"


SIBLINGS_SCRIPT = (
    ROOT
    / "template/.github/{% if '.' in import_path or depends_on %}scripts{% endif %}"
    / "check-siblings.sh"
)


def shell_function(script: str, name: str) -> str:
    """A function of a bash script, from its ``name() {`` line to its closing brace."""
    start = script.index(f"\n{name}() {{\n") + 1
    return script[start : script.index("\n}\n", start) + 3]


@pytest.mark.parametrize(
    ("version", "previous"),
    [("0.2.0", "0.1"), ("0.2.3", "0.1"), ("0.10.1", "0.9"), ("0.1.0", "0.0"), ("1.0.0", "")],
)
def test_the_sibling_check_reads_the_previous_minor(version: str, previous: str) -> None:
    """#74: a sibling that pins this package's previous minor adopts the new minor in its own
    package (conventions §12), so the check leaves it out with a warning; the previous minor
    is the one below the wheel's, and a major's first minor has none."""
    function = shell_function(SIBLINGS_SCRIPT.read_text(), "previous_minor")
    run = subprocess.run(
        ["bash", "-c", f'set -euo pipefail\n{function}previous_minor "$1"', "bash", version],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == (f"{previous}\n" if previous else "")


def test_the_sibling_check_tells_a_pin_by_resolved_versions() -> None:
    """#74, as D87 tells a sibling on another core minor: the minor a sibling pins is the
    release of this package it resolves to on its own, and the pin is its one conflict when
    it installs beside the wheel with its requirement on this package overridden by the
    wheel; the warning names the pin. ``scripts/prove.sh`` runs both outcomes."""
    lines = SIBLINGS_SCRIPT.read_text().splitlines()
    (override,) = [line for line in lines if "--override" in line]
    assert '"$work/override.txt"' in override
    (written,) = [line for line in lines if line.rstrip().endswith('> "$work/override.txt"')]
    assert "@ file://" in written
    assert '"$distribution" "${wheel[0]}"' in written
    (warning,) = [line for line in lines if 'echo "::warning::${requirement}: pins' in line]
    assert '${distribution} $(minor "$pinned").*' in warning
