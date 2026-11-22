- `scripts/adr_index.py` is the one version that the organization's repositories share, which
  opens each line of `docs/adr.md` with the anchor that a citation such as `docs/adr.md#0014`
  links to and lists the records in force before the superseded ones. The rendered
  `pyproject.toml` leaves the script out of ruff while mypy checks it, and every command runs
  it as `python3 -I`. A source writes its index again with the new script in its adoption pull
  request, since the check `adr-index` fails on the index that the old one wrote.
  (https://github.com/xippios/sdk-core/issues/357, https://github.com/xippios/sdk-template/issues/246)
  - Hand-apply: `CLAUDE.md` — write the index command of `## Commands` as
    `python3 -I scripts/adr_index.py --check` — the check `adr-index` runs the script
    isolated, and people run it as the check does.
    `docs/adr.md` — write it again with `python3 -I scripts/adr_index.py` — the new script
    opens each line with its record's anchor and lists the superseded records last.
