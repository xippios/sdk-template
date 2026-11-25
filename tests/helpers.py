"""What the template tests share: the family's variants and their answers, the render, and
the tools a test runs on a render (ruff, git, copier's skip matcher, the readers of a rendered
module's names).

``conftest.py`` renders each variant once per session from these answers; a test module
imports what it reads from here.
"""

import ast
import hashlib
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import jinja2
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
}


# The template's own lines of the two workflows it copies from sdk-core and extends, with
# no comment, as core's bytes carry none (#312): in ci.yml the full history for the two
# steps that read the pull request (core's handover at v0.4.1, "Template v0.2.1",
# https://github.com/xippios/sdk-core/blob/v0.4.1/docs/handover.md), in publish.yml the
# refusal of a git-pinned core before the tag.
FETCH_DEPTH = "          fetch-depth: 0\n"
CI_STEPS = (
    "      - name: The changelog has an entry",
    "      - uses: astral-sh/setup-uv@",
)
PUBLISH_STEP = (
    "      - name: Refuse a pyproject with [tool.uv.sources]",
    "      - name: Tag the merge commit",
)


# The rules no change of a render breaks, in a file of the template's that Claude Code loads
# at launch by its place, and the layout of what a source adds to the family's tree, the
# source's own, which the render's CLAUDE.md imports (#300, #233).
NEVER_FILE = ".claude/rules/never.md"
LAYOUT_FILE = "docs/layout.md"


# The release script and the assembler it loads, the organization's one version of each,
# which a render carries byte for byte (#247): the template's files, outside the render's
# ruff as the index script is.
RELEASE_SCRIPTS = ["scripts/changelog_assemble.py", "scripts/release_prepare.py"]


# Core 0.5.0's check of a built answer's mark (sdk-core ADR-0064): the module that core's
# handover names for it, and its collecting line as core's docstring gives it, alone. A
# source renders it, and so does a package of the general shape that holds a key.
BUILT_ANSWERS = "tests/test_built_answers.py"
BUILT_ANSWERS_LINE = "from xippios.core.testing.built_answers import *  # noqa: F403"


# A stand-in for a 40-character sdk-core commit, never fetched: hex of high entropy, as a
# real SHA is, computed so that no literal in this file looks like a secret.
FAKE_CORE_SHA = hashlib.sha1(b"a fixed stand-in for an sdk-core commit").hexdigest()


# The names of xippios-core 0.5.0 that /add-endpoint gives a new task where it meets them
# (#270, sdk-core#483), each as the command writes its call or its name, as sdk-core's main
# exports them from xippios.core: the mark of a code field's names (sdk-core#406), the walk of
# an offset-paged list and the one check of a download's destination. The two of
# LIST_HELPERS read a packaged list (sdk-core#384, sdk-core#406), so a render without
# reference data names neither.
LIST_HELPERS = ["`PackagedList.codes(", "`names_codes`"]
TASK_HELPERS = [
    "`NamedBy(",
    "`ResultCap(paged=True)`",  # sdk-core#388
    '`ResultCap(keep="last")`',
    "`fetch_pages(",
    "`newer_than(",  # sdk-core#392
    "`fetch_counted(",  # sdk-core#403
    "`QueryTooLarge`",
    "`Ceiling(",  # sdk-core#404
    "`fetch_periods(",
    "`check_dest(",
]
# The names of core 0.5.0's recorder that /record-fixture gives a recording (#270,
# sdk-core#483), as sdk-core's main exports them from xippios.core.testing: the source's
# rewrite step, the sync recorder and the one send that writes nothing under their plain
# names, and the two by which a source's own capture of a task builds and writes its
# exchanges.
RECORDER = [
    "`rewrite=`",
    "`record`",
    "`send_once`",
    "`fixture_from_response(",
    "`write_fixture(",
]


def keyed(env: str) -> dict[str, object]:
    """The key answer, a variable's name, so no line looks like a secret; how the key is sent
    is no answer, but the source's own auth in ``_client.py`` (#301)."""
    return {"api_key_env": env}


# Core's one key class, which sends a key where upstream documents it: the source's first
# pull request passes it, and the scaffold renders none (#301; sdk-core ADR-0059).
KEY_AUTHS = {"KeyAuth"}


def key_answers(answers: dict[str, object]) -> dict[str, object]:
    """The key answer a render reads, as given."""
    return {k: v for k, v in answers.items() if k.startswith("api_key_")}


# The family's variants (T11 as narrowed): the shapes its sources take. A core pin and a name
# at its bound are answers of their own, each tested by its rule in test_template.py.
VARIANTS: dict[str, dict[str, object]] = {
    # sdk-usda-nass's shape: a key of its own and a nested import path (sdk-core ADR-0006).
    "keyed-nested": {
        "source_slug": "usda-nass",
        **keyed("NASS_API_KEY"),
    },
    # sdk-eurostat's: no key, a flat import path.
    "keyless-flat": {
        "source_slug": "eurostat",
        **keyed(""),
    },
    # sdk-usda-esmis's (and sdk-usda-wasde's): no key, a nested import path; with the
    # 64-character name that broke four docstrings' line length (row 60), which
    # test_generated_code_is_lint_and_format_clean checks with every other file.
    "keyless-nested": {
        "source_slug": "usda-esmis",
        "source_name": "USDA ESMIS (Economics, Statistics and Market Information System)",
        **keyed(""),
    },
    # sdk-usda-wasde's, as it will start (sdk-core ADR-0021): no key, a nested import path, and the
    # source packages it depends on, one open and one keyed, whose variable then reaches
    # the offline placeholder and live.yml (D47); the first parser package, it parses the
    # files it downloads (sdk-core ADR-0020), so has_files renders parse/ and the samples' table.
    "dependency": {
        "source_slug": "usda-wasde",
        "source_dependencies": (
            '[{name: example-base, minor: "0.3", key_env: ""},'
            ' {name: example-keyed, minor: "0.1", key_env: EXAMPLE_KEYED_API_KEY}]'
        ),
        "has_files": True,
        **keyed(""),
    },
    # sdk-cashctrl's (#174): a multi-tenant source with a write server and a key per tenant,
    # its tenants named by org; flat. A multi-tenant source packages no reference data, whose
    # refresh fetches through the one client of a source with one tenant (#301).
    "tenants": {
        "source_slug": "cashctrl",
        "write_server": True,
        "tenant_param": "org",
        "has_reference_data": False,
        **keyed("CASHCTRL_API_KEY"),
    },
}
# A source on unreleased core: the keyed nested answers with a full-SHA core pin.
PINNED = {**VARIANTS["keyed-nested"], "core_git_ref": FAKE_CORE_SHA}

# The general part of a repository without tasks and servers (ADR-0003), in the two renders of
# the invented source that scripts/prove.sh proves too: a publisher's shared package with a
# nested import path, which holds the key its sources share, and a flat package in a
# repository not named sdk-<slug>, which holds none (sdk-core#538). They answer none of a
# source's questions of an upstream, so the checks of a source's render, which read VARIANTS,
# read neither.
GENERAL: dict[str, dict[str, object]] = {
    "general-nested": {
        "shape": "general",
        "source_slug": "example-shared",
        "source_name": "Shared code of the example sources",
        **keyed("EXAMPLE_API_KEY"),
    },
    "general-flat": {
        "shape": "general",
        "source_slug": "example",
        "source_name": "Example tools",
        "repository_name": "xippios-example",
    },
}


def package_dir(answers: dict[str, object]) -> str:
    import_path = str(answers.get("import_path") or str(answers["source_slug"]).replace("-", "."))
    return import_path.replace(".", "/")


def dependencies(answers: dict[str, object]) -> list[dict[str, str]]:
    """The source packages a variant depends on, parsed from its answer (sdk-core ADR-0021)."""
    parsed = yaml.safe_load(str(answers.get("source_dependencies", "[]")))
    assert isinstance(parsed, list)
    return parsed


# The two kinds of package a source may depend on, each with the record of sdk-core that says
# what it serves: a source package its task layer, a publisher's shared package its public
# names (#335). The answers do not tell them apart, so a text on a dependency names both.
DEPENDENCY_KINDS = {
    "source package": "sdk-core ADR-0021",
    "shared package": "sdk-core ADR-0065 decision 3",
}


def kinds_unnamed(text: str) -> list[str]:
    """The kinds of dependency that ``text`` does not name with their record: the kind, then
    its record in the next parentheses, its lines joined."""
    flat = " ".join(text.split())
    return [
        kind
        for kind, record in DEPENDENCY_KINDS.items()
        if not re.search(rf"{kind}[^()]*\({re.escape(record)}\b[^()]*\)", flat)
    ]


def has_files(answers: dict[str, object]) -> bool:
    """Whether a variant parses the files it downloads (sdk-core ADR-0020); copier's default no."""
    return answers.get("has_files", False) is True


def has_reference_data(answers: dict[str, object]) -> bool:
    """Whether a variant packages reference data (conventions §3); copier's default yes."""
    return answers.get("has_reference_data", True) is True


def write_server(answers: dict[str, object]) -> bool:
    """Whether a variant has a write server (#174); copier's default no."""
    return answers.get("write_server", False) is True


def tenant_param(answers: dict[str, object]) -> str:
    """The parameter that names a multi-tenant variant's tenant (#174), else empty."""
    return str(answers.get("tenant_param", ""))


def tenant_credential(answers: dict[str, object]) -> str:
    """The pattern of a multi-tenant variant's key variable, ``<PREFIX>_<NAME>_API_KEY``, from
    the key answer alone (#301): the key's prefix, or the slug's, core's own, where the
    tenants hold no key; empty for a source with one tenant."""
    if not tenant_param(answers):
        return ""
    key = str(key_answers(answers).get("api_key_env", ""))
    prefix = key.removesuffix("_API_KEY") or str(answers["source_slug"]).upper().replace("-", "_")
    return prefix + "_<NAME>_API_KEY"


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
    tenant's key for a multi-tenant source, then its dependencies', once; a multi-tenant
    source without a key names its credential in ``live_secrets`` (#301)."""
    own = str(key_answers(answers).get("api_key_env", ""))
    if tenant_param(answers) and own:
        own = f"{tenant_prefix(answers)}_DEMO_{tenant_field(answers)}"
    keys = [own] + [d["key_env"] for d in dependencies(answers)]
    return list(dict.fromkeys(key for key in keys if key))


def env_vars(answers: dict[str, object]) -> list[tuple[str, bool, bool]]:
    """The variables a render's ``ENV_VARS`` declares, each with whether it is secret and
    required: the key, or the tenant list and the tenants' key pattern, then the
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


def module(dst: Path, answers: dict[str, object], name: str) -> ast.Module:
    return ast.parse((dst / "src/xippios" / package_dir(answers) / name).read_text())


def assigned(tree: ast.Module, target: str) -> ast.expr:
    """The value a module-level statement assigns to ``target``, annotated or not."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == target:
            return node.value
        if isinstance(node, ast.AnnAssign) and ast.unparse(node.target) == target:
            assert node.value is not None, target
            return node.value
    raise AssertionError(f"no {target} at module level")


def keywords(call: ast.Call) -> dict[str, str]:
    return {str(k.arg): ast.unparse(k.value) for k in call.keywords}


def imported(tree: ast.Module, origin: str) -> set[str]:
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == origin
        for alias in node.names
    }


def entries(dst: Path, answers: dict[str, object]) -> list[tuple[str, bool, bool]]:
    """``ENV_VARS`` of a render's ``_client.py``: each entry's name, secret and required."""
    tree = module(dst, answers, "_client.py")
    value = assigned(tree, "ENV_VARS")
    assert isinstance(value, ast.Tuple), ast.unparse(value)
    names = {"API_KEY_ENV": str(key_answers(answers).get("api_key_env", ""))}
    listed = []
    for call in value.elts:
        assert isinstance(call, ast.Call)
        assert ast.unparse(call.func) == "EnvVar"
        (first,) = call.args
        given = keywords(call)
        named = names[first.id] if isinstance(first, ast.Name) else ast.literal_eval(first)
        flags = [given[flag] == "True" for flag in ("secret", "required")]
        listed.append((named, flags[0], flags[1]))
    return listed


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


def ruff(
    dst: Path, command: str, *args: str, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    """``ruff <command>`` in ``dst``, writing no cache into a render the tests share; ``stdin``
    is the source that ``--stdin-filename`` names, so a check writes no file there."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", command, "--no-cache", *args],
        cwd=dst,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def copier_patterns(setting: str, pkg: str, shape: str = "source", key: str = "") -> list[str]:
    """The lines of a list setting of ``copier.yml``, ``_skip_if_exists`` or ``_exclude``, as
    copier 9.19.1 renders them for a render of ``shape`` whose package is ``pkg`` and whose
    key answer is ``key``: each pattern rendered with the answers it reads, then split into
    its lines."""
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    answers = {"package_dir": pkg, "shape": shape, "api_key_env": key}
    rendered = [env.from_string(p).render(answers) for p in QUESTIONS[setting]]
    return [line for pattern in rendered for line in pattern.splitlines()]


def skip_matcher(pkg: str, shape: str = "source") -> Callable[[str], bool]:
    """Whether copier's ``_skip_if_exists`` protects a path, matched as copier 9.19.1 does:
    the patterns rendered, read as gitignore lines by pathspec."""
    patterns = copier_patterns("_skip_if_exists", pkg, shape)
    return PathSpec.from_lines("gitignore", patterns).match_file


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
