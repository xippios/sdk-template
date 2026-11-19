- `tenant_param` names a multi-tenant source's tenant parameter, `org` say, and renders
  core's kit: `Tenants` in `_client.py`, a client and a key `<PREFIX>_<NAME>_API_KEY` per
  tenant beside the reserved `demo`, the tenant list task, `build(lock)` and `serve_tenants`
  in each server with the `check_<param>` of `_client.py`, and
  `keep_reserved_tenants(TENANTS)` in the template's `tests/conftest.py`. The offline tests
  and `live.yml` take the reserved tenant's key, `<PREFIX>_DEMO_API_KEY`, in place of
  `api_key_env`'s, so a source that lists it in `live_secrets` drops it there in the update,
  and the answer takes at most 20 characters and refuses a source without a key of its own
  or behind a gateway.
  sdk-cashctrl passes `-d tenant_param=org` and keeps its own `INSTRUCTIONS` in the
  conflicts of `mcp.py`, since the render's name the tenant list `cashctrl_list_orgs` where
  its tool is `cashctrl_list_organisations`, and sdk-google-mail, whose tenants hold refresh
  tokens, keeps its tenant lines by hand until the row cited here renders them.
  (ADR-0036, https://github.com/xippios/sdk-template/issues/174, https://github.com/xippios/sdk-template/issues/207)
  - Hand-apply: `src/xippios/<package>/_client.py` — a source that answers `tenant_param`
    exports `TENANTS`, `DEMO` and `check_<param>(<param>)`, the startup check of its
    servers' `serve_tenants`, and lists its tenant list and its variables' patterns in
    `ENV_VARS` — the template's `mcp.py`, `mcp_write.py` and `tests/conftest.py` import
    them.
    `src/xippios/<package>/tasks.py` — the tenant list, `list_task(TENANTS, name=...)`,
    stands in `__all__` — conventions §8 serves it on the read server.
    `scripts/refresh_reference.py` — a multi-tenant source fetches through
    `client_for(DEMO)` — no module-level client serves every tenant.
    `CLAUDE.md` — the `Credentials` and `Tenants` rows name the key's pattern, the tenant
    list and `demo`, and the rule of one limiter per host names `client_for(<param>)` — the
    render states them.
