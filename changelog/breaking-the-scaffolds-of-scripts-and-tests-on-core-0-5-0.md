- The rendered `scripts/refresh_reference.py` declares its lists in one `Lists` of
  xippios-core, with the package, the lists it ships, its client and the quota header, and
  its `main` calls core's `run(LISTS, argv)`; its commented examples reach a new render
  alone, among them a list of values whose fetch makes its records from the values in its
  wrapper's `Answer`, since core's frame refuses an `Answer` of plain values.
  `tests/test_built_answers.py` is its collecting line alone, without `READERS` and
  `ALLOWED`, which core's check no longer reads, and `tests/test_live.py` holds no probe of
  upstream's base URL,
  `test_upstream_answers`, and imports neither `httpx` nor the client's `BASE_URL` and
  `config`. A render without reference data therefore holds no live test until its first
  task brings its smoke test, and its nightly run exits with pytest's status 5 until then,
  as the probe of the scaffold's host that never resolves failed it before.
  (https://github.com/xippios/sdk-core/issues/482, https://github.com/xippios/sdk-core/issues/483,
  https://github.com/xippios/sdk-core/issues/477, https://github.com/xippios/sdk-template/issues/342,
  https://github.com/xippios/sdk-template/issues/343)
  - Hand-apply: `scripts/refresh_reference.py` — declare
    `LISTS = Lists(package=PACKAGE, lists=(...), packaged=PACKAGED_LISTS, client=client,
    quota_header=...)` from what it passed to `run`, its `Listed` entries as they stand,
    and call `run(LISTS, argv)` — core's `run` takes one declaration and no keyword.
    `tests/test_built_answers.py` — keep its collecting line alone, deleting `READERS` and
    `ALLOWED`, empty or filled, with the comment above them, and give a place that the
    check then fails a kind of conventions §10 or the input's sentence — the check reads
    neither.
    `tests/test_live.py` — delete `test_upstream_answers` and its imports of `httpx` and of
    `BASE_URL` and `config` where nothing else uses them — core's family check and each
    task's smoke test hold what the probe held.
    `src/xippios/<import path>/reference/README.md` — where the provenance table's header
    is not `| File | Origin | Fetched |`, take that one — core's frame knows that header
    alone.
