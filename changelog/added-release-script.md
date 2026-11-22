- A render carries `scripts/release_prepare.py` and the assembler it loads by its path,
  `scripts/changelog_assemble.py`, the organization's one version of each, and
  `/release-prep` runs `python3 -I scripts/release_prepare.py <version> --date <YYYY-MM-DD>`
  in place of the assembly by hand. The script writes the release's section of
  `CHANGELOG.md` from the fragments, removes them and sets the version in `pyproject.toml`
  and on the package's own entry in `uv.lock`, with no `uv lock`, and a second run writes
  nothing. The rendered `pyproject.toml` leaves both scripts out of ruff, and mypy checks
  them with a generic without arguments let through in the assembler alone.
  (https://github.com/xippios/sdk-template/issues/247)
  - Hand-apply: `CLAUDE.md` — name `scripts/changelog_assemble.py` and
    `scripts/release_prepare.py` after `scripts/adr_index.py` among the files the update
    writes again, and lay both out under `scripts/` in `## Layout`, as a render has them —
    every update writes the two scripts again, and the Layout names each script the
    repository holds.
