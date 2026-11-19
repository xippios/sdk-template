# ADR-0001: Two answers render the package contract's variants: a write server and a multi-tenant source

Status: Accepted · Date: 2026-11-19 · Decided by https://github.com/xippios/sdk-template/issues/174

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
2. **The variables derive from the key answers.** A multi-tenant source's tenants each have
   a key of their own, `<PREFIX>_<NAME>_API_KEY`, the prefix `api_key_env`'s without
   `_API_KEY`, passed as the registry's `var_prefix` where it is not the slug's; their names
   are listed in `<PREFIX>_<PARAM>S`; and the reserved tenant `demo`, declared by
   `<PREFIX>_DEMO_API_KEY` alone, is the one the offline tests pin and `live.yml` passes.
   `ENV_VARS` lists the tenant list, not required, and the key pattern, required, both from
   these answers, then the dependencies' keys and the live secrets, secret and required.
3. **A key of the source's own.** `tenant_param` needs `api_key_env`, which names the
   tenants' keys, and refuses a gateway, whose key every package behind it shares. A
   source whose tenant credential is no key answers no `tenant_param` and keeps its tenant
   lines by hand, as no answer renders a client of a source's own
   (https://github.com/xippios/sdk-template/issues/175).
4. **What a source sets beside the render stays its own.** The render passes
   `check=check_<param>` from `_client.py`, which checks that a bound tenant has its key,
   and names no noun for a tenant, no read server held to loopback and no write server's
   name of its own: a source that wants one keeps its line, merged three ways.
5. **The option hooks by default.** Every server's `build()` passes the caps and the option
   hooks its tasks module defines, `MCP_CAPS`, `mcp_add_options` and `mcp_apply_options`,
   or `None`, so a source with options defines them in `tasks.py` alone
   (https://github.com/xippios/sdk-template/issues/65).

## Consequences

- A source with a write server answers `write_server: true` at its adoption: its own
  `mcp_write.py` comes as one conflict against the render, its `tasks_write.py` stays, and
  its entry points take the two names. sdk-cashctrl answers `tenant_param: org` too, and
  takes `live_secrets` without its demo key, which `key_envs` now names.
- sdk-google-mail answers `write_server: true` alone: its accounts' refresh tokens are no
  key of the template's, so its `mcp.py`, `mcp_write.py` and `tests/conftest.py` keep their
  tenant lines by hand until an answer names such a credential
  (https://github.com/xippios/sdk-template/issues/207).
- The template's tests render a sixth variant, sdk-cashctrl's shape, and `scripts/prove.sh
  --tenants` proves a nested multi-tenant source with a write server and basic auth: a
  server a host builds from `build()`'s tool set with `register_tasks` serves the tools,
  caps and option defaults of the entry point, in every shape, and of the server `--org`
  binds.
- Core's `serve_tenants` takes no option hook of the source's, so a multi-tenant source's
  options reach a host through its tool set but not its own entry point, until sdk-core
  decides https://github.com/xippios/sdk-core/issues/311.
