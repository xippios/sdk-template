- `write_server: true` renders a write server: `mcp_write.py`, the template's, serves
  `tasks_write.__all__` as confirm-gated tools from a `build()` of its own, the
  `tasks_write.py` scaffold is the source's once rendered, and the entry points become
  `xippios-<slug>-mcp-read` and `xippios-<slug>-mcp-write`, with no alias for
  `xippios-<slug>-mcp`. A source with a write server of its own, as sdk-cashctrl and
  sdk-google-mail have, passes `-d write_server=true` to the update that takes this release,
  which keeps its `tasks_write.py` and leaves conflicts in its `mcp_write.py`, its own lines
  against the render's around the lines both share, three on sdk-cashctrl's `main`. The generated README configures the write server in a block
  of its own. (https://github.com/xippios/sdk-template/issues/174, https://github.com/xippios/sdk-template/issues/81)
  - Hand-apply: `README.md` — where the answer is `true`, the MCP block runs
    `xippios-<slug>-mcp-read` and a second block runs `xippios-<slug>-mcp-write` — the
    README named one entry point.
    `CLAUDE.md` — where the answer is `true`, the `Write tools` row names `tasks_write.py`
    and its entry point, and the Layout and the run command name the two servers — the
    file said the package is read-only.
