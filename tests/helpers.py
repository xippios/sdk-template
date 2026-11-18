"""What the template tests share: the family's variants and their answers, the render, and
the tools a test runs on a render (ruff, git, copier's skip matcher).

``conftest.py`` renders each variant once per session from these answers; a test module
imports what it reads from here.
"""

import hashlib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import yaml
from copier import run_copy
from pathspec import PathSpec

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = yaml.safe_load((ROOT / "copier.yml").read_text())
CORE_DEFAULT = str(QUESTIONS["core_version"]["default"])

BASE_ANSWERS: dict[str, object] = {
    "source_name": "Example Data Service",
    "upstream_url": "https://api.example.org",
    "upstream_docs_url": "https://api.example.org/docs",
    "api_base_url": "https://api.example.org/v1",
    "rate_limit_per_minute": 120,
}


# A stand-in for a 40-character sdk-core commit, never fetched: hex of high entropy, as a
# real SHA is, computed so that no literal in this file looks like a secret.
FAKE_CORE_SHA = hashlib.sha1(b"a fixed stand-in for an sdk-core commit").hexdigest()


def keyed(env: str, location: str = "query", name: str | None = None) -> dict[str, object]:
    """Answers for how the key is sent; values are variables so no line looks like a secret."""
    answers: dict[str, object] = {"api_key_env": env, "api_key_location": location}
    if name is not None:
        answers["api_key_name"] = name
    return answers


# What the api.data.gov gateway answer derives (ADR-0009): the key's variable, its
# location and its header, recorded as if answered.
DATA_GOV = "api.data.gov"
GATEWAY_KEY = keyed("DATA_GOV_API_KEY", "header", "X-Api-Key")


def gateway_of(answers: dict[str, object]) -> str:
    return str(answers.get("gateway", "none"))


def key_answers(answers: dict[str, object]) -> dict[str, object]:
    """The three key answers a render reads: the gateway's where it is set, else as given."""
    if gateway_of(answers) == DATA_GOV:
        return GATEWAY_KEY
    return {k: v for k, v in answers.items() if k.startswith("api_key_")}


# The family's variants (T11 as narrowed): the shapes its sources take. Their pace answers
# differ so that both provenances and a burst render; the key locations, a core pin and a
# name at its bound are answers of their own, each tested by its rule in test_template.py.
VARIANTS: dict[str, dict[str, object]] = {
    # sdk-usda-nass's shape: a key of its own, sent as a query parameter, and a nested
    # import path (ADR-0006); no gateway, answered as such.
    "keyed-nested": {
        "source_slug": "usda-nass",
        "gateway": "none",
        **keyed("NASS_API_KEY", "query", "key"),
    },
    # sdk-eurostat's: no key, a flat import path.
    "keyless-flat": {
        "source_slug": "eurostat",
        "rate_limit_provenance": "self-imposed",
        **keyed(""),
    },
    # sdk-usda-esmis's (and sdk-usda-wasde's): no key, a nested import path; with the
    # 64-character name that broke four docstrings' line length (row 60), which
    # test_generated_code_is_lint_and_format_clean checks with every other file.
    "keyless-nested": {
        "source_slug": "usda-esmis",
        "source_name": "USDA ESMIS (Economics, Statistics and Market Information System)",
        "rate_limit_burst": 3,
        "rate_limit_provenance": "self-imposed",
        **keyed(""),
    },
    # sdk-usda-wasde's, as it will start (ADR-0021): no key, a nested import path, and the
    # source packages it depends on, one open and one keyed, whose variable then reaches
    # the offline placeholder and live.yml (D47); the first parser package, it parses the
    # files it downloads (ADR-0020), so has_files renders parse/ and the samples' table.
    "dependency": {
        "source_slug": "usda-wasde",
        "source_dependencies": (
            '[{name: example-base, minor: "0.3", key_env: ""},'
            ' {name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'
        ),
        "has_files": True,
        **keyed(""),
    },
    # sdk-usda-psd's (and sdk-usda-esr's and sdk-usda-gats's): behind the api.data.gov
    # gateway (T9, ADR-0009), which derives the key answers, so none is passed; nested.
    "gateway": {
        "source_slug": "usda-psd",
        "gateway": DATA_GOV,
        "rate_limit_per_minute": 60,
        "rate_limit_provenance": "self-imposed",
    },
}
# A source on unreleased core: the keyed nested answers with a full-SHA core pin.
PINNED = {**VARIANTS["keyed-nested"], "core_git_ref": FAKE_CORE_SHA}


def package_dir(answers: dict[str, object]) -> str:
    import_path = str(answers.get("import_path") or str(answers["source_slug"]).replace("-", "."))
    return import_path.replace(".", "/")


def dependencies(answers: dict[str, object]) -> list[dict[str, str]]:
    """The source packages a variant depends on, parsed from its answer (ADR-0021)."""
    parsed = yaml.safe_load(str(answers.get("source_dependencies", "[]")))
    assert isinstance(parsed, list)
    return parsed


def has_files(answers: dict[str, object]) -> bool:
    """Whether a variant parses the files it downloads (ADR-0020); copier's default no."""
    return answers.get("has_files", False) is True


def key_envs(answers: dict[str, object]) -> list[str]:
    """Every key variable a render reads: the source's own, then its dependencies', once."""
    own = str(key_answers(answers).get("api_key_env", ""))
    keys = [own] + [d["key_env"] for d in dependencies(answers)]
    return list(dict.fromkeys(key for key in keys if key))


def live_secrets(answers: dict[str, object]) -> list[str]:
    """The other variables a render's live run reads (#105), parsed from its answer; none at
    the default, which every variant takes."""
    parsed = yaml.safe_load(str(answers.get("live_secrets", "[]")))
    assert isinstance(parsed, list)
    return parsed


def generate(template_src: Path, dst: Path, **answers: object) -> Path:
    run_copy(
        str(template_src),
        str(dst),
        data={**BASE_ANSWERS, **answers},
        defaults=True,
        overwrite=True,
        quiet=True,
    )
    return dst


def ruff(dst: Path, command: str, *args: str) -> subprocess.CompletedProcess[str]:
    """``ruff <command>`` in ``dst``, writing no cache into a render the tests share."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", command, "--no-cache", *args],
        cwd=dst,
        capture_output=True,
        text=True,
        check=False,
    )


def skip_matcher(pkg: str) -> Callable[[str], bool]:
    """Whether copier's ``_skip_if_exists`` protects a path, matched as copier 9.19.1 does:
    the patterns rendered, read as gitignore lines by pathspec."""
    rendered = [p.replace("{{ package_dir }}", pkg) for p in QUESTIONS["_skip_if_exists"]]
    return PathSpec.from_lines("gitignore", rendered).match_file


def git(cwd: Path, *args: str) -> str:
    """git with a fixed identity and no signing, independent of the user's configuration."""
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    unsigned = ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    return subprocess.run(
        ["git", *identity, *unsigned, *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout
