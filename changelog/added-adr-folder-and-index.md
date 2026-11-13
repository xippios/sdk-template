- A generated repository has `docs/adr/` for its design decisions, one `NNNN-<slug>.md`
  record each, and `docs/reports/` for its dated reports, each folder with a README that
  lays its files out, and this repository keeps the same. `scripts/adr_index.py`, which
  needs the standard library alone, writes the index `docs/adr.md` and `docs/adr.json` from
  the records' headers, and its `--check` fails while either is stale. The script and the
  READMEs are the template's and the index is the source's, as `_skip_if_exists` now names
  the two scripts a source fills instead of all of `scripts/`, so `copier update` creates
  the new files and touches no script of a source's own.
  (https://github.com/xippios/sdk-template/issues/121)
