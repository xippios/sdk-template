"""The release script (#247): ``scripts/release_prepare.py`` and the assembler it loads by its
path, ``scripts/changelog_assemble.py``, the organization's one version of each, which a
render carries byte for byte. They are the template's files, which an update writes again,
outside the render's ruff, and ``/release-prep`` runs the script in place of an assembly by
hand.

Each test reads the renders of ``conftest.py`` or runs the rendered script on a copy of one,
and asserts mechanics: a blob id, a name present, what the script writes and what it runs.
"""

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from helpers import RELEASE_SCRIPTS, ROOT, VARIANTS, git, package_dir, skip_matcher

# The git blob id of each script, as `git hash-object` gives it and as the tree of the
# organization's version lists it: a copy edited here would write another section than the
# organization's repositories write. The next version of a script changes its id.
BLOB_IDS = {
    # pragma: allowlist nextline secret
    "scripts/changelog_assemble.py": "e10263706fda4da3662f6fd598d17080826363fd",
    # pragma: allowlist nextline secret
    "scripts/release_prepare.py": "8e491fef4ccd7823d822dc75f5d8f7e75f16cd79",
}

# The one relaxation of the render's mypy: the assembler's bytes annotate one field as a bare
# `list`, which strict mypy refuses, and no copy edits them.
MYPY_OVERRIDE = {"module": ["scripts.changelog_assemble"], "disallow_any_generics": False}

# The command /release-prep runs, and the assembler's preview, which writes nothing.
PREPARE = "`python3 -I scripts/release_prepare.py <version> --date <YYYY-MM-DD>`"
NOTES = "`python3 -I scripts/changelog_assemble.py --notes`"

# The release the run prepares on a render, whose scaffold is 0.1.0, and the two changes it
# takes, each a fragment as changelog/README.md lays it out.
VERSION, DATE = "0.2.0", "2026-11-22"
FRAGMENTS = {
    "added-get-thing.md": "- `get_thing` returns one thing by its id.\n",
    "fixed-page-size.md": "- `list_things` asks for the page size upstream documents.\n",
}


def blob_id(data: bytes) -> str:
    """The id git gives a file's bytes, `git hash-object`'s."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def lock(name: str, version: str) -> str:
    """A ``uv.lock`` as ``uv lock`` writes one for a render: the package itself at ``.``
    and the core it depends on, from the index."""
    return (
        "version = 1\n"
        "revision = 3\n"
        'requires-python = ">=3.12"\n'
        "\n"
        "[[package]]\n"
        f'name = "{name}"\n'
        f'version = "{version}"\n'
        'source = { editable = "." }\n'
        "dependencies = [\n"
        '    { name = "xippios-core" },\n'
        "]\n"
        "\n"
        "[[package]]\n"
        'name = "xippios-core"\n'
        'version = "0.4.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    )


def snapshot(repo: Path) -> dict[str, bytes]:
    """Every file of ``repo`` but git's, by its path, with its bytes."""
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


def changed_lines(before: bytes, after: bytes) -> list[tuple[str, str]]:
    """The lines a write changed, each (before, after), of a file that kept its line count."""
    old, new = before.decode().splitlines(), after.decode().splitlines()
    assert len(old) == len(new), "the line count stands"
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def run(repo: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """A rendered script as a release runs it: ``python3 -I`` from the repository's root,
    the script finding the repository from its own path."""
    return subprocess.run(
        [sys.executable, "-I", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_release_scripts_are_core_s_bytes(keyed_nested: Path) -> None:
    """Each script the template renders holds the organization's bytes, executable as its
    first line says, and the render carries them unchanged as the template's files, which
    ``_skip_if_exists`` leaves to the update."""
    protected = skip_matcher(package_dir(VARIANTS["keyed-nested"]))
    for rel in RELEASE_SCRIPTS:
        source = ROOT / "template" / rel
        assert blob_id(source.read_bytes()) == BLOB_IDS[rel], rel
        assert os.access(source, os.X_OK), rel
        assert (keyed_nested / rel).read_bytes() == source.read_bytes(), rel
        assert os.access(keyed_nested / rel, os.X_OK), rel
        assert not protected(rel), f"{rel} is the template's"


def test_the_render_checks_the_scripts_as_they_stand(keyed_nested: Path) -> None:
    """The render's ruff leaves both scripts alone, as it does the index script, and its
    strict mypy checks them with the one relaxation that the assembler's bytes need."""
    tool = tomllib.loads((keyed_nested / "pyproject.toml").read_text())["tool"]
    for rel in RELEASE_SCRIPTS:
        assert rel in tool["ruff"]["extend-exclude"], rel
    assert "scripts" in tool["mypy"]["files"]
    assert tool["mypy"]["overrides"] == [MYPY_OVERRIDE]


def test_release_prep_runs_the_script(variant: tuple[str, Path]) -> None:
    """``/release-prep`` names the script with the version and the date, and the
    assembler's preview of the section, in every render."""
    _, dst = variant
    text = " ".join((dst / ".claude/commands/release-prep.md").read_text().split())
    assert PREPARE in text
    assert NOTES in text


def test_the_script_prepares_a_release_on_a_render(keyed_nested: Path, tmp_path: Path) -> None:
    """On a copy of a render with two fragments and a lock, the preview prints the section
    and writes nothing; the script writes the section, removes the fragments and sets the
    version in ``pyproject.toml`` and on the package's own entry in ``uv.lock``, each on
    its line alone, and runs no ``uv``; a second run writes nothing."""
    repo = tmp_path / "repo"
    shutil.copytree(keyed_nested, repo, ignore=shutil.ignore_patterns(".ruff_cache"))
    name = tomllib.loads((repo / "pyproject.toml").read_text())["project"]["name"]
    scaffold = tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"]
    (repo / "uv.lock").write_text(lock(name, scaffold))
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the render")
    for fragment, bullet in FRAGMENTS.items():
        (repo / "changelog" / fragment).write_text(bullet)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "two changes")
    # A uv ahead of the real one on the path, which leaves a mark where anything runs it.
    bin_dir, mark = tmp_path / "bin", tmp_path / "uv-ran"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(f"#!/bin/sh\ntouch {shlex.quote(str(mark))}\nexit 1\n")
    (bin_dir / "uv").chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    before = snapshot(repo)

    notes = run(repo, env, "scripts/changelog_assemble.py", "--notes")
    assert notes.returncode == 0, notes.stdout
    for bullet in FRAGMENTS.values():
        assert bullet.strip() in notes.stdout
    assert snapshot(repo) == before, "the preview writes nothing"

    prepared = run(repo, env, "scripts/release_prepare.py", VERSION, "--date", DATE)
    assert prepared.returncode == 0, prepared.stdout
    assert not mark.exists(), "the script ran uv"
    after = snapshot(repo)
    changelog = after["CHANGELOG.md"].decode()
    assert f"\n## [{VERSION}] - {DATE}\n" in changelog
    assert "## [Unreleased]" not in changelog
    for fragment, bullet in FRAGMENTS.items():
        assert bullet.strip() in changelog, fragment
        assert f"changelog/{fragment}" not in after, fragment
    assert "changelog/README.md" in after
    versioned = (f'version = "{scaffold}"', f'version = "{VERSION}"')
    for rel in ["pyproject.toml", "uv.lock"]:
        assert changed_lines(before[rel], after[rel]) == [versioned], rel
    packages = {
        p["name"]: p["version"] for p in tomllib.loads(after["uv.lock"].decode())["package"]
    }
    assert packages == {name: VERSION, "xippios-core": "0.4.0"}
    changed = {rel for rel in before.keys() | after.keys() if before.get(rel) != after.get(rel)}
    fragments = {f"changelog/{fragment}" for fragment in FRAGMENTS}
    assert changed == {"CHANGELOG.md", "pyproject.toml", "uv.lock", *fragments}

    again = run(repo, env, "scripts/release_prepare.py", VERSION, "--date", DATE)
    assert again.returncode == 0, again.stdout
    assert snapshot(repo) == after, "a second run writes nothing"
    assert not mark.exists(), "the second run ran uv"
