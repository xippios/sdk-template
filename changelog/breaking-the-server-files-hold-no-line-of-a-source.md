- The rendered `mcp.py` and `mcp_write.py` hold no line of a source, and an update writes
  them and `http.py` whole: `build()` returns the tool set that xippios-core builds from the
  tasks module, `ToolSet.from_tasks`, `run()` calls core's one `main`, with the registry and
  the check for a multi-tenant source, and `http.py` passes `tool_functions(tasks)`, the
  list that `mcp.py` serves. The scaffolds of `tasks.py` and `tasks_write.py` hold the
  server's instructions as `MCP_INSTRUCTIONS`, and a multi-tenant source's bound text as
  `MCP_BOUND_INSTRUCTIONS`, and the scaffold of `__init__.py` re-exports the tenant list
  task where `tasks.py` lists it. For new repositories only, the comments of `_client.py`
  name core's one `KeyAuth`. (ADR-0002, https://github.com/xippios/sdk-core/issues/476)
  - Hand-apply: `src/xippios/<import path>/tasks.py` — move the instructions that `mcp.py`
    held, `INSTRUCTIONS`, into `MCP_INSTRUCTIONS`, and a multi-tenant source's
    `BOUND_INSTRUCTIONS` into `MCP_BOUND_INSTRUCTIONS`, declare in sdk-google-mail
    `MCP_LOOPBACK_ONLY = True` for its read server held to loopback, and give
    `mcp_apply_options` where it is declared, as in sdk-usda-gats and sdk-usda-nass, core's
    signature, `mcp_apply_options(namespace) -> None`, without the server — core reads them
    from the tasks module, and the update writes `mcp.py` without them.
    `src/xippios/<import path>/tasks_write.py` — move the write server's instructions into
    `MCP_INSTRUCTIONS` likewise, and a multi-tenant source's bound text into
    `MCP_BOUND_INSTRUCTIONS` — the same, for `mcp_write.py`.
    `src/xippios/<import path>/_client.py` — in sdk-cashctrl, pass its noun for a tenant
    as `Tenants(noun=...)`, and let its write server take the name `xippios-cashctrl` and
    keep none of its own — core's `main` reads the noun from the registry, and both servers of a
    source are named `xippios-<source>`.
    `src/xippios/<import path>/__init__.py` — import and list in `__all__` each task of
    `tasks.__all__` and `tasks_write.__all__` that it does not re-export yet — core's
    family check holds that every task is the package's own.
