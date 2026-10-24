# Changelog

All notable changes to sdk-template are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the template uses
[Semantic Versioning](https://semver.org/). A generated repository records the tag it
was made from in `.copier-answers.yml`.

Every release ends with a **Hand-apply** list. `copier update` carries a template change
into the files it renders, but never touches a file under `_skip_if_exists` in
`copier.yml` once that file exists (task layer, models, endpoint wrappers, tests,
scripts, README, CHANGELOG, upstream snapshot, reference data). Each change to such a
file is one bullet, `` - `<path>` — <what> — <why> ``; port it by hand in the same
`chore/template-update` PR. A new file under those patterns is created by the update
where the repository has no file of that name. The list starts with 0.1.5; earlier tags
are not listed.

## [Unreleased]

### Added

- Questions `rate_limit_burst` (default `1`) and `rate_limit_provenance` (`documented` or
  `self-imposed`, default `documented`). `_client.py` renders
  `RateLimit(per_minute=..., burst=...)` under a comment naming the provenance, and the
  generated CLAUDE.md's rate-limit row states pace, burst and provenance (ADR-0010
  decision 1).
- Question `core_version` (default `0.1.0`, the current PyPI release): `pyproject.toml`
  depends on `xippios-core~=<core_version>`, the `mcp`, `http` and `testing` extras
  likewise, so a source depends on one core minor (conventions §12).
- `.github/workflows/live.yml`, the one rendered workflow: the `live` tests every night
  at 03:17 UTC and on `workflow_dispatch`, one job, `contents: read`, with
  `XIPPIOS_LIVE_TESTS=1` and, for a keyed source, the org secret named by `api_key_env`
  in that job's env and nowhere else (conventions §10).
- `tests/test_tasks_write.py` for write sources: the write server's tools are exactly the
  write tasks, no write task is a tool of the read server or a route of the router, every
  write task is a sync facade whose last parameter is `confirm: bool = False`, explained
  under `Args:` and a boolean defaulting to false in its tool's schema, and every write
  tool is marked destructive (conventions §8). Hand-rolled on core 0.1.0; core 0.2.0's
  `assert_write_tools` replaces most of it.
- `publish.yml` refuses to build a `pyproject.toml` that has `[tool.uv.sources]`, and
  `/release-prep` gains a step before the version bump that removes a core pin and
  raises `core_version` to the core release carrying the pinned change (conventions §12).
- This changelog, with a Hand-apply list per release.

### Changed

- `rate_limit_per_minute` is the pace, documented or self-imposed, no longer "the
  documented limit", in `copier.yml`, the README and the generated docs (ADR-0010). On
  `copier update`, an existing repository's `_client.py` gets `burst=1` (it had
  `burst = per_minute`) unless the update passes `-d rate_limit_burst=N`; pass
  `-d rate_limit_provenance=self-imposed` where upstream documents no limit.
- The core bound: `xippios-core~=<core_version>` replaces the hard-coded `>=0.1.0`. With
  `core_git_ref` set the bound stays `~=`: uv takes core from the git pin and does not
  check the bound against it. The `[tool.uv.sources]` comment says how to unpin
  (`uvx copier update --defaults --vcs-ref=:current: -d core_git_ref= -d core_version=X.Y.Z`),
  and its `rev` line carries `# pragma: allowlist secret`, so a 40-character commit SHA
  no longer trips detect-secrets.
- `_client.py` renders `__all__` one sorted name per line with a trailing comma, so a
  source that exports one more name no longer conflicts on every update.
- mypy checks `scripts/` too (`files = ["src", "tests", "scripts"]`).
- The sdist leaves out `tests/fixtures`.
- `http.py`'s docstring: `GET` for a task whose parameters are all scalars, `POST`
  otherwise (ADR-0007), as `tests/test_adapters.py` asserts.
- `/refresh-upstream`: fetch dates are UTC in ISO 8601 (a date `YYYY-MM-DD`, a timestamp
  with `Z`), and `scripts/refresh_upstream.py` may change in the snapshot PR.
- `/refresh-reference-data`: a source need not package lists, a multi-tenant source
  packages no tenant data (ADR-0014), the refresh script runs with whatever the list
  endpoints need rather than a key as a given; agents get one lookup task per list or
  the upstream's own lookup operation when it serves every list through one; the enums
  formatting step links the core fix, sdk-core#20, instead of a workspace-local file.
- `/record-fixture`, `/add-endpoint` and the `models.py` example name no source
  (ADR-0008: nothing source-specific is scaffolded).
- Human step 2 (`_message_after_copy`, `scripts/new-source.sh`, `/new-source`): for a key
  several sources share (ADR-0009), add the repository to the existing org secret's
  repository access; never `gh secret set --repos`, which replaces the list.
- The generated CLAUDE.md names the provider level among the `__init__.py` files never to
  add, describes `live.yml` and the write test, and points at this changelog's
  Hand-apply lists for template updates.
- The `CHANGELOG.md` scaffold names the write server for a write source.

### Fixed

- `scripts/refresh_reference.py` passes `mypy --strict`: `LISTS` holds coroutine
  functions, which is what `xippios.core.sync` takes.
- `tests/test_layout.py` stops at the `xippios` directory and fails with a message when
  there is none, instead of looping for ever.
- `tests/test_live.py`: the reachability check sends no key, so it spends no quota call
  on a keyed gateway.
- `tests/test_tasks.py`: the placeholder test keeps requests, URLs and header values out
  of its frame, so `pytest -l` cannot print the shell's key.
- `.secrets.baseline`, generated and the template's own, drops the `is_swagger_file`
  filter, which exempted every path containing "swagger" (verbatim upstream Swagger
  snapshots among them) from the scan; sdk-core dropped it too.

### Hand-apply

- `tests/test_tasks_write.py` (write sources) — new: the write server serves exactly
  `tasks_write.__all__`, no write task is on the read server or the router, every write
  task is a sync facade with `confirm: bool = False` last, explained in its docstring and
  boolean in its tool schema, and every write tool is marked destructive — conventions
  §8 had no generated test. `copier update` creates the file where there is none; a
  source with a `tests/test_tasks_write.py` of its own (sdk-cashctrl, which checks this
  with core's `assert_write_tools` in `tests/test_adapters.py`) keeps its file and adds
  only the checks it lacks.
- `tests/test_layout.py` — `test_namespace_levels_have_no_init` walks `PACKAGE_DIR.parents`
  up to the `xippios` directory and asserts it exists — the `while True` loop never ended
  for a package without an `xippios` ancestor.
- `tests/test_live.py` — `test_upstream_answers` sends a plain `httpx.AsyncClient` GET to
  `BASE_URL` (the family User-Agent and the client's timeouts, redirects followed) and
  asserts `status_code < 500` — through the package's client it sent the key to `/`,
  which a keyed gateway answers with 404 while counting a quota call.
- `tests/test_tasks.py` (keyed sources) — the auth-flow call moves into
  `send_through_auth`, which returns an `AuthReport` of booleans and the `where` text,
  and the test asserts its fields — with the request, its URL and its headers in the
  test's frame, `pytest -l` would print the shell's key once the placeholder pin had
  failed.
- `scripts/refresh_reference.py` — `LISTS` is typed
  `dict[str, Callable[[], Coroutine[Any, Any, list[str]]]]` (imports `Coroutine` and
  `Any` instead of `Awaitable`), and the docstring asks for whatever the list endpoints
  need, not the API key, and says a multi-tenant source packages no tenant data — the
  updated `pyproject.toml` has mypy check `scripts/`, where the old annotation fails
  `--strict` twice at `values = sync(fetch)()`; port it in the update PR itself, together
  with any other script there that `mypy --strict` now reports.
- `src/xippios/<pkg>/reference/README.md` — the lookup rule reads "one lookup task per
  list, `list_<thing>`, ..., or the upstream's own lookup operation when it serves every
  list through one", and a rule says a multi-tenant source packages no tenant data — the
  per-list rule did not fit a source whose upstream serves every list through one
  operation (ADR-0014 for the tenant rule).

New repositories only, nothing to port: the `CHANGELOG.md` scaffold's write-server clause
and the source-neutral example in the `models.py` docstring (the `README.md` scaffold is
unchanged).

## [0.1.5] - 2026-10-23

### Added

- `.gitattributes` with `docs/upstream/** -text`: the upstream snapshot stays byte for
  byte (CRLF, mixed endings).
- `tests/test_tasks.py` in keyed sources: `test_replay_tests_send_the_placeholder_key`
  checks the request the client's auth sends outside a live test.

### Changed

- `models.py` and `/add-endpoint`: upstream spellings are accepted with
  `Field(validation_alias=...)`, never `alias=`, which the adapters would serialise.
- `/refresh-upstream` runs `scripts/refresh_upstream.py` where a source keeps one.
- `/refresh-reference-data` formats the regenerated `enums.py` and names the pending core
  fix; `reference/README.md` gives each packaged list a `list_<thing>` lookup task.
- The read server's instructions word the list-tool hint so it holds before any list
  tool exists.
- The template's CLAUDE.md names the two copies that deviate from sdk-core, and why.

### Fixed

- Replay tests always send the placeholder key: the conftest fixture pins the key
  variable and `auth.key` for every test not marked `live`, whatever the shell holds.
- `_client.py` exports `auth` in keyed sources (the conftest imports it).
- detect-secrets: `.copier-answers.yml` is excluded from a baseline rescan as well as
  from the hook.
- Generated `.gitignore` covers `.env.*` and `.envrc.*`.
- `new-source.sh` titles the scaffold PR `chore:`, like its commit.

### Hand-apply

- `tests/conftest.py` (keyed sources) — `placeholder_api_key` pins both the key variable
  and `auth.key` to `PLACEHOLDER_KEY` in every test not marked `live` and returns it
  (`None` in a live test) — the auth caches the key per object, so a live test earlier in
  the run, or a key set in the shell, sent the real key in replay tests.
- `tests/test_tasks.py` (keyed sources) — new `test_replay_tests_send_the_placeholder_key`
  — proves on the outgoing request that the pin holds; port the Unreleased form, which
  also keeps the request out of the test's frame.
- `src/xippios/<pkg>/models.py` — the module docstring recommends
  `Field(validation_alias=...)` and warns against `alias=` — guidance only; port it if the
  file still carries the scaffold docstring.
- `src/xippios/<pkg>/reference/README.md` — each packaged list gets a `list_<thing>`
  lookup task, added by `/refresh-reference-data` where missing — port the Unreleased
  wording, which supersedes it.
