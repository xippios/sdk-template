"""The citations of sdk-core's records (#155): a render cites a record of sdk-core as
``sdk-core ADR-NNNN``, on one line, by the number of the record that stands at the core
release the template adopts, since a bare ``ADR-NNNN`` is a record of the repository's own,
as the render's ``docs/adr/README.md`` lays them out. So do this repository's own files,
which keep records of their own under ``docs/adr/``.

The files a render copies from sdk-core cite sdk-core's records inside sdk-core and stay
core's bytes, and ``docs/adr/README.md`` defines the form. Each test reads the files or
the renders of ``conftest.py`` and asserts the mechanic: a number, the name before it.
"""

import re
from collections.abc import Iterator
from pathlib import Path

from helpers import ROOT

# A citation, its number, and the name of sdk-core before it on its line, if any.
CITATION = re.compile(r"(sdk-core )?\bADR-(\d{4})\b")

# The files a render copies from sdk-core byte for byte, which cite core's records inside
# core, and the README that defines how a repository cites its own.
CORE_BYTES = {
    ".github/workflows/ci.yml",
    ".github/workflows/publish.yml",
    ".pre-commit-config.yaml",
    ".secrets.baseline",
    ".python-version",
    "LICENSE",
}
EXEMPT = CORE_BYTES | {"docs/adr/README.md"}

# The records that sdk-core's index, docs/adr.md at its tag v0.4.0, the core release the
# template adopts, lists as superseded, each with the record that stands in its place.
SUPERSEDED = {
    "0003": "0028",
    "0004": "0029",
    "0005": "0030",
    "0008": "0031",
    "0009": "0032",
    "0010": "0033",
    "0012": "0034",
    "0013": "0035",
    "0014": "0036",
    "0015": "0037",
    "0016": "0038",
    "0018": "0039",
    "0019": "0040",
    "0022": "0041",
    "0024": "0042",
}

# This repository's own files that cite records: its documents, its questions, its scripts
# and its workflows. The tests are left out, since they write records of a render's own.
OWN = ["README.md", "CLAUDE.md", "copier.yml", "scripts", ".github", ".claude"]


def citations(root: Path, rel: str) -> Iterator[tuple[str, bool, str]]:
    """Each citation of a file under ``root``: where it stands, whether sdk-core's name
    comes before it on its line, and its number."""
    text = (root / rel).read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), 1):
        for match in CITATION.finditer(line):
            yield f"{rel}:{number}", match.group(1) is not None, match.group(2)


def files(root: Path, *names: str) -> list[str]:
    """The files under ``root``, or under the names given there, as paths relative to it."""
    paths = [root / name for name in names] if names else [root]
    found = []
    for path in paths:
        for file in [path] if path.is_file() else sorted(path.rglob("*")):
            rel = file.relative_to(root).as_posix()
            if file.is_file() and not {".git", "__pycache__"} & set(Path(rel).parts):
                found.append(rel)
    return found


def test_a_render_cites_sdk_cores_records_by_name(variant: tuple[str, Path]) -> None:
    """Plan proof 5 of 0.4.0: no file of a render but core's bytes and
    ``docs/adr/README.md`` holds a bare ``ADR-NNNN``, in each of the family's variants."""
    _, render = variant
    bare = [
        f"{where}: ADR-{number}"
        for rel in files(render)
        if rel not in EXEMPT
        for where, named, number in citations(render, rel)
        if not named
    ]
    assert bare == []


def test_every_branch_of_the_template_cites_sdk_cores_records_by_name() -> None:
    """The template's files, the branches that no variant renders among them, a pace set
    under a documented limit or a key sent in a header, hold no bare ``ADR-NNNN`` but in
    core's bytes and ``docs/adr/README.md``."""
    template = ROOT / "template"
    bare = [
        f"{where}: ADR-{number}"
        for rel in files(template)
        if rel not in EXEMPT
        for where, named, number in citations(template, rel)
        if not named
    ]
    assert bare == []


def test_this_repositorys_bare_citations_name_its_own_records() -> None:
    """This repository keeps records of its own under ``docs/adr/``, so a bare
    ``ADR-NNNN`` in its own files names one of them, and sdk-core's carry sdk-core's name."""
    own = {path.name[:4] for path in (ROOT / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")}
    foreign = [
        f"{where}: ADR-{number}"
        for rel in files(ROOT, *OWN)
        for where, named, number in citations(ROOT, rel)
        if not named and number not in own
    ]
    assert foreign == []


def test_no_citation_names_a_record_that_core_superseded() -> None:
    """A citation of sdk-core's names the record that stands at v0.4.0, never one that
    sdk-core's index lists as superseded, in the template's files but core's bytes and in
    this repository's own."""
    template = ROOT / "template"
    cited = [
        (where, number)
        for rel in files(template)
        if rel not in CORE_BYTES
        for where, named, number in citations(template, rel)
        if named
    ] + [
        (where, number)
        for rel in files(ROOT, *OWN)
        for where, named, number in citations(ROOT, rel)
        if named
    ]
    stale = [
        f"{where}: ADR-{n}, which ADR-{SUPERSEDED[n]} supersedes"
        for where, n in cited
        if n in SUPERSEDED
    ]
    assert stale == []
