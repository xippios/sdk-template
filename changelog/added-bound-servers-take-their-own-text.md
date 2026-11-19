- A multi-tenant render's `mcp.py` and `mcp_write.py` define `BOUND_INSTRUCTIONS`, each
  server's text without the clause that a tool takes the tenant's argument, and `build(lock)`
  passes it to core's `tenant_instructions` as `bound=`, as sdk-core ADR-0036 decision 7
  has it. A server that `--<param>` binds no longer says that a tool takes the tenant's
  argument, and core's closing sentence names the tenant. At its update sdk-google-mail's
  own `BOUND_INSTRUCTIONS` merge with the render's, the write server's whole and the read
  server's but for its last line, where a conflict opens that runs through `run()`.
  (https://github.com/xippios/sdk-template/issues/219)
