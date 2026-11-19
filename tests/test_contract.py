"""The package contract a render carries (#81, #65), and its two variants' answers, a write
server and a multi-tenant source (#174).

``mcp.py`` builds core's ``ToolSet`` in ``build()``, with the option hooks of ``tasks.py``
by default, serves ``build_server(build())`` and exports ``ENV_VARS`` beside ``SOURCE``,
which ``_client.py`` declares. ``write_server`` renders the write server and its scaffold
under the two entry points; ``tenant_param`` renders core's registry, ``build(lock)``,
``serve_tenants`` and the strip of the other tenants' variables, for tenants that hold a
key or, named by ``tenant_credential_env``, a credential that is none (#207).
A bound server's text names no tenant argument (#219), and ``/add-endpoint`` names the test
of a write server (#220). ``scripts/prove.sh`` serves them: a host's server from the tool
set against the entry point's, and a bound server's instructions, on core.
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
    QUESTIONS,
    VARIANTS,
    env_vars,
    generate,
    git,
    key_answers,
    key_envs,
    keyed,
    package_dir,
    ruff,
    skip_matcher,
    tenant_credential,
    tenant_field,
    tenant_param,
    tenant_prefix,
    write_server,
)

# As ast.unparse writes them, in single quotes.
HOOKS = {
    "add_options": "getattr(tasks, 'mcp_add_options', None)",
    "apply_options": "getattr(tasks, 'mcp_apply_options', None)",
    "caps": "getattr(tasks, 'MCP_CAPS', None)",
}


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


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    (found,) = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    return found


def toolset_call(build: ast.FunctionDef) -> ast.Call:
    """The ``ToolSet(...)`` that ``build`` returns."""
    (returned,) = [n for n in ast.walk(build) if isinstance(n, ast.Return)]
    assert isinstance(returned.value, ast.Call), ast.unparse(build)
    assert ast.unparse(returned.value.func) == "ToolSet"
    return returned.value


def keywords(call: ast.Call) -> dict[str, str]:
    return {str(k.arg): ast.unparse(k.value) for k in call.keywords}


def imported(tree: ast.Module, origin: str) -> set[str]:
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == origin
        for alias in node.names
    }


# The multi-tenant variants: tenants that hold a key, and tenants that hold a credential
# that is none (#207).
TENANT_VARIANTS = ["tenants", "tenants-keyless"]


def servers(answers: dict[str, object]) -> list[tuple[str, str]]:
    """The servers a render has: its modules and the tasks modules they serve."""
    read = [("mcp.py", "tasks")]
    return read + ([("mcp_write.py", "tasks_write")] if write_server(answers) else [])


def test_mcp_builds_the_tool_set_and_serves_it(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0026, amendment 2026-11-18, points c and d: ``build()`` returns core's tool set,
    the caps and the option hooks of the tasks module by default (#65), ``server`` is
    ``build_server(build())``, and the module exports ``build``, ``SOURCE`` and
    ``ENV_VARS``, which it takes from ``_client.py``."""
    name, dst = variant
    answers = VARIANTS[name]
    for server_module, tasks_module in servers(answers):
        tree = module(dst, answers, server_module)
        exported = ast.literal_eval(assigned(tree, "__all__"))
        assert exported == ["ENV_VARS", "SOURCE", "build", "run", "server"], server_module
        dotted = f"xippios.{package_dir(answers).replace('/', '.')}"
        assert {"ENV_VARS", "SOURCE"} <= imported(tree, f"{dotted}._client"), server_module
        assert ast.unparse(assigned(tree, "server")) == "build_server(build())"
        build = function(tree, "build")
        assert ast.unparse(build.returns) == "ToolSet"
        given = keywords(toolset_call(build))
        hooks = {key: value.replace("tasks", tasks_module) for key, value in HOOKS.items()}
        assert {key: given.get(key) for key in hooks} == hooks, server_module
        assert given.get("read_only") == (None if tasks_module == "tasks" else "False")
        call = toolset_call(build)
        functions = "tool_functions(" + tasks_module + ")"
        if tenant_param(answers):
            assert ast.unparse(call.args[1]) == f"bind_tasks({functions}, lock)"
        else:
            assert ast.unparse(call.args[1]) == functions


def test_entry_points_follow_the_write_server(variant: tuple[str, Path]) -> None:
    """Conventions §1 and §8: ``xippios-<slug>-mcp`` for a read-only source, and
    ``-mcp-read`` and ``-mcp-write`` for one with a write server, with no alias for the old
    name (#174); the write server and its scaffold render only then, the scaffold the
    source's once rendered and the server the template's."""
    name, dst = variant
    answers = VARIANTS[name]
    slug, pkg = answers["source_slug"], package_dir(answers)
    dotted = pkg.replace("/", ".")
    scripts = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["scripts"]
    if write_server(answers):
        assert scripts == {
            f"xippios-{slug}-mcp-read": f"xippios.{dotted}.mcp:run",
            f"xippios-{slug}-mcp-write": f"xippios.{dotted}.mcp_write:run",
        }
    else:
        assert scripts == {f"xippios-{slug}-mcp": f"xippios.{dotted}.mcp:run"}
    for rel in [f"src/xippios/{pkg}/mcp_write.py", f"src/xippios/{pkg}/tasks_write.py"]:
        assert (dst / rel).is_file() is write_server(answers), rel
    protected = skip_matcher(pkg)
    assert protected(f"src/xippios/{pkg}/tasks_write.py"), "the source fills it"
    assert not protected(f"src/xippios/{pkg}/mcp_write.py"), "the template's, as mcp.py"


def test_the_write_scaffold_serves_nothing_yet(tenants: Path) -> None:
    """The scaffold's ``__all__`` is empty, so the write server registers no tool until a
    source adds its write tasks; ``http.py`` serves ``tasks`` alone."""
    answers = VARIANTS["tenants"]
    tree = module(tenants, answers, "tasks_write.py")
    assert ast.literal_eval(assigned(tree, "__all__")) == []
    http = (tenants / "src/xippios" / package_dir(answers) / "http.py").read_text()
    assert "tasks_write" not in http


def test_add_endpoint_brings_the_write_servers_test(variant: tuple[str, Path]) -> None:
    """Conventions §8, #220: where there is a write server, ``/add-endpoint`` names the test a
    source's first write task brings, core's ``assert_write_tools``, awaited under
    ``@pytest.mark.anyio``, in ``tests/test_tasks_write.py``; elsewhere it names none."""
    name, dst = variant
    text = (dst / ".claude/commands/add-endpoint.md").read_text()
    for named in [
        "xippios.core.testing import assert_write_tools",
        "await assert_write_tools(",
        "@pytest.mark.anyio",
        "tests/test_tasks_write.py",
    ]:
        assert (named in text) is write_server(VARIANTS[name]), (name, named)


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


def test_client_declares_the_variables_it_reads(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0026, amendment 2026-11-18, point c: ``_client.py`` declares ``ENV_VARS``, an
    ``EnvVar`` per variable, from the key answers and ``live_secrets``: the key, or a
    multi-tenant source's list and its tenants' key pattern, then the dependencies' keys."""
    name, dst = variant
    answers = VARIANTS[name]
    assert entries(dst, answers) == env_vars(answers)
    tree = module(dst, answers, "_client.py")
    assert "EnvVar" in imported(tree, "xippios.core")
    assert "ENV_VARS" in ast.literal_eval(assigned(tree, "__all__"))


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (
            {"live_secrets": "[EX_USER, EX_PASSWORD]", **keyed("EX_API_KEY")},
            [("EX_API_KEY", True, True), ("EX_USER", True, True), ("EX_PASSWORD", True, True)],
        ),
        ({"live_secrets": "[EX_USER]", **keyed("")}, [("EX_USER", True, True)]),
        ({**keyed("")}, []),
    ],
)
def test_the_variables_take_the_live_secrets(
    template_src: Path, tmp_path: Path, answers: dict[str, object], expected: list[object]
) -> None:
    """Each variable ``live_secrets`` names follows the key in ``ENV_VARS``, secret and
    required, and a keyless source with none declares an empty tuple; the README's MCP
    block sets each one."""
    dst = generate(template_src, tmp_path / "repo", source_slug="ex", **answers)
    full = {"source_slug": "ex", **answers}
    assert entries(dst, full) == expected == env_vars(full)
    readme = (dst / "README.md").read_text()
    block = readme.split("```json\n", 1)[1].split("```", 1)[0]
    (server,) = yaml.safe_load(block)["mcpServers"].values()
    assert list(server.get("env", {})) == [entry[0] for entry in expected]
    for check in ["check", "format"]:
        run = ruff(dst, check, *(["--check"] if check == "format" else []), ".")
        assert run.returncode == 0, run.stdout + run.stderr


def test_a_multi_tenant_source_renders_cores_registry(tenants: Path) -> None:
    """sdk-core ADR-0036, decision 13, and sdk-core ADR-0042, decision 1: ``tenant_param`` renders
    core's ``Tenants`` with the parameter once, a key per tenant under the key's prefix and the
    reserved ``demo``; a client per tenant and the startup check ``serve_tenants`` calls;
    the tenant list as a task; and no module-level client or key, which no tenant owns."""
    answers = VARIANTS["tenants"]
    param, prefix = tenant_param(answers), tenant_prefix(answers)
    tree = module(tenants, answers, "_client.py")
    registry = assigned(tree, "TENANTS")
    assert isinstance(registry, ast.Call)
    assert ast.unparse(registry.func) == "Tenants"
    assert keywords(registry) == {
        "list_var": repr(f"{prefix}_{param.upper()}S"),
        "param": repr(param),
        "fields": "('API_KEY',)",
        "reserved": "(DEMO,)",
    }, "the slug's prefix is the key's: no var_prefix"
    assert ast.literal_eval(assigned(tree, "DEMO")) == "demo"
    exported = ast.literal_eval(assigned(tree, "__all__"))
    assert {"TENANTS", "DEMO", "client_for", f"check_{param}"} <= set(exported)
    assert not {"client", "auth", "API_KEY_ENV"} & set(exported), "nothing for one tenant"
    check = function(tree, f"check_{param}")
    assert ast.unparse(check.body[-1]) == f"TENANTS.field({param}, 'API_KEY')"
    tasks = module(tenants, answers, "tasks.py")
    assert ast.literal_eval(assigned(tasks, "__all__")) == [f"list_{param}s"]
    listed = ast.unparse(assigned(tasks, f"list_{param}s"))
    assert listed == f"list_task(TENANTS, name='list_{param}s')"


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_multi_tenant_sources_commands_name_its_clients(
    render: Callable[[str], Path], name: str
) -> None:
    """``/add-endpoint``, ``/record-fixture`` and the generated ``CLAUDE.md`` name the client a
    multi-tenant render has, ``client_for``, and never the module-level ``client`` it does
    not define."""
    answers, tenants = VARIANTS[name], render(name)
    param = tenant_param(answers)
    for command in ["add-endpoint", "record-fixture"]:
        text = (tenants / f".claude/commands/{command}.md").read_text()
        assert "client_for(" in text, command
        assert "._client.client`" not in text, command
        assert "`client`" not in text, command
        assert "import client\n" not in text, command
    add_endpoint = (tenants / ".claude/commands/add-endpoint.md").read_text()
    assert f"client_for({param})" in add_endpoint
    claude = (tenants / "CLAUDE.md").read_text()
    assert f"`client_for({param})`" in claude
    assert "`client`" not in claude


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_multi_tenant_source_binds_its_servers(render: Callable[[str], Path], name: str) -> None:
    """Conventions §8: each server's ``build`` takes ``lock: TenantLock | None = None``,
    passes its instructions through ``tenant_instructions``, its bound text as ``bound=``
    (#219), and its entry point runs ``serve_tenants`` with the registry and the check, so
    ``--org`` binds it."""
    answers, tenants = VARIANTS[name], render(name)
    param = tenant_param(answers)
    for server_module, _ in servers(answers):
        tree = module(tenants, answers, server_module)
        build = function(tree, "build")
        assert ast.unparse(build.args) == "lock: TenantLock | None=None"
        given = keywords(toolset_call(build))
        expected = "tenant_instructions(INSTRUCTIONS, lock, bound=BOUND_INSTRUCTIONS)"
        assert given["instructions"] == expected, server_module
        (call,) = [n for n in function(tree, "run").body if isinstance(n, ast.Expr)][-1:]
        expected = f"serve_tenants(server, build, TENANTS, check=check_{param})"
        assert ast.unparse(call.value) == expected, server_module


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_bound_servers_instructions_take_no_tenant(
    render: Callable[[str], Path], name: str
) -> None:
    """#219: the text ``build(lock)`` passes as ``bound=`` names the tenant's parameter
    nowhere, where the unbound text names it, so the instructions of a bound server say
    nowhere that a tool takes it, core's closing sentence, that every tool takes no
    ``<param>``, aside. ``scripts/prove.sh`` reads the clause itself on core."""
    answers, tenants = VARIANTS[name], render(name)
    param = tenant_param(answers)
    named = re.compile(rf"\b{param}\b")
    for server_module, _ in servers(answers):
        tree = module(tenants, answers, server_module)
        unbound = ast.literal_eval(assigned(tree, "INSTRUCTIONS"))
        bound = ast.literal_eval(assigned(tree, "BOUND_INSTRUCTIONS"))
        assert named.search(unbound), (server_module, unbound)
        assert bound, server_module
        assert not named.search(bound), (server_module, bound)


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_multi_tenant_source_strips_the_other_tenants(
    render: Callable[[str], Path], name: str
) -> None:
    """sdk-core ADR-0042, decision 1: the template's ``tests/conftest.py`` calls core's
    ``keep_reserved_tenants(TENANTS)`` at import, before any fixture; the plugin pins the
    reserved tenant's credential, its key or the field ``tenant_credential_env`` names,
    which alone declares that tenant offline and which ``live.yml`` passes, and no other."""
    answers, tenants = VARIANTS[name], render(name)
    tree = ast.parse((tenants / "tests/conftest.py").read_text())
    calls = [ast.unparse(n.value) for n in tree.body if isinstance(n, ast.Expr)]
    assert calls == ["keep_reserved_tenants(TENANTS)"]
    assert "keep_reserved_tenants" in imported(tree, "xippios.core.testing")
    ini = tomllib.loads((tenants / "pyproject.toml").read_text())["tool"]["pytest"]
    keys = ini["ini_options"]["xippios_placeholder_key_envs"]
    reserved = f"{tenant_prefix(answers)}_DEMO_{tenant_field(answers)}"
    assert keys == key_envs(answers) == [reserved]


def test_the_tenants_prefix_is_the_keys(template_src: Path, tmp_path: Path) -> None:
    """A key whose prefix is not the slug's, as the Google sources share ``GOOGLE_``, gives
    the registry its ``var_prefix``, and every variable follows it."""
    answers = {"source_slug": "example-ledger", "tenant_param": "account", **keyed("EX_API_KEY")}
    dst = generate(template_src, tmp_path / "repo", **answers)
    registry = keywords(assigned(module(dst, answers, "_client.py"), "TENANTS"))
    assert registry["var_prefix"] == "'EX'"
    assert registry["list_var"] == "'EX_ACCOUNTS'"
    assert entries(dst, answers) == env_vars(answers)
    assert [entry[0] for entry in entries(dst, answers)] == ["EX_ACCOUNTS", "EX_<NAME>_API_KEY"]
    for check in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *check)
        assert run.returncode == 0, run.stdout + run.stderr


# The bound copier.yml states for tenant_param, as source_name's is stated.
TENANT_PARAM_BOUND = 20


@pytest.mark.parametrize(
    ("slug", "name"),
    [
        ("example-ledger", "workspace"),
        ("acme-books", "organisation"),
        ("example-ledger-books", "tenant_of_the_ledger"),
    ],
)
def test_tenant_param_is_bounded_by_the_longest_python_line(
    template_src: Path, tmp_path: Path, slug: str, name: str
) -> None:
    """A parameter up to the bound the help states renders ruff-clean (E501 at 100 columns)
    with a write server, the reference scaffold and a key prefix of its own, the import of
    the servers wrapped where a long import path needs it; one more is refused."""
    assert f"At most {TENANT_PARAM_BOUND} characters" in str(QUESTIONS["tenant_param"]["help"])
    assert len(name) <= TENANT_PARAM_BOUND
    answers = {"tenant_param": name, "write_server": True, **keyed("EX_BOOKS_API_KEY", "basic")}
    dst = generate(template_src, tmp_path / "bound", source_slug=slug, **answers)
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr
    longer = name + "x" * (TENANT_PARAM_BOUND + 1 - len(name))
    with pytest.raises(ValueError, match="tenant_param"):
        generate(
            template_src,
            tmp_path / "refused",
            source_slug=slug,
            **{**answers, "tenant_param": longer},
        )


@pytest.mark.parametrize(
    ("value", "answers"),
    [
        ("Org", keyed("EX_API_KEY")),
        ("org-id", keyed("EX_API_KEY")),
        ("1org", keyed("EX_API_KEY")),
        ("org", {"gateway": "api.data.gov"}),
    ],
)
def test_tenant_param_needs_a_name_and_no_gateway(
    template_src: Path, tmp_path: Path, value: str, answers: dict[str, object]
) -> None:
    """A parameter name, and no gateway's key, which every package behind it shares; a
    source without a key of its own answers ``tenant_credential_env`` instead (#209)."""
    with pytest.raises(ValueError, match="tenant_param"):
        generate(template_src, tmp_path / "repo", source_slug="ex", tenant_param=value, **answers)


def test_the_contracts_answers_are_recorded_and_its_derivations_not(tenants: Path) -> None:
    """Both answers are recorded on one line, the defaults included; what they derive is
    computed on each render."""
    recorded = yaml.safe_load((tenants / ".copier-answers.yml").read_text())
    assert recorded["write_server"] is True
    assert recorded["tenant_param"] == "org"
    for derived in ["tenant_prefix", "tenant_list_var", "env_vars"]:
        assert derived not in recorded, derived


# The auths of core's that a key answer renders: a source whose tenants hold no key passes
# its own in _build (#175, #209).
KEY_AUTHS = {"QueryKeyAuth", "HeaderKeyAuth", "BearerAuth", "BasicKeyAuth"}


def test_a_keyless_multi_tenant_source_renders_the_tenant_shape(
    template_src: Path, tmp_path: Path, tenants_keyless: Path
) -> None:
    """#207, #209: a source whose tenants hold a credential that is no key answers
    ``tenant_param``, and the template's two servers and ``tests/conftest.py`` render byte
    for byte as for a source whose tenants hold a key, with the same slug, parameter and
    write server."""
    answers = VARIANTS["tenants-keyless"]
    with_key = {k: v for k, v in answers.items() if k != "tenant_credential_env"}
    with_key.update(keyed(f"{tenant_prefix(answers)}_API_KEY", "bearer"))
    dst = generate(template_src, tmp_path / "keyed", **with_key)
    pkg = package_dir(answers)
    for rel in [
        f"src/xippios/{pkg}/mcp.py",
        f"src/xippios/{pkg}/mcp_write.py",
        "tests/conftest.py",
    ]:
        assert (tenants_keyless / rel).read_text() == (dst / rel).read_text(), rel


def test_a_keyless_multi_tenant_registry_takes_the_credential(tenants_keyless: Path) -> None:
    """Conventions §7: the registry's prefix and field are those of ``tenant_credential_env``,
    ``var_prefix`` given where the slug's is another, and ``check_<param>`` checks that
    field; each tenant's client takes no auth of the template's, the source's own being
    passed in ``_build``, and the module defines what the keyed shape's does."""
    answers = VARIANTS["tenants-keyless"]
    param, prefix, field = tenant_param(answers), tenant_prefix(answers), tenant_field(answers)
    assert (prefix, field) == ("GOOGLE", "REFRESH_TOKEN"), "the slug would give GOOGLE_MAIL"
    tree = module(tenants_keyless, answers, "_client.py")
    registry = assigned(tree, "TENANTS")
    assert isinstance(registry, ast.Call)
    assert keywords(registry) == {
        "var_prefix": repr(prefix),
        "list_var": repr(f"{prefix}_{param.upper()}S"),
        "param": repr(param),
        "fields": repr((field,)),
        "reserved": "(DEMO,)",
    }
    check = function(tree, f"check_{param}")
    assert ast.unparse(check.body[-1]) == f"TENANTS.field({param}, {field!r})"
    assert not KEY_AUTHS & imported(tree, "xippios.core"), "the source's auth, none of core's"
    (returned,) = [n for n in ast.walk(function(tree, "_build")) if isinstance(n, ast.Return)]
    assert returned.value is not None
    assert ast.unparse(returned.value) == "AsyncClient(config)"
    assert ast.literal_eval(assigned(tree, "__all__")) == [
        "BASE_URL",
        "DEMO",
        "ENV_VARS",
        "RATE_LIMIT",
        "SOURCE",
        "TENANTS",
        f"check_{param}",
        "classify",
        "client_for",
        "config",
    ]


def test_a_keyless_multi_tenant_sources_variables_follow_the_credential(
    tenants_keyless: Path,
) -> None:
    """``ENV_VARS`` lists the tenant list and the credential's pattern, then the live secrets;
    the plugin pins the reserved tenant's credential offline, the variable that alone
    declares that tenant, and ``live.yml`` passes it first."""
    answers = VARIANTS["tenants-keyless"]
    assert tenant_credential(answers) == "GOOGLE_<NAME>_REFRESH_TOKEN"
    assert (
        entries(tenants_keyless, answers)
        == env_vars(answers)
        == [
            ("GOOGLE_ACCOUNTS", False, False),
            ("GOOGLE_<NAME>_REFRESH_TOKEN", True, True),
            ("GOOGLE_CLIENT_ID", True, True),
            ("GOOGLE_CLIENT_SECRET", True, True),
        ]
    )
    ini = tomllib.loads((tenants_keyless / "pyproject.toml").read_text())["tool"]["pytest"]
    keys = ini["ini_options"]["xippios_placeholder_key_envs"]
    assert keys == key_envs(answers) == ["GOOGLE_DEMO_REFRESH_TOKEN"]
    workflow = yaml.safe_load((tenants_keyless / ".github/workflows/live.yml").read_text())
    (step,) = [step for step in workflow["jobs"]["live"]["steps"] if "env" in step]
    assert list(step["env"]) == [
        "XIPPIOS_LIVE_TESTS",
        *keys,
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]


def test_a_keyless_multi_tenant_render_names_no_key_of_its_tenants(tenants_keyless: Path) -> None:
    """No file of the render names a key the tenants do not hold: the client, the README,
    the CLAUDE.md and ``/record-fixture`` name the credential's variables, the reserved
    tenant's among them."""
    answers = VARIANTS["tenants-keyless"]
    prefix, field = tenant_prefix(answers), tenant_field(answers)
    keys = [f"{prefix}_{name}_API_KEY" for name in ["<NAME>", "DEMO", "ACME"]]
    for path in sorted(tenants_keyless.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".md", ".toml", ".yml"}:
            text = path.read_text()
            named = [key for key in [*keys, '"API_KEY"', "'API_KEY'"] if key in text]
            assert not named, (path, named)
    record = (tenants_keyless / ".claude/commands/record-fixture.md").read_text()
    assert f'TENANTS.var(DEMO, "{field}")' in record
    claude = (tenants_keyless / "CLAUDE.md").read_text().splitlines()
    (credentials,) = [line for line in claude if line.startswith("| Credentials | ")]
    assert f"`{tenant_credential(answers)}`" in credentials
    (row,) = [line for line in claude if line.startswith("| Tenants | ")]
    assert f"`{prefix}_DEMO_{field}`" in row
    readme = (tenants_keyless / "README.md").read_text()
    for name in [tenant_credential(answers), f"{prefix}_DEMO_{field}"]:
        assert f"`{name}`" in readme, name


def test_the_credential_is_recorded_where_it_is_asked(render: Callable[[str], Path]) -> None:
    """``tenant_credential_env`` is asked of a multi-tenant source without a key alone, and
    recorded there; a key derives it, and the prefix and the field it gives are computed on
    each render."""
    for name, answers in VARIANTS.items():
        recorded = yaml.safe_load((render(name) / ".copier-answers.yml").read_text())
        assert recorded.get("tenant_credential_env") == answers.get("tenant_credential_env"), name
        for derived in ["tenant_prefix", "tenant_field", "tenant_list_var"]:
            assert derived not in recorded, (name, derived)


@pytest.mark.parametrize(
    ("param", "value", "answers"),
    [
        ("account", None, keyed("")),
        ("account", "", keyed("")),
        ("account", "EX_REFRESH_TOKEN", keyed("")),
        ("account", "ex_<NAME>_REFRESH_TOKEN", keyed("")),
        ("account", "<NAME>_REFRESH_TOKEN", keyed("")),
        ("account", "EX_<NAME>_", keyed("")),
        ("account", "EX_<NAME>_<NAME>_TOKEN", keyed("")),
        ("account", "EX_<NAME>_API_KEY", keyed("")),
        ("account", "EX_<NAME>_REFRESH_TOKEN", keyed("EX_API_KEY")),
        ("", "EX_<NAME>_REFRESH_TOKEN", keyed("")),
    ],
)
def test_tenant_credential_env_is_one_variable_pattern_of_tenants_without_a_key(
    template_src: Path, tmp_path: Path, param: str, value: str | None, answers: dict[str, object]
) -> None:
    """A multi-tenant source without a key names its tenants' credential, once, as
    ``<PREFIX>_<NAME>_<FIELD>`` in upper case; a key is ``api_key_env``'s, which renders its
    auth and derives the pattern, and a source with one tenant names none."""
    data: dict[str, object] = {"tenant_param": param, **answers}
    if value is not None:
        data["tenant_credential_env"] = value
    with pytest.raises(ValueError, match="tenant_credential_env"):
        generate(template_src, tmp_path / "repo", source_slug="ex", **data)


# The bound copier.yml states for tenant_credential_env.
TENANT_CREDENTIAL_BOUND = 40


@pytest.mark.parametrize(
    "credential",
    [
        "EX_<NAME>_" + "A" * (TENANT_CREDENTIAL_BOUND - 16) + "_TOKEN",
        "E" * (TENANT_CREDENTIAL_BOUND - 13) + "_<NAME>_TOKEN",
    ],
)
def test_tenant_credential_env_is_bounded_by_the_longest_python_line(
    template_src: Path, tmp_path: Path, credential: str
) -> None:
    """A pattern up to the bound the help states, its field or its prefix at the longest,
    renders ruff-clean (E501 at 100 columns) with a parameter at its own bound, a write
    server and a long import path; one more character is refused."""
    help_text = str(QUESTIONS["tenant_credential_env"]["help"])
    assert f"At most {TENANT_CREDENTIAL_BOUND} characters" in help_text
    assert len(credential) == TENANT_CREDENTIAL_BOUND
    answers = {"tenant_param": "tenant_of_the_ledger", "write_server": True, **keyed("")}
    slug = "example-ledger-books"
    dst = generate(
        template_src,
        tmp_path / "bound",
        source_slug=slug,
        tenant_credential_env=credential,
        **answers,
    )
    for args in [("check", "."), ("format", "--check", ".")]:
        run = ruff(dst, *args)
        assert run.returncode == 0, run.stdout + run.stderr
    with pytest.raises(ValueError, match="tenant_credential_env"):
        generate(
            template_src,
            tmp_path / "refused",
            source_slug=slug,
            tenant_credential_env="X" + credential,
            **answers,
        )


def test_the_readme_configures_each_server(variant: tuple[str, Path]) -> None:
    """#88: the README's MCP blocks run each entry point, the write server's in a block of
    its own, and set the variables of the list, a tenant's by an example name."""
    name, dst = variant
    answers = VARIANTS[name]
    slug = answers["source_slug"]
    readme = (dst / "README.md").read_text()
    blocks = [block.split("```", 1)[0] for block in readme.split("```json\n")[1:]]
    configured = [next(iter(yaml.safe_load(block)["mcpServers"].values())) for block in blocks]
    entry_points = [server["args"][2] for server in configured]
    if write_server(answers):
        assert entry_points == [f"xippios-{slug}-mcp-read", f"xippios-{slug}-mcp-write"]
    else:
        assert entry_points == [f"xippios-{slug}-mcp"]
    names = [entry[0].replace("<NAME>", "ACME") for entry in env_vars(answers)]
    for server in configured:
        assert list(server.get("env", {})) == names


def test_an_update_merges_a_sources_own_write_server(template_src: Path, tmp_path: Path) -> None:
    """What the fragment says an update does: a source that wrote its write server by hand
    and answers ``write_server`` at its update gets the render's ``mcp_write.py`` as
    conflicts against its own, here one hunk since the two share no line, keeps its
    ``tasks_write.py``, takes the two entry points, and keeps a line of its own in
    ``mcp.py`` where the render leaves its place alone."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    git(template, "init", "-q", "-b", "main")
    for tag in ["v0.0.1", "v0.0.2"]:
        (template / "RELEASE").write_text(f"{tag}\n")
        git(template, "add", "-A")
        git(template, "commit", "-q", "--no-verify", "-m", tag)
        git(template, "tag", tag)
    answers = {"source_slug": "ex", **keyed("EX_API_KEY")}
    dst = tmp_path / "repo"
    data = {**BASE_ANSWERS, **answers}
    run_copy(str(template), str(dst), data=data, defaults=True, vcs_ref="v0.0.1", quiet=True)
    pkg = dst / "src/xippios/ex"
    own_server = '"""The source\'s own write server."""\n'
    own_tasks = '"""The source\'s own write tasks."""\n\n__all__ = ["create_thing"]\n'
    (pkg / "mcp_write.py").write_text(own_server)
    (pkg / "tasks_write.py").write_text(own_tasks)
    mcp = (pkg / "mcp.py").read_text()
    line = '    "Tools are read-only. "\n'
    assert line in mcp
    (pkg / "mcp.py").write_text(mcp.replace(line, '    "Tools are read-only, the source says. "\n'))
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source with a write server of its own")
    run_update(
        str(dst),
        data={"write_server": True},
        defaults=True,
        overwrite=True,
        vcs_ref="v0.0.2",
        quiet=True,
    )
    server = (pkg / "mcp_write.py").read_text()
    assert server.startswith("<<<<<<< before updating\n" + own_server + "=======\n"), server
    assert "def build() -> ToolSet:" in server
    assert ">>>>>>> after updating" in server
    assert (pkg / "tasks_write.py").read_text() == own_tasks, "the source's, skip-listed"
    assert "the source says" in (pkg / "mcp.py").read_text(), "its own line, merged"
    scripts = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["scripts"]
    assert sorted(scripts) == ["xippios-ex-mcp-read", "xippios-ex-mcp-write"]
