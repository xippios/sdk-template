- The capture skeleton, `scripts/refresh_upstream.py`, takes the fixes the sources made to
  their own copies and conventions §3's rules for a snapshot from core 0.4.0, which
  `/refresh-upstream` says how to fill and the stub of `docs/upstream/FETCHED.md`, taken by
  a new repository alone, lays out. Its attribution check reads a page's visible text,
  checks each `Statement` on the page that prints it, a terms page by its lines and an API
  document's `info` by what `ATTRIBUTION` records, and narrows by a `VOCABULARY` that
  `FETCHED.md` lists, while `--check` compares content, after a `canonical` hook, and
  prints a moved Last-Modified or sha256 as information. `linked`, `SPEC_PAGE`, `names=`,
  `sample=True` and `NOT_FETCHED` record the pages the sources met, no redirect to another
  host is followed, `FETCHED.md` lists `OBSERVED.md` and a table `Not fetched`, and a row
  with an ETag ends in the secret scan's allowlist mark.
  (https://github.com/xippios/sdk-template/issues/123,
  https://github.com/xippios/sdk-template/issues/42)
  - Hand-apply: `scripts/refresh_upstream.py` — where the source keeps a capture script of
    its own, port what it lacks of the skeleton at this tag: the visible-text check per
    page with `Statement`, `terms=True`, `VOCABULARY` and `INFO_TERMS`, `--check` by
    content with `canonical`, `stable=False` keeping Last-Modified, `linked`, `SPEC_PAGE`
    and `names=`, no redirect to another host with `NOT_FETCHED` and the table
    `Not fetched`, `sample=True` under `samples/`, the row of `OBSERVED.md`, the allowlist
    mark after a row with an ETag, whose audited `.secrets.baseline` entries go with the
    next refresh, and the converter's own dependencies pinned in the script's block, or
    `exclude-newer` — eight sources met these limits one at a time, conventions §3 asks
    the table, the row and the samples of every snapshot from core 0.4.0, and `FETCHED.md`
    follows at the next refresh, since an adoption fetches nothing.
    `CLAUDE.md` — in Never, write the rule on `docs/upstream/` as "Never edit
    `docs/upstream/` by hand but `docs/upstream/OBSERVED.md`, the notes on what upstream
    does but never documents" — conventions §3 makes that file the one written by hand.
