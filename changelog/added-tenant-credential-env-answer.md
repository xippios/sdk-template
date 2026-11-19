- `tenant_credential_env` names the variable of each tenant's credential,
  `<PREFIX>_<NAME>_<FIELD>`, for a multi-tenant source whose tenants hold no key, a refresh
  token say, so `tenant_param` renders the tenant shape without `api_key_env`: core's
  `Tenants` takes the prefix as `var_prefix` and the field as its one field, the reserved
  `demo` is declared by `<PREFIX>_DEMO_<FIELD>`, which the offline tests pin and `live.yml`
  passes, and `ENV_VARS`, the README and the CLAUDE.md name the credential's variables.
  The template's `mcp.py`, `mcp_write.py` and `tests/conftest.py` render as for tenants with
  a key, the scaffold of `_client.py` leaves the auth to the source, and a source whose
  tenants hold a key renders as before, with nothing more to answer.
  sdk-google-mail passes `-d write_server=true -d tenant_param=account
  -d tenant_credential_env=GOOGLE_<NAME>_REFRESH_TOKEN` and `live_secrets` without
  `GOOGLE_DEMO_REFRESH_TOKEN`, and the update leaves three conflicts in `mcp.py`, three in
  `mcp_write.py`, one in `tests/conftest.py`, the whole file, and two in `pyproject.toml`,
  its consent entry point and its placeholder list, on its `main`.
  (ADR-0036, https://github.com/xippios/sdk-template/issues/207, https://github.com/xippios/sdk-template/issues/209)
  - Hand-apply: `src/xippios/<package>/_client.py` — where the tenants hold no key,
    `TENANTS` takes `fields=("<FIELD>",)`, and `var_prefix="<PREFIX>"` where the slug gives
    another, `check_<param>(<param>)` checks `TENANTS.field(<param>, "<FIELD>")`, and
    `ENV_VARS` lists `<PREFIX>_<PARAM>S` and `<PREFIX>_<NAME>_<FIELD>` — the render derives
    them from the answer, and the template's servers import `check_<param>` and `ENV_VARS`.
    `README.md` — the environment line and the MCP blocks name `<PREFIX>_<NAME>_<FIELD>`,
    `<PREFIX>_ACME_<FIELD>` and `<PREFIX>_DEMO_<FIELD>` — the render names the credential,
    never a key.
    `CLAUDE.md` — the `Credentials` row names `<PREFIX>_<NAME>_<FIELD>` and the source's
    auth, and the `Tenants` row `<PREFIX>_DEMO_<FIELD>` — the render said the API is open.
