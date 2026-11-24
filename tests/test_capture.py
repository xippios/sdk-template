"""The capture script, ``scripts/refresh_upstream.py``, as a render holds it: the declaration
it hands core's snapshot frame, the command that fills it, the stub of ``FETCHED.md`` and the
rule of the render's Never file.

xippios-core 0.5.0's frame, ``xippios.core.refresh``, fetches, checks the attribution, writes
``FETCHED.md`` and compares with ``--check`` (sdk-core ADR-0062), and core's own tests hold
what it does. These tests read the render, and ``scripts/prove.sh`` runs the rendered script
on core's frame.
"""

import ast
import re
import sys
from pathlib import Path

from helpers import BASE_ANSWERS, NEVER_FILE, ROOT, VARIANTS

FRAME = "xippios.core.refresh"
# The last line of a FETCHED.md that core's frame wrote, which names the file's form (sdk-core
# ADR-0062, decision 8): a fresh render carries none until its first refresh writes the file.
FORM_MARK = re.compile(r"<!-- form \d+ of the FETCHED\.md that xippios\.core\.refresh writes -->")
# The fields of the declaration a source fills, which the render declares and the command names.
FILLED = ["pages", "attribution", "not_fetched", "vocabulary", "capture"]
# The hooks a source adds where it needs them, which the command names and the render leaves to
# their defaults: a snapshot that links no page declares no linked (sdk-core ADR-0062),
# and one whose pages need no converter no reduce, whose default keeps the body as fetched (#300).
ADDED = ["canonical", "linked", "reduce"]


def flat(text: str) -> str:
    return " ".join(text.split())


def top_level(script: str) -> list[ast.stmt]:
    return ast.parse(script).body


def snapshot_call(body: list[ast.stmt]) -> ast.Call:
    """The call that the script's top level assigns to ``SNAPSHOT``."""
    (call,) = [
        node.value
        for node in body
        if isinstance(node, ast.Assign)
        and [target.id for target in node.targets if isinstance(target, ast.Name)] == ["SNAPSHOT"]
        and isinstance(node.value, ast.Call)
    ]
    assert isinstance(call, ast.Call)
    return call


def keywords(call: ast.Call) -> dict[str, ast.expr]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}


def test_the_script_declares_its_snapshot_to_core_s_frame(variant: tuple[str, Path]) -> None:
    """ADR-0062 of sdk-core: the script imports core's frame, assigns its ``Snapshot`` to
    ``SNAPSHOT`` at its top level, which imports and declares alone, and runs it under
    ``if __name__ == "__main__":`` alone, so it sends nothing while it loads. Its pages are
    empty until the source fills them, and it declares no ``linked`` while it links no page.
    It runs in the project's environment, with no ``# /// script`` block, and defines no
    function of its own: the scaffold's ``reduce`` has left for core's default (#300)."""
    name, dst = variant
    answers = {**BASE_ANSWERS, **VARIANTS[name]}
    script = (dst / "scripts/refresh_upstream.py").read_text()
    assert "# /// script" not in script
    body = top_level(script)
    imported: set[str] = set()
    for node in body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
    assert FRAME in imported
    others = {module for module in imported - {FRAME} if module not in sys.stdlib_module_names}
    assert not others, others
    for node in body:
        allowed = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef)
        docstring = isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        main = isinstance(node, ast.If) and ast.unparse(node.test) == "__name__ == '__main__'"
        assert isinstance(node, allowed) or docstring or main, ast.unparse(node)
    assert not [node.name for node in body if isinstance(node, ast.FunctionDef)]
    (guard,) = [node for node in body if isinstance(node, ast.If)]
    assert [ast.unparse(node) for node in guard.body] == ["raise SystemExit(run(SNAPSHOT))"]
    call = snapshot_call(body)
    assert ast.unparse(call.func) == "Snapshot"
    declared = keywords(call)
    assert ast.literal_eval(declared["name"]) == answers["source_name"]
    assert ast.literal_eval(declared["slug"]) == answers["source_slug"]
    assert ast.literal_eval(declared["pages"]) == (), "core's frame refuses to run until filled"
    for field in FILLED:
        assert field in declared, field
    for field in ADDED:
        assert field not in declared, field


def test_refresh_upstream_command_follows_the_declaration(keyless_flat: Path) -> None:
    """The command names the fields of ``SNAPSHOT`` a source fills, the hooks it adds where it
    needs them, core's helpers, the records it fills them with, the page kinds, ``--check``,
    the hand-written file and the samples (#123, sdk-core ADR-0062); a keyed sample's
    credentials are the source's own client's, whose variables the declaration names
    (sdk-core#483); the converter is the project's, so the command names no ``# /// script``
    block (sdk-core ADR-0062, decision 1). ``--check`` is the one comparison, so the command
    names no family check of ``FETCHED.md`` (#310)."""
    command = flat((keyless_flat / ".claude/commands/refresh-upstream.md").read_text())
    assert "`SNAPSHOT`" in command
    assert f"`{FRAME}`" in command
    for name in [*FILLED, *ADDED, "read_json", "dump_json", "changed"]:
        assert f"`{name}`" in command, name
    for name in ["Page", "Statement", "NotFetched"]:
        assert f"`{name}(" in command, name
    for keyword in ["status=403", "status=302", "stable=False", "excerpt=True", "terms=True"]:
        assert keyword in command, keyword
    for keyword in ["sample=True", "names=", "keyed=True", "`--keyless`", "client=", "variables="]:
        assert keyword in command, keyword
    assert "family check" not in command, "#310"
    assert "uv run scripts/refresh_upstream.py --check" in command
    assert "# /// script" not in command
    for name in ["`pyproject.toml`", "`uv.lock`", "`html.parser`", "`MarkdownConverter`"]:
        assert name in command, name
    for name in ["`docs/upstream/OBSERVED.md`", "`Not fetched`", "`docs/upstream/samples/`"]:
        assert name in command, name
    assert "`git add docs/upstream scripts`" in command, "row 35 a"


def test_the_stub_leaves_the_file_to_core_s_frame(keyless_flat: Path) -> None:
    """#300: FETCHED.md's stub holds its title and one paragraph, which names the script that
    writes the file whole, and none of the sections and tables that core's frame writes at
    the first refresh. It carries no mark of the frame's form, which the first refresh writes
    with the file (sdk-core ADR-0062, decisions 6 and 8)."""
    stub = (keyless_flat / "docs/upstream/FETCHED.md").read_text()
    title, *blocks = [block for block in stub.split("\n\n") if block.strip()]
    assert title.startswith("# "), title
    assert "\n" not in title, title
    assert len(blocks) == 1, "one paragraph"
    assert "`scripts/refresh_upstream.py`" in stub
    assert "\n## " not in stub
    assert "|" not in stub, "no table of the frame's"
    assert not FORM_MARK.search(stub)


def test_the_rule_on_the_snapshot_leaves_the_notes_to_the_hand(keyless_flat: Path) -> None:
    """Conventions §3: the render's Never file forbids a hand edit of ``docs/upstream/`` but
    for OBSERVED.md, which the command and core's frame name as the one file so written. The
    template's README, whose tree lays out the family's files, names the declaration the
    script holds for core's frame (#240, #300)."""
    never = flat((keyless_flat / NEVER_FILE).read_text())
    (rule,) = [line for line in never.split("- Never ") if line.startswith("edit `docs/upstream/`")]
    assert "`docs/upstream/OBSERVED.md`" in rule
    readme = (ROOT / "README.md").read_text()
    tree = flat(readme.split("\n## What gets generated\n", 1)[1].split("```", 2)[1])
    entry = tree.split("refresh_upstream.py ", 1)[1].split(" adr_index.py ", 1)[0]
    assert "SNAPSHOT" in entry, entry
    assert FRAME in entry, entry


def test_no_rendered_test_reads_observed_md(variant: tuple[str, Path]) -> None:
    """#236: core 0.4.1's family check holds the row of OBSERVED.md in FETCHED.md in every
    source that keeps the file (sdk-core ADR-0044), so the render's own tests read neither,
    ``tests/test_family.py`` collecting that check in one line."""
    _, dst = variant
    tests = sorted((dst / "tests").rglob("*.py"))
    assert dst / "tests/test_family.py" in tests
    for path in tests:
        text = path.read_text()
        assert "OBSERVED" not in text, path.name
        assert "FETCHED" not in text, path.name
