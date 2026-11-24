"""The package contract a render carries (#81, #65), and its two variants' answers, a write
server and a multi-tenant source (#174).

``mcp.py`` builds core's ``ToolSet`` in ``build()`` from ``tasks.py`` alone, which declares
the server's instructions, serves ``build_server(build())``, runs core's one ``main`` and
exports ``ENV_VARS`` beside ``SOURCE``, which ``_client.py`` declares: no line of it is a
source's (ADR-0002, decision 9). ``write_server`` renders the write server and its scaffold
under the two entry points; ``tenant_param`` renders core's registry, ``build(lock)``, the
registry handed to ``main`` and the strip of the other tenants' variables, for tenants that
hold a key; tenants that hold another credential name it in ``live_secrets`` (#301).
A bound server's text names no tenant argument (#219), ``/add-endpoint`` names the test
of a write server (#220), and the write scaffold declares a preview's ``reads``, which that
test holds (#271). ``scripts/prove.sh`` serves them: a host's server from the tool set
against the entry point's, and a bound server's instructions, on core.
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
    KEY_AUTHS,
    QUESTIONS,
    VARIANTS,
    assigned,
    entries,
    env_vars,
    generate,
    git,
    imported,
    key_envs,
    keyed,
    keywords,
    live_secrets,
    module,
    package_dir,
    ruff,
    skip_matcher,
    tenant_field,
    tenant_param,
    tenant_prefix,
    write_server,
)


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    (found,) = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    return found


def toolset_call(build: ast.FunctionDef) -> ast.Call:
    """The ``ToolSet.from_tasks(...)`` that ``build`` returns, core's reader of a tasks module
    (sdk-core ADR-0063, decision 7)."""
    (returned,) = [n for n in ast.walk(build) if isinstance(n, ast.Return)]
    assert isinstance(returned.value, ast.Call), ast.unparse(build)
    assert ast.unparse(returned.value.func) == "ToolSet.from_tasks"
    return returned.value


def entry_call(tree: ast.Module) -> str:
    """The one statement of ``run`` after its docstring, core's ``main``."""
    body = function(tree, "run").body
    (call,) = [n for n in body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
    assert len(body) == 2, ast.unparse(function(tree, "run"))
    return ast.unparse(call.value)


# The multi-tenant variant: tenants that hold a key (#174); tenants that hold another
# credential are no variant, but name it in live_secrets (#301).
TENANT_VARIANTS = ["tenants"]


def servers(answers: dict[str, object]) -> list[tuple[str, str]]:
    """The servers a render has: its modules and the tasks modules they serve."""
    read = [("mcp.py", "tasks")]
    return read + ([("mcp_write.py", "tasks_write")] if write_server(answers) else [])


def test_mcp_builds_the_tool_set_and_serves_it(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0063, decisions 7 and 8: ``build()`` returns the tool set that core builds
    from the tasks module, ``server`` is ``build_server(build())``, ``run`` calls core's one
    ``main``, and the module exports the contract's five names, ``ENV_VARS`` and ``SOURCE``
    taken from ``_client.py``. It holds no ``getattr`` read, no instructions and no second
    build (ADR-0002, decision 9)."""
    name, dst = variant
    answers = VARIANTS[name]
    for server_module, tasks_module in servers(answers):
        tree = module(dst, answers, server_module)
        exported = ast.literal_eval(assigned(tree, "__all__"))
        assert exported == ["ENV_VARS", "SOURCE", "build", "run", "server"], server_module
        dotted = f"xippios.{package_dir(answers).replace('/', '.')}"
        assert {"ENV_VARS", "SOURCE"} <= imported(tree, f"{dotted}._client"), server_module
        assert ast.unparse(assigned(tree, "server")) == "build_server(build())"
        assert {"main", "ToolSet", "build_server"} <= imported(tree, "xippios.core.mcp")
        build = function(tree, "build")
        assert ast.unparse(build.returns) == "ToolSet"
        call = toolset_call(build)
        assert [ast.unparse(arg) for arg in call.args] == ["SOURCE", tasks_module]
        expected = {"version": "__version__"}
        if tenant_param(answers):
            expected["lock"] = "lock"
        if tasks_module == "tasks_write":
            expected["read_only"] = "False"
        assert keywords(call) == expected, server_module
        if not tenant_param(answers):
            assert entry_call(tree) == "main(build)", server_module
        source = ast.unparse(tree)
        assert "getattr(" not in source, server_module
        assert not {"INSTRUCTIONS", "BOUND_INSTRUCTIONS"} & {
            ast.unparse(target)
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
        }, server_module


def test_the_tasks_modules_hold_the_servers_text(variant: tuple[str, Path]) -> None:
    """sdk-core ADR-0063, decision 7: each tasks module that a server serves declares its
    instructions as ``MCP_INSTRUCTIONS``, which core reads, and the scaffold declares no
    option hook; ``http.py`` passes ``tool_functions(tasks)``, the list ``mcp.py`` serves."""
    name, dst = variant
    answers = VARIANTS[name]
    for _, tasks_module in servers(answers):
        tree = module(dst, answers, f"{tasks_module}.py")
        text = ast.literal_eval(assigned(tree, "MCP_INSTRUCTIONS"))
        named = str(answers.get("source_name", BASE_ANSWERS["source_name"]))
        assert text.startswith(f"{named} "), (tasks_module, text)
        assert not {"mcp_add_options", "mcp_apply_options"} & {
            n.name for n in tree.body if isinstance(n, ast.FunctionDef)
        }, tasks_module
    http = module(dst, answers, "http.py")
    router = ast.unparse(assigned(http, "router"))
    assert router == "router_from_tasks(SOURCE, tool_functions(tasks))"
    assert "tool_functions" in imported(http, "xippios.core")


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
    ``@pytest.mark.anyio``, in ``tests/test_tasks_write.py``, which takes the write tool set
    first, ``mcp_write.build()``, and holds each preview's ``reads`` in every call (sdk-core
    ADR-0050, #271, sdk-core#483); elsewhere it names none."""
    name, dst = variant
    text = (dst / ".claude/commands/add-endpoint.md").read_text()
    for named in [
        "xippios.core.testing import assert_write_tools",
        "await assert_write_tools(",
        "mcp_write.build(),",
        "@pytest.mark.anyio",
        "tests/test_tasks_write.py",
    ]:
        assert (named in text) is write_server(VARIANTS[name]), (name, named)


WRITE_VARIANTS = [name for name, answers in VARIANTS.items() if write_server(answers)]


@pytest.mark.parametrize("name", WRITE_VARIANTS)
def test_the_write_scaffold_declares_its_previews_reads(
    name: str, render: Callable[[str], Path]
) -> None:
    """Conventions §8, sdk-core ADR-0050, #271: the write scaffold declares one preview, a
    model whose ``performed`` is ``Literal[False]`` and which declares ``reads: list[str]``,
    the operations a preview read, so a write task that returns it passes core's
    ``assert_write_tools``, which holds the preview in every call and which
    ``scripts/prove.sh`` runs on core. The scaffold still serves no task."""
    answers = VARIANTS[name]
    tree = module(render(name), answers, "tasks_write.py")
    previews = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            fields = {
                ast.unparse(statement.target): ast.unparse(statement.annotation)
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
            }
            if fields.get("performed") == "Literal[False]":
                previews.append((node.name, fields))
    assert len(previews) == 1, (name, previews)
    ((preview, fields),) = previews
    assert fields.get("reads") == "list[str]", (name, preview, fields)
    assert ast.literal_eval(assigned(tree, "__all__")) == [], "no write task yet"


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
    reserved ``demo``; a client per tenant and the startup check core's ``main`` calls;
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
    assert not KEY_AUTHS & imported(tree, "xippios.core"), "the source's auth, none of core's"
    (returned,) = [n for n in ast.walk(function(tree, "_build")) if isinstance(n, ast.Return)]
    assert returned.value is not None
    assert ast.unparse(returned.value) == "AsyncClient(config)", "the source passes its auth"
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
    not define; ``/record-fixture`` records a task's exchanges for the reserved tenant
    (#270)."""
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
    record = (tenants / ".claude/commands/record-fixture.md").read_text()
    assert f"`{param}=DEMO`" in record
    claude = (tenants / "CLAUDE.md").read_text()
    assert f"`client_for({param})`" in claude
    assert "`client`" not in claude


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_multi_tenant_source_binds_its_servers(render: Callable[[str], Path], name: str) -> None:
    """Conventions §8: each server's ``build`` takes ``lock: TenantLock | None = None`` and
    hands it to core, which binds the tasks and ends the bound text with its sentence (#219),
    and its entry point hands core's ``main`` the registry and the check, so ``--org`` binds
    it (sdk-core ADR-0063, decision 7)."""
    answers, tenants = VARIANTS[name], render(name)
    param = tenant_param(answers)
    for server_module, _ in servers(answers):
        tree = module(tenants, answers, server_module)
        build = function(tree, "build")
        assert ast.unparse(build.args) == "lock: TenantLock | None=None"
        assert keywords(toolset_call(build))["lock"] == "lock", server_module
        expected = f"main(build, tenants=TENANTS, check=check_{param})"
        assert entry_call(tree) == expected, server_module


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_bound_servers_instructions_take_no_tenant(
    render: Callable[[str], Path], name: str
) -> None:
    """#219: the text ``build(lock)`` passes as ``bound=`` names the tenant's parameter
    nowhere, where the unbound text names it, so the instructions of a bound server say
    nowhere that a tool takes it, core's closing sentence, that every tool takes no
    ``<param>``, aside. The tasks modules hold both texts, ``MCP_INSTRUCTIONS`` and
    ``MCP_BOUND_INSTRUCTIONS``, which core reads (sdk-core ADR-0063, decision 7).
    ``scripts/prove.sh`` reads the clause itself on core."""
    answers, tenants = VARIANTS[name], render(name)
    param = tenant_param(answers)
    named = re.compile(rf"\b{param}\b")
    for _, tasks_module in servers(answers):
        tree = module(tenants, answers, f"{tasks_module}.py")
        unbound = ast.literal_eval(assigned(tree, "MCP_INSTRUCTIONS"))
        bound = ast.literal_eval(assigned(tree, "MCP_BOUND_INSTRUCTIONS"))
        assert named.search(unbound), (tasks_module, unbound)
        assert bound, tasks_module
        assert not named.search(bound), (tasks_module, bound)


@pytest.mark.parametrize("name", TENANT_VARIANTS)
def test_a_multi_tenant_source_strips_the_other_tenants(
    render: Callable[[str], Path], name: str
) -> None:
    """sdk-core ADR-0042, decision 1: the template's ``tests/conftest.py`` calls core's
    ``keep_reserved_tenants(TENANTS)`` at import, before any fixture; the plugin pins the
    reserved tenant's key, which alone declares that tenant offline and which ``live.yml``
    passes, from the pattern ``ENV_VARS`` declares, and no other tenant's variable
    (sdk-core ADR-0035): ``pyproject.toml`` names no variable for it."""
    answers, tenants = VARIANTS[name], render(name)
    tree = ast.parse((tenants / "tests/conftest.py").read_text())
    calls = [ast.unparse(n.value) for n in tree.body if isinstance(n, ast.Expr)]
    assert calls == ["keep_reserved_tenants(TENANTS)"]
    assert "keep_reserved_tenants" in imported(tree, "xippios.core.testing")
    ini = tomllib.loads((tenants / "pyproject.toml").read_text())["tool"]["pytest"]
    assert "xippios_placeholder_key_envs" not in ini["ini_options"]
    reserved = f"{tenant_prefix(answers)}_DEMO_{tenant_field(answers)}"
    assert key_envs(answers) == [reserved]
    pattern = f"{tenant_prefix(answers)}_<NAME>_{tenant_field(answers)}"
    assert (pattern, True, True) in entries(tenants, answers)


def test_the_tenants_prefix_is_the_keys(template_src: Path, tmp_path: Path) -> None:
    """A key whose prefix is not the slug's, as the Google sources share ``GOOGLE_``, gives
    the registry its ``var_prefix``, and every variable follows it."""
    answers = {
        "source_slug": "example-ledger",
        "tenant_param": "account",
        "has_reference_data": False,
        **keyed("EX_API_KEY"),
    }
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
    with a write server and a key prefix of its own, the import of the servers wrapped where
    a long import path needs it; one more is refused."""
    assert f"At most {TENANT_PARAM_BOUND} characters" in str(QUESTIONS["tenant_param"]["help"])
    assert len(name) <= TENANT_PARAM_BOUND
    answers = {
        "tenant_param": name,
        "write_server": True,
        "has_reference_data": False,
        **keyed("EX_BOOKS_API_KEY"),
    }
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
    ],
)
def test_tenant_param_needs_a_name(
    template_src: Path, tmp_path: Path, value: str, answers: dict[str, object]
) -> None:
    """A parameter name: lower case, letters, digits and underscores, a letter first."""
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


def test_a_multi_tenant_source_without_a_key_names_its_credential_in_the_live_secrets(
    template_src: Path, tmp_path: Path
) -> None:
    """#301: no question names the credential of tenants that hold no key. Such a source
    names its variables in ``live_secrets``, the reserved tenant's first: ``live.yml``
    passes them, ``ENV_VARS`` declares each, so the plugin pins each offline,
    ``/record-fixture`` names each, and the template's servers and ``tests/conftest.py``
    render byte for byte as for tenants with a key."""
    assert "tenant_credential_env" not in QUESTIONS
    names = ["EXAMPLE_DEMO_REFRESH_TOKEN", "EXAMPLE_CLIENT_ID", "EXAMPLE_CLIENT_SECRET"]
    answers = {
        "source_slug": "example-mail",
        "write_server": True,
        "tenant_param": "account",
        "live_secrets": "[" + ", ".join(names) + "]",
        "has_reference_data": False,
        **keyed(""),
    }
    dst = generate(template_src, tmp_path / "keyless", **answers)
    recorded = yaml.safe_load((dst / ".copier-answers.yml").read_text())
    assert "tenant_credential_env" not in recorded
    assert key_envs(answers) == []
    ini = tomllib.loads((dst / "pyproject.toml").read_text())["tool"]["pytest"]
    assert "xippios_placeholder_key_envs" not in ini["ini_options"]
    assert [entry for entry in entries(dst, answers) if entry[0] in names] == [
        (name, True, True) for name in names
    ]
    workflow = yaml.safe_load((dst / ".github/workflows/live.yml").read_text())
    (step,) = [step for step in workflow["jobs"]["live"]["steps"] if "env" in step]
    assert list(step["env"]) == ["XIPPIOS_LIVE_TESTS", *names]
    record = (dst / ".claude/commands/record-fixture.md").read_text()
    assert "`" + "` and `".join(names) + "`" in record
    with_key = {k: v for k, v in answers.items() if k != "live_secrets"}
    with_key.update(keyed("EXAMPLE_API_KEY"))
    keyed_dst = generate(template_src, tmp_path / "keyed", **with_key)
    pkg = package_dir(answers)
    for rel in [f"src/xippios/{pkg}/mcp.py", f"src/xippios/{pkg}/mcp_write.py"]:
        assert (dst / rel).read_text() == (keyed_dst / rel).read_text(), rel
    conftest = (dst / "tests/conftest.py").read_text()
    assert conftest == (keyed_dst / "tests/conftest.py").read_text()


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
    ``tasks_write.py`` and takes the two entry points."""
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
    scripts = tomllib.loads((dst / "pyproject.toml").read_text())["project"]["scripts"]
    assert sorted(scripts) == ["xippios-ex-mcp-read", "xippios-ex-mcp-write"]


def test_an_update_keeps_a_sources_script_and_drops_the_placeholder_list(
    template_src: Path, tmp_path: Path
) -> None:
    """#241: a keyless multi-tenant source made by the template before it, whose
    ``pyproject.toml`` named its live secrets under ``xippios_placeholder_key_envs`` and
    said nothing under ``[project.scripts]``, adds a script of its own after the servers'
    entry points, as sdk-google-mail adds its consent command. The update to the working
    tree's render drops the list, which core's plugin no longer reads, since it reads
    ``ENV_VARS`` (sdk-core ADR-0035), and keeps the script, with no conflict: the file is
    the render with the source's line."""
    template = tmp_path / "template"
    shutil.copytree(template_src, template)
    jinja = template / "template/pyproject.toml.jinja"
    current = jinja.read_text()
    # The template before #241 and before core's plugin read ENV_VARS: no comment under
    # [project.scripts], and the live secrets in the list.
    head, rest = current.split("[project.scripts]\n", 1)
    lines = rest.splitlines(keepends=True)
    while lines[0].startswith("#"):
        lines.pop(0)
    listed = "xippios_placeholder_key_envs = {{ live_secret_names | tojson }}\n"
    before = head + "[project.scripts]\n" + "".join(lines) + listed
    git(template, "init", "-q", "-b", "main")
    for tag, text in [("v0.0.1", before), ("v0.0.2", current)]:
        jinja.write_text(text)
        (template / "RELEASE").write_text(f"{tag}\n")
        git(template, "add", "-A")
        git(template, "commit", "-q", "--no-verify", "-m", tag)
        git(template, "tag", tag)
    answers = {
        "source_slug": "example-mail",
        "write_server": True,
        "tenant_param": "account",
        "live_secrets": "[EXAMPLE_DEMO_REFRESH_TOKEN, EXAMPLE_CLIENT_ID, EXAMPLE_CLIENT_SECRET]",
        "has_reference_data": False,
        **keyed(""),
    }
    dst = tmp_path / "repo"
    data = {**BASE_ANSWERS, **answers}
    run_copy(str(template), str(dst), data=data, defaults=True, vcs_ref="v0.0.1", quiet=True)
    pyproject = dst / "pyproject.toml"
    ini = tomllib.loads(pyproject.read_text())["tool"]["pytest"]["ini_options"]
    assert ini["xippios_placeholder_key_envs"] == live_secrets(answers), "the list before"
    slug, dotted = answers["source_slug"], package_dir(answers).replace("/", ".")
    own = f"xippios-{slug}-auth"
    last = f'xippios-{slug}-mcp-write = "xippios.{dotted}.mcp_write:run"\n'
    line = f'{own} = "xippios.{dotted}._consent:run"\n'
    text = pyproject.read_text()
    assert text.count(last) == 1, "the servers' last entry point"
    pyproject.write_text(text.replace(last, last + line))
    git(dst, "init", "-q", "-b", "main")
    git(dst, "add", "-A")
    git(dst, "commit", "-q", "--no-verify", "-m", "a source with a script of its own")
    run_update(str(dst), defaults=True, overwrite=True, vcs_ref="v0.0.2", quiet=True)
    after = pyproject.read_text()
    assert "<<<<<<< before updating" not in after, after
    assert not list(dst.rglob("*.rej"))
    parsed = tomllib.loads(after)
    assert "xippios_placeholder_key_envs" not in parsed["tool"]["pytest"]["ini_options"]
    servers = [f"xippios-{slug}-mcp-read", f"xippios-{slug}-mcp-write"]
    assert list(parsed["project"]["scripts"]) == [*servers, own], "the source's, kept"
    rendered = generate(template_src, tmp_path / "render", **answers)
    assert after == (rendered / "pyproject.toml").read_text().replace(last, last + line)
