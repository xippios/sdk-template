"""The client's answers: the key sent as the basic-auth user name, a pace set under a limit
upstream documents, and the rule of one limiter per host, which takes no answer (#162, #46,
#79).

``scripts/prove.sh -d api_key_location=basic -d rate_limit_provenance=below-documented``
proves such a render on core: its checks, and the header its client sends.
"""

import ast
import re
from pathlib import Path

import pytest
import yaml
from helpers import QUESTIONS, ROOT, VARIANTS, generate, keyed, ruff

# A keyed source whose key goes as the HTTP basic user name, paced under a limit upstream
# documents: the two values the step adds, in one render.
BASIC: dict[str, object] = {
    "source_slug": "ex",
    "rate_limit_provenance": "below-documented",
    **keyed("EX_API_KEY", "basic"),
}
CLIENT = "src/xippios/ex/_client.py"
ADD_ENDPOINT = ".claude/commands/add-endpoint.md"


@pytest.fixture(scope="module")
def basic(template_src: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The render of ``BASIC``, shared by this module's tests, which write nothing into it."""
    return generate(template_src, tmp_path_factory.mktemp("basic") / "repo", **BASIC)


def row(dst: Path, name: str) -> str:
    """The row of the rendered ``CLAUDE.md``'s facts table that ``name`` heads."""
    (found,) = [
        line
        for line in (dst / "CLAUDE.md").read_text().splitlines()
        if line.startswith(f"| {name} | ")
    ]
    return found


def blocks(text: str) -> list[str]:
    """``text`` cut into its paragraphs, list items and numbered steps, whitespace folded."""
    parts = re.split(r"\n\s*\n|\n(?=\s*(?:- |\d+\. ))", text)
    return [" ".join(part.split()) for part in parts]


def test_copier_offers_basic_and_below_documented() -> None:
    """#162 and #46: ``api_key_location`` offers ``basic`` after the three it had, and
    ``rate_limit_provenance`` ``below-documented`` between its two, ``documented`` still
    the default; the README's questions table names both."""
    locations = QUESTIONS["api_key_location"]["choices"]
    assert list(locations.values()) == ["query", "header", "bearer", "basic"]
    provenances = QUESTIONS["rate_limit_provenance"]["choices"]
    assert list(provenances.values()) == ["documented", "below-documented", "self-imposed"]
    assert QUESTIONS["rate_limit_provenance"]["default"] == "documented"
    readme = (ROOT / "README.md").read_text().splitlines()
    for question, value in [
        ("api_key_location", "basic"),
        ("rate_limit_provenance", "below-documented"),
    ]:
        (line,) = [line for line in readme if line.startswith(f"| `{question}` |")]
        assert f"`{value}`" in line, question


def test_basic_sends_the_key_as_the_basic_user_name(basic: Path) -> None:
    """#173: ``basic`` renders core's ``BasicKeyAuth`` on the key's variable, imported from
    ``xippios.core`` and exported, in a ruff-clean ``_client.py``; no parameter or header
    name is asked or recorded, and the credentials row names the variable and basic auth."""
    client = (basic / CLIENT).read_text()
    (core,) = [
        node
        for node in ast.parse(client).body
        if isinstance(node, ast.ImportFrom) and node.module == "xippios.core"
    ]
    assert "BasicKeyAuth" in [alias.name for alias in core.names]
    assert "\nauth = BasicKeyAuth(API_KEY_ENV, source=SOURCE)\n" in client
    assert "client = AsyncClient(config, auth=auth)" in client
    assert '    "auth",\n' in client, "auth is exported"
    for args in [("check",), ("format", "--check")]:
        run = ruff(basic, *args, CLIENT)
        assert run.returncode == 0, run.stdout + run.stderr
    answers = yaml.safe_load((basic / ".copier-answers.yml").read_text())
    assert answers["api_key_location"] == BASIC["api_key_location"]
    assert "api_key_name" not in answers, "a basic user name has no parameter or header"
    credentials = row(basic, "Credentials")
    assert credentials.startswith("| Credentials | `EX_API_KEY` from the environment, sent ")
    assert "basic" in credentials


def test_each_provenance_renders_its_own_comment_and_row(
    basic: Path, keyed_nested: Path, keyless_flat: Path
) -> None:
    """#177: ``below-documented`` renders the comment above ``RATE_LIMIT`` and the
    provenance of the ``Rate limit`` row each of its own, neither the documented one nor
    the self-imposed one, and the row leaves the source a comment to fill with the
    documented limit, beside the pace."""
    renders = {"below-documented": basic, "documented": keyed_nested, "self-imposed": keyless_flat}
    assert VARIANTS["keyed-nested"].get("rate_limit_provenance", "documented") == "documented"
    assert VARIANTS["keyless-flat"]["rate_limit_provenance"] == "self-imposed"
    comments: dict[str, str] = {}
    provenances: dict[str, str] = {}
    for provenance, dst in renders.items():
        lines = next(dst.glob("src/xippios/**/_client.py")).read_text().splitlines()
        (pace,) = [i for i, line in enumerate(lines) if line.startswith("RATE_LIMIT = ")]
        comments[provenance] = lines[pace - 1]
        found = re.search(r"burst \d+; (.+?) \(sdk-core ", row(dst, "Rate limit"))
        assert found, provenance
        provenances[provenance] = found[1]
    assert all(comment.startswith("# ") for comment in comments.values()), comments
    assert len(set(comments.values())) == len(renders), comments
    assert len(set(provenances.values())) == len(renders), provenances
    assert "self-imposed" not in comments["below-documented"]
    assert "self-imposed" not in provenances["below-documented"]
    assert "<!--" in provenances["below-documented"], "the documented limit, the source's"
    assert "<!--" not in provenances["documented"]


def test_no_answer_names_a_second_host() -> None:
    """#172: a second host is a constant in the source's own ``_client.py``, so
    ``copier.yml`` asks for one base URL and one pace, and for no host."""
    questions = [name for name in QUESTIONS if not name.startswith("_")]
    assert [name for name in questions if "url" in name and "base" in name] == ["api_base_url"]
    assert not [name for name in questions if "host" in name]
    assert [name for name in questions if name.startswith("rate_limit_")] == [
        "rate_limit_per_minute",
        "rate_limit_burst",
        "rate_limit_provenance",
    ]


def test_claude_md_and_add_endpoint_state_one_limiter_per_host(variant: tuple[str, Path]) -> None:
    """#172, conventions §2 and §6: the rendered ``CLAUDE.md`` and ``/add-endpoint`` each
    state the rule in one paragraph, the one that names ``RateLimit``: it names
    ``_client.py``, where a second host's client and pace go, ``classify``, whose path
    checks name a second base on the first host, and ``docs/upstream/``, which names a
    mirror's host beside its canonical one; ``/add-endpoint``'s names ``CLAUDE.md``, where
    the host's row goes."""
    name, dst = variant
    for rel, names in [
        ("CLAUDE.md", ["`_client.py`", "`classify`", "`docs/upstream/`"]),
        (ADD_ENDPOINT, ["`_client.py`", "`classify`", "`docs/upstream/`", "`CLAUDE.md`"]),
    ]:
        (rule,) = [block for block in blocks((dst / rel).read_text()) if "`RateLimit`" in block]
        for named in ["conventions §2", "§6", *names]:
            assert named in rule, f"{name}: {rel}: {named}"
