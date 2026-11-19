- The generated `CLAUDE.md` names `_TOKEN` among the endings of a variable that nobody
  reads or prints, where it named `_REFRESH_TOKEN`, as sdk-core's conventions §7 does, so
  the rule takes in every token's variable, a refresh token's among them.
  (ADR-0030, https://github.com/xippios/sdk-template/issues/169)
  - Hand-apply: `CLAUDE.md` — in the rule of `## Never` that starts "Never read or print",
    name the endings `_API_KEY`, `_TOKEN` or `_SECRET` in place of `_API_KEY`,
    `_REFRESH_TOKEN` or `_SECRET` — conventions §7 names `_TOKEN`, which covers a refresh
    token's variable and every other token's.
