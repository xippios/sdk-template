- A render cites each record of sdk-core as `sdk-core ADR-NNNN`, by the number of the record
  that stands at core 0.4.0, in every file but `docs/adr/README.md` and the lines copied
  from sdk-core, the fixture cap's step in `ci.yml` and its message among them, since a
  bare `ADR-NNNN` names a record of the source's own. A citation of a record that core
  0.4.0 restated takes the record that supersedes it, as sdk-core's `docs/adr.md` lists
  them, with its decision as that record numbers it, and the help of `core_version` cites
  sdk-core ADR-0039 decision 1 for the bound `~=X.Y.Z`. Two of them stand in the sentences
  that a source's capture script writes into `docs/upstream/FETCHED.md`, so its `--check`
  names `FETCHED.md` until its next capture run writes the file again.
  (https://github.com/xippios/sdk-template/issues/155, https://github.com/xippios/sdk-template/issues/205, https://github.com/xippios/sdk-template/issues/212)
  - Hand-apply: `src/xippios/<package>/_client.py` — search the file for `ADR-` and write
    each citation of a record of sdk-core as `sdk-core ADR-NNNN`, by the record that stands
    in sdk-core's `docs/adr.md` at v0.4.0, a superseded record's decision or amendment as
    the record that supersedes it names it, and leave a citation of a record of the
    source's own bare — a bare `ADR-NNNN` names the source's own record, as its
    `docs/adr/README.md` lays them out, and the scaffold cited the records core restated.
    `src/xippios/<package>/__init__.py` — the same — the same.
    `src/xippios/<package>/errors.py` — the same — the same.
    `src/xippios/<package>/models.py` — the same — the same.
    `src/xippios/<package>/api/` — the same — the same.
    `src/xippios/<package>/parse/` — the same — the same.
    `src/xippios/<package>/tasks.py` — the same — the same.
    `src/xippios/<package>/tasks_write.py` — the same — the same.
    `src/xippios/<package>/params.py` — the same — the same.
    `scripts/refresh_reference.py` — the same — the same.
    `scripts/refresh_upstream.py` — the same, and where the script captures, run
    `uv run scripts/refresh_upstream.py` after it, a capture run that fetches every page
    once, so that the script writes `docs/upstream/FETCHED.md` again and `--check` passes,
    never `FETCHED.md` by hand — `render_fetched` writes two of the citations into
    `FETCHED.md`, wrapped at 88 columns, `--check` names the file until the script writes
    it again, and a skeleton's stub takes them at the first capture.
    `tests/test_tasks.py` — the same — the same.
    `tests/test_live.py` — the same — the same.
    `tests/fixtures/files/README.md` — the same — the same.
    `README.md` — the same — the same.
    `CLAUDE.md` — the same — the same.
