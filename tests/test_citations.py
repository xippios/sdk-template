"""The citations of sdk-core's records (#155): a render cites a record of sdk-core as
``sdk-core ADR-NNNN``, on one line, by the number of the record that stands at the core
release the template adopts, since a bare ``ADR-NNNN`` is a record of the repository's own,
as the render's ``docs/adr/README.md`` lays them out. So do this repository's own files,
which keep records of their own under ``docs/adr/``.

The files a render copies from sdk-core cite sdk-core's records inside sdk-core and stay
core's bytes, but the lines the template adds to ``ci.yml`` and ``publish.yml``, and
``docs/adr/README.md`` defines the form. ``scripts/adr_index.py`` holds the bytes that the
organization's repositories share, whose docstring gives ``ADR-0014`` as the example of an
anchor and cites no record (#246). Each test reads the files or the renders of
``conftest.py`` and asserts the mechanic: a number, the name before it.
"""

import re
from collections.abc import Iterator
from pathlib import Path

from helpers import CI_STEPS, CORE_DEFAULT, FETCH_DEPTH, PUBLISH_STEP, ROOT

# A citation, its number, and the name of sdk-core before it on its line, if any.
CITATION = re.compile(r"(sdk-core )?\bADR-(\d{4})\b")

# The files a render copies from sdk-core, which cite core's records inside core but on the
# lines the template adds to two of them.
CORE_BYTES = {
    ".github/workflows/ci.yml",
    ".github/workflows/publish.yml",
    ".pre-commit-config.yaml",
    ".secrets.baseline",
    ".python-version",
    "LICENSE",
}

# The files that the tests of bare citations leave out: docs/adr/README.md, which defines the
# form of a citation, and the organization's one index script, whose bytes no repository edits.
NO_CITATIONS = {"docs/adr/README.md", "scripts/adr_index.py"}

# The records that sdk-core's index, docs/adr.md at its tag v0.5.0, the core release the
# template adopts, lists as superseded, each with the record that stands in its place. The
# adoption of another core release brings the map to that release's index and SUPERSEDED_AT
# to its version, which test_the_superseded_records_are_those_of_the_adopted_core asks.
SUPERSEDED_AT = "0.5.0"
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
    "0023": "0059",
    "0024": "0042",
    "0046": "0062",
    "0048": "0066",
    "0049": "0064",
    "0051": "0062",
    "0056": "0067",
    "0057": "0066",
}

# This repository's own files that cite records: its documents, its questions, its scripts
# and its workflows. The tests are left out, since they write records of a render's own.
OWN = ["README.md", "CLAUDE.md", "copier.yml", "scripts", ".github", ".claude"]


def own_lines(rel: str, text: str) -> set[int]:
    """The numbers of the lines the template adds to a file it copies from sdk-core: in
    ``ci.yml`` the full history and the two steps that read the pull request, in
    ``publish.yml`` the refusal of a git-pinned core, as ``tests/test_template.py`` takes
    them out before it compares the rest with core's digest; none in the other four."""
    spans = []
    if rel == ".github/workflows/ci.yml":
        start = text.index(FETCH_DEPTH)
        spans.append((start, start + len(FETCH_DEPTH)))
        start = text.index(CI_STEPS[0])
        spans.append((start, text.index(CI_STEPS[1], start)))
    elif rel == ".github/workflows/publish.yml":
        start = text.index(PUBLISH_STEP[0])
        spans.append((start, text.index(PUBLISH_STEP[1], start)))
    return {
        text.count("\n", 0, offset) + 1
        for first, stop in spans
        for offset in range(first, stop)
        if offset == first or text[offset - 1] == "\n"
    }


def citations(root: Path, rel: str, rendered: bool = True) -> Iterator[tuple[str, bool, str]]:
    """Each citation of a file under ``root``, of a file a render copies from sdk-core those
    on the template's own lines alone: where it stands, whether sdk-core's name comes before
    it on its line, and its number. This repository's own files are no render's."""
    text = (root / rel).read_text(encoding="utf-8")
    own = own_lines(rel, text) if rendered and rel in CORE_BYTES else None
    for number, line in enumerate(text.splitlines(), 1):
        if own is not None and number not in own:
            continue
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
    ``NO_CITATIONS`` holds a bare ``ADR-NNNN``, the template's own lines of ``ci.yml``
    and ``publish.yml`` included, in each of the family's variants."""
    _, render = variant
    bare = [
        f"{where}: ADR-{number}"
        for rel in files(render)
        if rel not in NO_CITATIONS
        for where, named, number in citations(render, rel)
        if not named
    ]
    assert bare == []


def test_every_branch_of_the_template_cites_sdk_cores_records_by_name() -> None:
    """The template's files, the branches that no variant renders among them, a pace set
    under a documented limit or a key sent in a header, hold no bare ``ADR-NNNN`` but in
    core's bytes and ``NO_CITATIONS``."""
    template = ROOT / "template"
    bare = [
        f"{where}: ADR-{number}"
        for rel in files(template)
        if rel not in NO_CITATIONS
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
        if rel not in NO_CITATIONS
        for where, named, number in citations(ROOT, rel, rendered=False)
        if not named and number not in own
    ]
    assert foreign == []


def test_no_citation_names_a_record_that_core_superseded() -> None:
    """A citation of sdk-core's names the record that stands at 0.5.0, never one that
    sdk-core's index lists as superseded, in the template's files but core's bytes and in
    this repository's own."""
    template = ROOT / "template"
    cited = [
        (where, number)
        for rel in files(template)
        for where, named, number in citations(template, rel)
        if named
    ] + [
        (where, number)
        for rel in files(ROOT, *OWN)
        for where, named, number in citations(ROOT, rel, rendered=False)
        if named
    ]
    stale = [
        f"{where}: ADR-{n}, which ADR-{SUPERSEDED[n]} supersedes"
        for where, n in cited
        if n in SUPERSEDED
    ]
    assert stale == []


def test_the_superseded_records_are_those_of_the_adopted_core() -> None:
    """The map of superseded records is sdk-core's index at the core release the template
    adopts, so an adoption that moves ``core_version``'s default fails here until the map
    and ``SUPERSEDED_AT`` follow the new release's index."""
    assert CORE_DEFAULT == SUPERSEDED_AT, "bring SUPERSEDED to sdk-core's docs/adr.md there"
