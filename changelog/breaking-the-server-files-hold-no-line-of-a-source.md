- The rendered `mcp.py` and `mcp_write.py` hold no line of a source: `build()` returns the
  tool set that xippios-core builds from the tasks module, `ToolSet.from_tasks`, `run()`
  calls core's one `main`, with the registry and the check for a multi-tenant source, and
  `http.py` passes `tool_functions(tasks)`, the list that `mcp.py` serves. An update renders
  the three files again and merges a source's own edit of its earlier render into them, as
  into every file of the template's, silently where this release leaves the lines around the
  edit alone and as a conflict where it changes them, so a source takes the render's text by
  hand. The scaffolds of `tasks.py` and `tasks_write.py` hold the server's instructions as
  `MCP_INSTRUCTIONS`, and a multi-tenant source's bound text as `MCP_BOUND_INSTRUCTIONS`, the
  scaffold of `__init__.py` re-exports the tenant list task where `tasks.py` lists it, and
  for new repositories only the comments of `_client.py` name core's one `KeyAuth`.
  (ADR-0002, https://github.com/xippios/sdk-core/issues/476)
  - Hand-apply: `src/xippios/<import path>/tasks.py` — move the instructions that `mcp.py`
    held, `INSTRUCTIONS`, into `MCP_INSTRUCTIONS`, and a multi-tenant source's
    `BOUND_INSTRUCTIONS` into `MCP_BOUND_INSTRUCTIONS`, declare in sdk-google-mail
    `MCP_LOOPBACK_ONLY = True` for its read server held to loopback, and give
    `mcp_apply_options` where it is declared, as in sdk-usda-gats and sdk-usda-nass, core's
    signature, `mcp_apply_options(namespace) -> None`, without the server — core reads them
    from the tasks module, and the render's `mcp.py` holds none of them.
    `src/xippios/<import path>/tasks_write.py` — move the write server's instructions into
    `MCP_INSTRUCTIONS` likewise, and a multi-tenant source's bound text into
    `MCP_BOUND_INSTRUCTIONS` — the same, for `mcp_write.py`.
    `src/xippios/<import path>/_client.py` — in sdk-cashctrl, pass its noun for a tenant
    as `Tenants(noun=...)` — core's `main` reads the noun from the registry.
    `src/xippios/<import path>/__init__.py` — import and list in `__all__` each task of
    `tasks.__all__` and `tasks_write.__all__` that it does not re-export yet — core's
    family check holds that every task is the package's own.
    `src/xippios/<import path>/mcp.py` — after the update, compare it with a render of this
    release with the source's answers and take the render's text wherever the two part, a
    line of the source's that the update kept without a conflict included — the update
    merges a source's own edit into the render and says nothing where this release leaves
    the lines around it alone, and no line of the file is a source's (ADR-0002, decision 9).
    `src/xippios/<import path>/mcp_write.py` — the same, where the source has a write
    server, and in sdk-cashctrl, whose update keeps its line
    `server = build_server(build(), name=...)`, take the render's line
    `server = build_server(build())`, so that its write server takes the name
    `xippios-cashctrl` and keeps none of its own —
    the same, and both servers of a source are named `xippios-<source>`.
    `src/xippios/<import path>/http.py` — compare it with the render likewise and take the
    render's text — the same.
