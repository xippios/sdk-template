# ADR-0001: Two answers render the package contract's variants: a write server and a multi-tenant source

Status: Superseded by ADR-0002 · Date: 2026-11-19 · Decided by https://github.com/xippios/sdk-template/issues/174 · Amended 2026-11-19 by https://github.com/xippios/sdk-template/issues/209 · Amended 2026-11-19 by https://github.com/xippios/sdk-template/issues/221

## Context

sdk-core 0.4.0 defines the package contract by which a host serves a source (sdk-core
ADR-0026, amendment 2026-11-18, points c and d; conventions §7 and §8): a source's `mcp.py`
defines `build(**options)`, which returns core's `ToolSet`, its module-level `server` is
`build_server(build())`, and its `_client.py` declares the variables it reads as
`EnvVar` entries. Two variants of the contract are in the family. A source with a write
server has two entry points, `xippios-<source>-mcp-read` and `xippios-<source>-mcp-write`,
and a second module, `mcp_write.py`, over `tasks_write.py`. A multi-tenant source declares
its tenants with core's `Tenants`, and each of its servers takes `build(lock)`, passes its
tasks through `bind_tasks` and runs `serve_tenants`, while its `tests/conftest.py` strips
every tenant but the reserved one with `keep_reserved_tenants` (sdk-core ADR-0036,
decision 13; sdk-core ADR-0042, decision 1).

Both variants live in files the template owns, `mcp.py`, `tests/conftest.py` and
`pyproject.toml`'s entry points, so a source that has them carries them as hand lines that
every update merges, and a pull request that touches `pyproject.toml` is the human's.
sdk-cashctrl has both variants, its tenants' keys sent as the basic user name, and
sdk-google-mail has both, its tenants' credential a refresh token of its own flow.

## Decision

1. **Two answers, names rather than switches.** `write_server`, a boolean, renders
   `mcp_write.py`, the `tasks_write.py` scaffold, which the source fills and
   `_skip_if_exists` protects, and the entry points `-mcp-read` and `-mcp-write` in place
   of `-mcp`, with no alias for the old name. `tenant_param`, empty by default, names the
   tenant's parameter, `org` say, and renders core's registry, `build(lock)`,
   `serve_tenants` and the strip.
2. **The variables derive from the key answers, or from one answer without a key.** A
   multi-tenant source's tenants each have a credential of their own,
   `<PREFIX>_<NAME>_<FIELD>`. Where they hold a key, it is `<PREFIX>_<NAME>_API_KEY`, the
   prefix `api_key_env`'s without `_API_KEY`. Where they hold another credential, a refresh
   token say, one more answer names its variable, `tenant_credential_env`, which a key
   derives instead, so a source with a key answers nothing more (amended 2026-11-19). The
   prefix is passed as the registry's `var_prefix` where it is not the slug's, and the
   field is the registry's one field; the tenants' names are listed in
   `<PREFIX>_<PARAM>S`; and the reserved tenant `demo`, declared by
   `<PREFIX>_DEMO_<FIELD>` alone, is the one the offline tests pin, since that variable
   alone declares it, and the one `live.yml` passes. `ENV_VARS` lists the tenant list, not
   required, and the credential's pattern, required, both from these answers, then the
   dependencies' keys and the live secrets, secret and required.
3. **A credential of the source's own.** `tenant_param` refuses a gateway, whose key every
   package behind it shares, and takes at most 20 characters, so every generated Python
   line stays within 100 columns. Without `api_key_env` it needs `tenant_credential_env`,
   one upper-case `<PREFIX>_<NAME>_<FIELD>` of at most 40 characters, for the same reason,
   whose field is no `API_KEY`: a key is `api_key_env`'s, which renders the key's auth.
   The scaffold of such a source's `_client.py` passes no auth to a tenant's client: the
   source's own reads the credential, as no render of a source without a client of its own
   is made (https://github.com/xippios/sdk-template/issues/175). The template's servers and
   `tests/conftest.py` render as for tenants with a key (amended 2026-11-19).
4. **What a source sets beside the render stays its own.** The render passes
   `check=check_<param>` from `_client.py`, which checks that a bound tenant has its credential,
   and names no noun for a tenant, no read server held to loopback and no write server's
   name of its own: a source that wants one keeps its line, merged three ways. So does a
   source whose tenant list is not named `list_<param>s` keep its own instructions, which
   name that tool.
5. **The option hooks by default.** Every server's `build()` passes the caps and the option
   hooks its tasks module defines, `MCP_CAPS`, `mcp_add_options` and `mcp_apply_options`,
   or `None`, so a source with options defines them in `tasks.py` alone
   (https://github.com/xippios/sdk-template/issues/65).

## Consequences

- A source with a write server answers `write_server: true` at its adoption: its own
  `mcp.py` and `mcp_write.py` come as conflicts against the render, merged around the lines
  both share, two in each on sdk-cashctrl's `main` (amended 2026-11-19), its
  `tasks_write.py` stays, and its entry points take the two names. sdk-cashctrl answers
  `tenant_param: org` too, keeps its instructions, which name
  `cashctrl_list_organisations`, and takes `live_secrets` without its demo key, which
  `key_envs` now names.
- A render with `tenant_param` gives `mcp.py` and `mcp_write.py` a bound text,
  `BOUND_INSTRUCTIONS`, each server's instructions without the clause that a tool takes the
  tenant's argument, and passes it as `bound=` to core's `tenant_instructions`, so the
  instructions of a server that `--<param>` binds say that no tool takes the tenant in
  core's closing sentence alone (amended 2026-11-19).
- sdk-google-mail answers `write_server: true`, `tenant_param: account` and
  `tenant_credential_env: GOOGLE_<NAME>_REFRESH_TOKEN`, and takes `live_secrets` without
  `GOOGLE_DEMO_REFRESH_TOKEN`, which `key_envs` now names (amended 2026-11-19). Its own
  `mcp.py` and `mcp_write.py` come as three conflicts each against the render, its
  `tests/conftest.py` as one, the whole file, and its `pyproject.toml` as two, its consent
  entry point and its placeholder list, on its `main`. Its `BOUND_INSTRUCTIONS` merge with
  the render's, so it no longer keeps them as its own lines (amended 2026-11-19). It keeps
  the read server's loopback rule as its lines, and `_client.py` takes `check_account` and
  `ENV_VARS` by hand.
- The template's tests render a sixth variant, sdk-cashctrl's shape, and a seventh,
  sdk-google-mail's, and `scripts/prove.sh --tenants` proves a nested multi-tenant source
  with a write server and basic auth, and `--tenants-keyless` one whose tenants hold a
  refresh token under a prefix the slug does not give: a server a host builds with
  `register_tasks` from `build()`'s tool set and a second package's serves the tools, caps
  and option defaults of the entry point, in every shape, and of the server `--org` or
  `--account` binds, whose instructions say that no tool takes the tenant in core's closing
  sentence alone (amended 2026-11-19).
- Core's `serve_tenants` takes no option hook of the source's, so a multi-tenant source's
  options reach a host through its tool set but not its own entry point, until sdk-core
  decides https://github.com/xippios/sdk-core/issues/311.
