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


# The table of the files and pages that FETCHED.md lists, as the capture skeleton writes it.
TABLE_HEADER = "| File | URL | Fetched | HTTP | Bytes | sha256 | ETag | Last-Modified | Note |"


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
    # sdk-cashctrl's (#174): a multi-tenant source with a write server, each tenant's key
    # sent as the basic user name (#173), its tenants named by org; flat.
    "tenants": {
        "source_slug": "cashctrl",
        "write_server": True,
        "tenant_param": "org",
        "rate_limit_provenance": "self-imposed",
        **keyed("CASHCTRL_API_KEY", "basic"),
    },
    # sdk-google-mail's (#207, #209): a multi-tenant source whose tenants hold a refresh
    # token, no key, under a prefix the slug does not give (GOOGLE, not GOOGLE_MAIL), with
    # a write server and the live secrets of its OAuth client; its tenants named by
    # account; nested.
    "tenants-keyless": {
        "source_slug": "google-mail",
        "write_server": True,
        "tenant_param": "account",
        "tenant_credential_env": "GOOGLE_<NAME>_REFRESH_TOKEN",
        "live_secrets": "[GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]",
        "rate_limit_burst": 10,
        "rate_limit_provenance": "self-imposed",
        **keyed(""),
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


def write_server(answers: dict[str, object]) -> bool:
    """Whether a variant has a write server (#174); copier's default no."""
    return answers.get("write_server", False) is True


def tenant_param(answers: dict[str, object]) -> str:
    """The parameter that names a multi-tenant variant's tenant (#174), else empty."""
    return str(answers.get("tenant_param", ""))


def tenant_credential(answers: dict[str, object]) -> str:
    """The pattern of a multi-tenant variant's credential variable, ``<PREFIX>_<NAME>_<FIELD>``
    (#209): its key's, ``<PREFIX>_<NAME>_API_KEY``, where it has a key, else its answer;
    empty for a source with one tenant."""
    if not tenant_param(answers):
        return ""
    key = str(key_answers(answers).get("api_key_env", ""))
    if key:
        return key.removesuffix("_API_KEY") + "_<NAME>_API_KEY"
    return str(answers["tenant_credential_env"])


def tenant_prefix(answers: dict[str, object]) -> str:
    """The prefix of a multi-tenant variant's variables: its credential's, before ``_<NAME>_``."""
    return tenant_credential(answers).split("_<NAME>_")[0]


def tenant_field(answers: dict[str, object]) -> str:
    """The field of a multi-tenant variant's credential, after ``_<NAME>_``, as core's
    ``Tenants(fields=...)`` takes it: ``API_KEY`` where it has a key."""
    credential = tenant_credential(answers)
    return credential.split("_<NAME>_")[1] if credential else ""


def key_envs(answers: dict[str, object]) -> list[str]:
    """Every key variable a render's tests and live run read: the source's own, the reserved
    tenant's credential for a multi-tenant source, then its dependencies', once."""
    if tenant_param(answers):
        own = f"{tenant_prefix(answers)}_DEMO_{tenant_field(answers)}"
    else:
        own = str(key_answers(answers).get("api_key_env", ""))
    keys = [own] + [d["key_env"] for d in dependencies(answers)]
    return list(dict.fromkeys(key for key in keys if key))


def env_vars(answers: dict[str, object]) -> list[tuple[str, bool, bool]]:
    """The variables a render's ``ENV_VARS`` declares, each with whether it is secret and
    required: the key, or the tenant list and the tenants' credential pattern, then the
    dependencies' keys and the live secrets, each once."""
    own = str(key_answers(answers).get("api_key_env", ""))
    if tenant_param(answers):
        prefix, param = tenant_prefix(answers), tenant_param(answers).upper()
        listed = [(f"{prefix}_{param}S", False, False), (tenant_credential(answers), True, True)]
    else:
        listed = [(own, True, True)] if own else []
    for name in [d["key_env"] for d in dependencies(answers)] + live_secrets(answers):
        if name and name not in [entry[0] for entry in listed]:
            listed.append((name, True, True))
    return listed


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


def detect_secrets_hook(directory: Path, *files: str) -> subprocess.CompletedProcess[str]:
    """The generated repository's detect-secrets hook, on ``files`` in ``directory``."""
    hook = [sys.executable, "-m", "detect_secrets.pre_commit_hook"]
    return subprocess.run(
        [*hook, "--baseline", ".secrets.baseline", *files],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )


def git(cwd: Path, *args: str) -> str:
    """git with a fixed identity and no signing, independent of the user's configuration."""
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    unsigned = ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    return subprocess.run(
        ["git", *identity, *unsigned, *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout
