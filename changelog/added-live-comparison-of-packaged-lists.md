- The rendered `tests/test_live.py` collects xippios-core 0.4.1's nightly comparison of each
  packaged list with the list upstream serves now, that of sdk-core ADR-0055, by one star
  import, with `LIVE_LISTS` and `NO_LIVE_LIST` declared empty at its top level, and a render
  without reference data collects none. `/refresh-reference-data` says that a new packaged
  list takes its entry in `LIVE_LISTS`, or in `NO_LIVE_LIST` with the reason it is not
  compared, which core's family check holds.
  (https://github.com/xippios/sdk-template/issues/252)
  - Hand-apply: `tests/test_live.py` — add `from xippios.core.testing.live import *  # noqa: F403`
    with `LIVE_LISTS` and `NO_LIVE_LIST` at the top level, an entry for each packaged list,
    delete the source's own comparison of a packaged list and move a skip at the module's
    import into the tests or fixtures that need it — core's family check, by
    sdk-core ADR-0055, fails a packaged list in neither declaration and a module that skips
    at its import.
