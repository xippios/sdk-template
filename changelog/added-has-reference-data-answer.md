- A source that packages no reference data answers `has_reference_data: false`: none of
  `params.py`, `enums.py`, `reference/`, `scripts/refresh_reference.py` and
  `/refresh-reference-data` renders, and no update brings them back, where copier brought
  back the deleted script. Such a source passes `-d has_reference_data=false` to the update
  that takes this release, which deletes the files the template rendered, the source's
  lines in them included, and leaves a file the source added under `reference/` for the
  source to delete. Every other source keeps the default, `true`, and its scaffold.
  (https://github.com/xippios/sdk-template/issues/40)
  - Hand-apply: `CLAUDE.md` — where the answer is `false`, drop the Layout's rows of
    `params.py`, `enums.py`, `reference/` and `refresh_reference.py`, the command
    `refresh-reference-data` from the `.claude/commands/` row, and the four from the files
    the Template updates section names — the update deletes them, and a render with the
    answer names none of them.
