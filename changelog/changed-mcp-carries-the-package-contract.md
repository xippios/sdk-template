- The generated `mcp.py` carries sdk-core 0.4.0's package contract: `build()` returns core's
  `ToolSet`, with the caps and the option hooks that `tasks.py` defines, `MCP_CAPS`,
  `mcp_add_options` and `mcp_apply_options`, `server` is `build_server(build())`, and
  `ENV_VARS`, which `_client.py` declares as `EnvVar` entries from the key answers and
  `live_secrets`, stands beside `SOURCE`. A host builds one server from several tool sets
  with `register_tasks`, and a source with options of its own defines them in `tasks.py`
  alone, as sdk-usda-gats and sdk-usda-nass do. An update merges a source's hand-written
  `mcp.py` three ways, a line of its own carried where the render leaves its place alone and
  conflicts where the render rewrites it, its imports, `build` and `run()` among them, two
  on sdk-cashctrl's `main`, which resolve to the render's lines but those the source keeps.
  (ADR-0026, https://github.com/xippios/sdk-template/issues/81, https://github.com/xippios/sdk-template/issues/65)
  - Hand-apply: `src/xippios/<package>/_client.py` — import `EnvVar` from `xippios.core`,
    declare `ENV_VARS: tuple[EnvVar, ...]` after `API_KEY_ENV`, one
    `EnvVar(<name or pattern>, secret=..., required=...)` per variable the package reads,
    the key first, and name it in `__all__` — the template's `mcp.py` imports it, so the
    package fails to import until it is there.
    `CLAUDE.md` — the Layout's `_client.py` line names `ENV_VARS` and its `mcp.py` line
    `build()` and `server` — the render names them.
