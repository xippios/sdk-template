- A render collects xippios-core 0.4.1's check of a built answer's mark, as
  sdk-core ADR-0049 records it, in `tests/test_built_answers.py`, its one line followed by
  the source's `READERS` and `ALLOWED`, and `/add-endpoint` says how a test marks an answer
  it builds. The module is the source's once rendered, so `copier update` creates it where a
  source has none and leaves the source's declarations alone after. The template's rendered
  tests build no answer, so a new source passes the check before its first test.
  (§10, https://github.com/xippios/sdk-template/issues/271)
  - Hand-apply: `CLAUDE.md` — name `test_built_answers.py` under `tests/` in the Layout,
    and `tests/test_built_answers.py` after `tests/test_live.py` among the files the
    package fills, as a render with the package's answers has them — the update creates the
    module and never writes the package's `CLAUDE.md`.
    `tests/test_built_answers.py` — where the source holds a module of that name of its
    own, as sdk-cashctrl does, replace its own check by the collecting line with the
    source's `READERS` and `ALLOWED` below it — the update keeps a file of that name as it
    stands.
