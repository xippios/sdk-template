# ADR-0002: The answers that render the package contract's variants, and what the template asks

Status: Accepted · Date: 2026-11-24 · Decided by https://github.com/xippios/sdk-template/issues/301 · Supersedes ADR-0001

## Context

sdk-core defines the package contract by which a host serves a source (sdk-core ADR-0026,
amendment 2026-11-18, points c and d; conventions §7 and §8): a source's `mcp.py` defines
`build(**options)`, which returns core's `ToolSet`, its module-level `server` is
`build_server(build())`, and its `_client.py` declares the variables it reads as `EnvVar`
entries. Two variants of the contract are in the family. A source with a write server has two
entry points, `xippios-<source>-mcp-read` and `xippios-<source>-mcp-write`, and a second
module, `mcp_write.py`, over `tasks_write.py`. A multi-tenant source declares its tenants with
core's `Tenants`, and each of its servers takes `build(lock)`, passes its tasks through
`bind_tasks` and runs `serve_tenants`, while its `tests/conftest.py` strips every tenant but
the reserved one with `keep_reserved_tenants` (sdk-core ADR-0036, decision 13; sdk-core
ADR-0042, decision 1). ADR-0001 gave each variant an answer and was amended twice, the first
time for a third answer, `tenant_credential_env`, which named the credential of tenants that
hold no key.

The template's questions then held answers that keep no source in step: answers that act at
generation alone, and answers that one source or one publisher needs. Four answers on
https://github.com/xippios/sdk-template/issues/301 settle them: the six answers that acted at
generation alone leave, and the scaffold's `_client.py` keeps a marked place for the base URL,
the auth and the pace (part 1); `human` becomes a constant and `core_version` stays an answer
(part 2); `tenant_credential_env` goes back to sdk-google-mail, its one consumer, while
`source_dependencies` stays (part 3). The second answer on
https://github.com/xippios/sdk-template/issues/302 takes the `gateway` question out with its
branch, which three sources behind api.data.gov answer, since the gateway moves from core to
their publisher's shared package. ADR-0001 has no room for a third amendment, so this record
takes its place.

## Decision

1. **Two answers, names rather than switches.** `write_server`, a boolean, renders
   `mcp_write.py`, the `tasks_write.py` scaffold, which the source fills and
   `_skip_if_exists` protects, and the entry points `-mcp-read` and `-mcp-write` in place of
   `-mcp`, with no alias for the old name. `tenant_param`, empty by default, names the
   tenant's parameter, `org` say, and renders core's registry, `build(lock)`, `serve_tenants`
   and the strip. Carried from ADR-0001, decision 1.
2. **The tenants' variables derive from the key answer alone.** A multi-tenant source's
   tenants each hold a key of their own, `<PREFIX>_<NAME>_API_KEY`, the prefix `api_key_env`'s
   without `_API_KEY`, passed as the registry's `var_prefix` where it is not the slug's; the
   registry's one field is `API_KEY`; the tenants' names are listed in `<PREFIX>_<PARAM>S`; and
   the reserved tenant `demo`, declared by `<PREFIX>_DEMO_API_KEY` alone, is the one the
   offline tests pin and the one `live.yml` passes. `ENV_VARS` lists the tenant list, not
   required, and the key's pattern, required, then the dependencies' keys and the live
   secrets, secret and required. No answer names another credential (#301, part 3).
3. **A credential that is no key is the source's own.** A multi-tenant source whose tenants
   hold another credential, a refresh token say, answers no key and names that credential's
   variables in `live_secrets`, the reserved tenant's first: `live.yml` passes them, core's
   plugin sets each to the placeholder in the offline tests, `/record-fixture` names each,
   and its own `_client.py` holds the registry, the auth and the check that read them. The
   template's servers and `tests/conftest.py` render as for tenants with a key. No variant of
   the template renders such a source: where `api_key_env` is empty, a new render's registry
   takes the slug's prefix, core's own, and the key's field, which the source's first pull
   request changes as it sets the base URL. `tenant_param` takes at most 20 characters, so
   every generated Python line stays within 100 columns. Replaces ADR-0001, decisions 2 and
   3, for a credential that is no key.
4. **What a source sets beside the render stays its own.** The render passes
   `check=check_<param>` from `_client.py`, which checks that a bound tenant has its key, and
   names no noun for a tenant, no read server held to loopback and no write server's name of
   its own: a source that wants one keeps its line, merged three ways. So does a source whose
   tenant list is not named `list_<param>s` keep its own instructions, which name that tool.
   Carried from ADR-0001, decision 4.
5. **The option hooks by default.** Every server's `build()` passes the caps and the option
   hooks its tasks module defines, `MCP_CAPS`, `mcp_add_options` and `mcp_apply_options`, or
   `None`, so a source with options defines them in `tasks.py` alone
   (https://github.com/xippios/sdk-template/issues/65). Carried from ADR-0001, decision 5.
6. **What the template asks.** The template asks what keeps its sources in step (#301,
   part 1). `copier.yml` asks fourteen questions whose answers a source records, `source_slug`, `import_path`, `source_name`,
   `upstream_url`, `upstream_docs_url`, `api_key_env`, `write_server`, `tenant_param`,
   `core_version`, `core_git_ref`, `source_dependencies`, `live_secrets`, `has_files` and
   `has_reference_data`, and computes ten that no source records. An answer that acts at
   generation alone is no question: the source's first pull request fills its place in a file
   it owns (#301, part 1). An answer that one source or one publisher needs goes back to
   it (#301, part 3; #302, part 2). `core_version` stays an answer, which an adoption
   raises (#301, part 2), and so does `source_dependencies`, with the computed
   `depends_on` (#301, part 3).
7. **The human is a constant.** `.github/CODEOWNERS` is copied as it stands: each path that
   steers a source, `.github/`, `CLAUDE.md`, `.claude/`, `pyproject.toml` and
   `.copier-answers.yml`, is owned by `jdidaskalu`. Another owner is a change of the template,
   which every update carries (#301, part 2).
8. **No gateway question.** The scaffold's client renders no gateway, and no file of a render
   names one. A source behind api.data.gov keeps its recorded `api_key_env`,
   `DATA_GOV_API_KEY`, and imports the gateway from its publisher's shared package,
   `xippios.usda.fas`, in its own `_client.py` (#302, part 2; sdk-core ADR-0032).

## Consequences

- Every source's update drops `gateway` and `human` from `.copier-answers.yml`, since copier
  records no answer of a question it no longer asks, and its `.github/CODEOWNERS` takes the
  new header with the same rules.
- sdk-usda-psd, sdk-usda-esr and sdk-usda-gats keep `api_key_env` and change one import of
  `_client.py` by hand at their adoption, `Gateway` from `xippios.usda.fas` in place of
  `xippios.core.data_gov`, since the file is theirs once rendered.
- sdk-google-mail drops `tenant_credential_env` and passes `-d live_secrets=` with
  `GOOGLE_DEMO_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, in that order:
  its `live.yml` and its placeholder list render the bytes they rendered before, and its
  `/record-fixture` names the three variables where it named the reserved tenant's credential
  alone. Its `_client.py`, `README.md` and `CLAUDE.md` are its own and keep their lines.
- sdk-cashctrl answers `write_server: true` and `tenant_param: org`, and its render follows
  decision 2 as before.
- The template's tests render five variants, keyed and nested, keyless and flat, keyless and
  nested, a dependent that parses files, and a flat multi-tenant source with a write server
  and a key per tenant, and `scripts/prove.sh --all` runs five proofs. No proof renders a source
  whose tenants hold no key or a source behind a gateway.
- Core's `serve_tenants` takes no option hook of the source's, so a multi-tenant source's
  options reach a host through its tool set but not its own entry point, until sdk-core
  decides https://github.com/xippios/sdk-core/issues/311.
