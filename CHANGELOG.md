# Changelog

All notable changes to sdk-template are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the template uses
[Semantic Versioning](https://semver.org/). A generated repository records the tag it
was made from in `.copier-answers.yml`.

Every release ends with a **Hand-apply** list. `copier update` carries a template change
into the files it renders, but never touches a file under `_skip_if_exists` in
`copier.yml` once that file exists (the package `__init__.py`, the client, models,
endpoint wrappers, the task layer, the packaged lists and enums, reference data,
scripts, the task and live tests and the fixtures, upstream snapshot, README and
CHANGELOG). Each change to such a file is one bullet,
`` - `<path>` — <what> — <why> ``; port it by hand in the same `chore/template-update`
PR. A new file under those patterns is created by the update where the repository has no
file of that name. The list starts with 0.1.5; earlier tags are not listed.

## [Unreleased]

### Removed

- The write side. sdk-cashctrl stands alone (Johannes's decision of 2026-10-25,
  ADR-0024): the one source with write tools keeps its write server and tests it
  itself, on its last template tag, and the template renders read-only packages only.
  Gone are the `needs_write_tools` question and what it rendered: `mcp_write.py` with
  the `xippios-<slug>-mcp-write` entry point in `pyproject.toml`, the `tasks_write.py`
  scaffold, the generated `tests/test_tasks_write.py` (confirm last and documented), the
  write lines of the generated `README.md`, `CLAUDE.md`, `CHANGELOG.md` and `live.yml`,
  and the two `_skip_if_exists` entries; `/adopt-release` and the generated `CLAUDE.md`
  no longer list `tasks_write.py` and `tests/test_tasks_write.py` among the files a
  source fills. Conventions §8 still governs a write server: the `confirm` check and the
  loopback rule are core's.
- The `basic` key location (`BasicKeyAuth`, the key as the HTTP basic user name), which
  only sdk-cashctrl answered: `api_key_location` offers `query`, `header` and `bearer`,
  and `api_key_name` is asked for `query` and `header` as before.
- Template-internal: the template tests lose the write variants, the `basic` case and
  every assertion on them; the variants that carried them keep their other answers (a
  header key, a long name, a git-pinned core, now with a bearer key).

### Hand-apply

None. The scaffolds of `_client.py`, `README.md` and `CHANGELOG.md` lose their write and
`basic` branches and the README's status comment no longer names `tasks_write.__all__`,
which matters to new repositories only. The two files under `_skip_if_exists` the
template stops rendering, `src/xippios/<package>/tasks_write.py` and
`tests/test_tasks_write.py`, exist only in a repository generated with write tools,
sdk-cashctrl alone, which stays on its last template tag: `copier update` to this
release would delete both, a write task of its own included, with no conflict marker,
and turn its `basic` answer into the default `query` (checked with copier 9.19.1). No
other repository has them.

**Updating from 0.2.2.** `copier update` drops `needs_write_tools` from
`.copier-answers.yml` (checked with copier 9.19.1); no `-d` answer is needed for it.

## [0.2.2] - 2026-10-27

The gates repository `xippios/.github` was renamed to `xippios/sdk-gates` on 2026-10-27;
v0.2.1 renders `gates.yml` calling the old name, v0.2.2 the new one. A source adopts this
release together with core 0.2.1 from PyPI, in one adoption PR (conventions §15) that
`/adopt-release v0.2.2` walks, with `core_version=0.2.1` and the bound `~=0.2.1`; a
source already on v0.2.1 updates with nothing to hand-apply.

### Changed

- `gates.yml` (the template's own and the one it renders) calls the gates repository
  under its new name `xippios/sdk-gates` (renamed from `.github` on 2026-10-27).
  `copier update` carries it (`gates.yml` is not under `_skip_if_exists`), so it needs
  no Hand-apply bullet.

### Hand-apply

None.

**Updating from 0.2.1.** `copier update` carries `gates.yml`; no answer changes. A
repository still on 0.2.0 reads 0.2.1's paragraph as well (with v0.2.2 in place of
v0.2.1).

## [0.2.1] - 2026-10-27

Generated repositories depend on xippios-core 0.2.1 (conventions 1.15) and take two
things from it: the release train, in which a release PR's merge tags the release and
Johannes approves the `pypi` run, and core's family check, `tests/test_family.py`, which
replaces the layout and adapter tests every source carried. The template tags its own
releases the same way from this one on, through `release.yml`. A source adopts this
release together with core 0.2.1 from PyPI, in one adoption PR (conventions §15) that
`/adopt-release v0.2.1` walks, with `core_version=0.2.1` and the bound `~=0.2.1`, since
`tests/test_family.py` imports what core 0.2.0 lacks; before the update it moves the
tests of its own out of `tests/test_adapters.py`, which the update deletes (Hand-apply).

### Added

- `tests/test_family.py`, template-owned, one line:
  `from xippios.core.testing.family import *  # noqa: F403`. It collects core 0.2.1's
  family check (conventions §10, ADR-0013 amendment): the empty namespace levels,
  `py.typed` and `__version__`; `mcp.py` and `http.py` serving exactly `tasks.__all__`
  minus `BULK_TASKS`, the write server exactly `tasks_write.__all__`; every task
  synchronous, returning `Result[T]`, with an agent docstring; the README status table
  listing exactly the read and the write tasks; a template tag in `.copier-answers.yml`;
  the core bound `~=X.Y.Z`. The check finds the package under test as the one `tasks.py`
  under `src/xippios/`, so the scaffold sets no `xippios_package` ini option; a repository
  with several names its package there.
- `.github/workflows/gates.yml`, core 0.2.1's file: the `merge-class` and `family-review`
  workflows of `xippios/.github`, called as jobs, each only when the repository variable
  `GATES_CALLER` is `1`, which Johannes sets per repository if the ruleset editor offers
  no "Require workflows" rule (the caller wiring of the `xippios/.github` README). It
  ships off.
- `ci.yml` carries the two family checks that read the pull request rather than the
  package, as core's `docs/handover.md` gives them: "CHANGELOG.md has an entry" on every
  PR but a release (`chore/release-*`), an adoption (`chore/template-update*`) or
  Dependabot's (`dependabot/`, which writes no entry), and "Fixture files under 256 KiB"
  on the fixture files a PR adds or changes, a moved one included (`--no-renames`),
  `LEVEL: warning` in this release and `error` from v0.3.0, when the cap binds a source
  (ADR-0019; conventions 1.14's header). The checkout fetches the whole history
  (`fetch-depth: 0`) for `git diff origin/<base>...HEAD`.
- The README scaffold's status table carries a comment naming the format the family
  check reads: the `## Status` heading and the `Task function` column kept, the task's
  name first in its cell, in backticks, several tasks of a row as backticked names
  separated by commas.
- The template's own `.github/workflows/release.yml`: on every push to `main` it reads the
  top `## [X.Y.Z] - ` heading of `CHANGELOG.md` and, when `vX.Y.Z` has no tag yet, tags
  the merge commit with that section as the tag's message; otherwise it ends quietly
  (conventions §12, ADR-0018 amendment (b)). The release PR of this release is the first
  that tags itself.
- The template's own `.github/workflows/gates.yml`, core 0.2.1's file, byte for byte the
  one it ships, which the template tests check: sdk-template carries the gates caller as
  every repository does, off until Johannes sets `GATES_CALLER` on it.
- `scripts/new-source.sh` enables auto-merge and branch deletion on merge on the new
  repository (`gh repo edit --enable-auto-merge --delete-branch-on-merge`; sdk-usda-esr
  found that a new repository's first release or adoption PR could not auto-merge,
  ADR-0018), gives the sessions' team `sdk-sessions` write access to it when the team
  exists (until then it prints a notice and goes on), reading the team in the pre-flight
  beside the organisation's default-branch check so that any other error stops it before
  anything is created, and reminds that a session owns `sdk-<slug>` in the workspace's
  `coordination/owners.toml` before the repository is generated there, since the
  workspace's guard refuses work in a directory no session owns.
- `copier.yml`: `core_git_ref` accepts only an empty value, `main` or a full 40-character
  lowercase commit SHA, the forms uv and the merge-class check read as one commit; a
  short SHA, a tag or another branch is refused. Both validators, this one and
  `core_version`'s, anchor their pattern at the very end (`\Z`), so a value with a
  trailing newline is refused too.

### Changed

- The release train (conventions §12, ADR-0018 amendment (b)). `publish.yml` is core
  0.2.1's: it runs on every push to `main` and on dispatch; `release-check` lets through
  a push that changed `pyproject.toml` or `CHANGELOG.md` when the version has no tag and
  `CHANGELOG.md` has its `## [X.Y.Z] - ` heading, so a first release, whose version the
  scaffold already says, tags itself from its CHANGELOG change; then CI, the annotated
  tag `vX.Y.Z` on the merge commit with the CHANGELOG section as its message, the build
  checked against that tag, and the `pypi` environment that Johannes approves. No session
  and no human pushes a source's tag. The workflow's header gives the recovery path and
  the race of two pushes close together. The template's one step beyond core's file,
  "Refuse a pyproject with [tool.uv.sources]", moves from the build into the `tag` job,
  before the tag, so a pinned release leaves no tag without a release.
- `ci.yml` is core 0.2.1's plus the two steps above: no push trigger of its own (a push
  to `main` runs it once, through `publish.yml`, for a release) and every action pinned
  by commit SHA.
- `core_version` defaults to `0.2.1`, rendered `xippios-core~=0.2.1`, the patch case of
  conventions §12 (ADR-0018 amendment (c)): `tests/test_family.py` imports what 0.2.0
  lacks. Its help says so: a patch floor rests on that amendment, after a core git pin or
  not.
- `tests/conftest.py` keeps `pytest_plugins` only: core 0.2.1's plugin provides
  `anyio_backend` (asyncio).
- `/release-prep`: a release PR changes only the subset of conventions §12
  (`pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `README.md`, `CLAUDE.md`,
  `docs/handover.md`, and `scripts/check-siblings.sh` where a source has one); a core
  pin's removal and a reference-data refresh are PRs of their own before it (conventions
  §12; the reference-data step from the sdk-usda-nass release review). Its merge tags
  through `publish.yml` and Johannes approves the `pypi` run, so no step tells a human to
  tag; the session enables auto-merge only when the merge class is `auto` (ADR-0018
  amendment (e)). A first release keeps the scaffold's `0.1.0` and needs the PyPI pending
  publisher before the approval; the heading is re-dated if the merge slips to a later
  day; a moving `main` is merged in, never force-pushed (from the sdk-cashctrl 0.1.0
  release review).
- `/adopt-release` follows conventions 1.15's §15: the core release `X.Y.Z` the template
  release names, with the patch-case bound (`~=0.2.1` for v0.2.1); a helper core lacks is
  carried by the source and named in a queue row, a second copy only when the row names
  both, never a third (ADR-0023); the fixtures, mounts and tests the adoption makes dead
  may go, nothing else (ADR-0018 amendment (d)); `docs/upstream/FETCHED.md` stays for the
  next `/refresh-upstream` (ADR-0003 amendment); a file the template release removes is
  deleted by the update, so step 3 first moves the tests of the source's own out of it,
  before the `copier update` command, with `git show HEAD:tests/test_adapters.py` as the
  way back when the update ran first; the examples name core 0.2.1, template v0.2.1 and
  conventions 1.15; the session enables auto-merge only when the merge class is `auto`,
  and a `human` adoption waits for Johannes (ADR-0018 amendment (e)); the PR body counts
  the live calls and carries `## Decisions taken`.
- `/add-endpoint`: `tests/test_family.py` proves that a new task is served, shaped and
  listed; the status-table row's format.
- The generated CLAUDE.md: the layout names `tests/test_family.py` and `gates.yml`; the
  PR-body rules add the open questions, the live-call count, the `## Decisions taken`
  block and sdk-core's `docs/review-checklist.md` (also under Read first); every PR but a
  release, an adoption or Dependabot's adds a CHANGELOG entry; the release train, whose
  release PR changes only conventions §12's subset (with `scripts/check-siblings.sh`
  where the source has one); the update and Never sections allow auto-merge by merge
  class only; the quota sentence shows the `QuotaPolicy` installation instead of pointing
  at a commented block that a repository generated before v0.2.0 lacks (from the
  sdk-usda-nass adoption review).
- `.github/PULL_REQUEST_TEMPLATE.md` is core 0.2.1's, sha256 `657a5d0e…`; v0.2.0's copy
  lagged the definition of done, as the template's own core 0.2.0 adoption found. It
  mirrors the definition of done: the pointer to sdk-core's `docs/review-checklist.md`,
  a core PR's consumers, the fixture grep for the fields a source keeps out of its
  projections, the fixture cap and file samples, the Adoption PR block and its intro,
  the Process lines (the session's auto-merge only when the merge class is `auto`,
  ADR-0018 amendment (e); the live-call count; the `## Decisions taken` block; the
  release subset), and headings of their own for Assumptions, Open questions and
  Decisions taken.
- `_message_after_copy`, `new-source.sh` and `/new-source`: human step 3 is the review and
  merge of the scaffold PR, since releases tag themselves; step 1 says the first
  release's publish job needs the pending publisher. `/new-source` names core 0.2.1 as the
  default and a full SHA for a pin.
- The `[tool.uv.sources]` comment of a pinned `pyproject.toml`: the pin's removal is a PR
  of its own, before the release PR.
- Template-internal: `scripts/prove.sh` renders from a git snapshot of the working tree
  tagged with the CHANGELOG's top release version, so the generated `.copier-answers.yml`
  names a tag as the family check requires, and `--keyless` proves a keyless flat source,
  `sdk-example`, the shape eurostat starts in. The template tests pin `gates.yml`,
  the template's own included, and the PR template to core's 0.2.1 bytes and `ci.yml` and
  `publish.yml` to core's bytes with the template's documented steps taken out; they
  render a keyless flat variant, check that the deleted test files are absent and the
  family test is its one line, refuse a `core_git_ref` that is neither `main` nor a full
  SHA, and require the generated `.copier-answers.yml` to be byte-identical to copier's
  write-back, as the merge-class check does.

### Removed

- `tests/test_layout.py` and `tests/test_adapters.py`: the family check makes their
  checks. `copier update` deletes both (checked with copier 9.19.1), a test a source
  added to one of them included, with no conflict marker: move such a test before the
  update (sdk-comtrade's and sdk-cashctrl's, below).
- From the `tests/test_tasks.py` scaffold: `test_package_has_a_version` and
  `test_task_is_a_sync_facade_with_an_agent_docstring`, which the family check replaces
  without requiring `async_fn` (conventions §6 makes the async variant optional). Its
  docstring points at `sent_query(route)` beside `sent_urls(route)`.
- From the `tests/test_tasks_write.py` scaffold, which write sources get:
  `test_the_write_server_serves_exactly_the_write_tasks`, which the family check's
  `test_family_write_server_serves_the_write_tasks` makes (conventions §8, core's
  `assert_write_tools`), and the `async_fn` assertion of the per-task test (conventions
  §6 makes the async variant optional). The per-task test,
  `test_write_task_takes_confirm_last_and_documents_it`, keeps what the family check
  leaves out: `confirm` last and explained under `Args:`.

### Hand-apply

- `tests/test_tasks.py` — delete `test_package_has_a_version`,
  `test_task_is_a_sync_facade_with_an_agent_docstring`, the `TASKS` list and the imports
  only they used — the family check in `tests/test_family.py` makes them (conventions §10).
- `tests/test_adapters.py` (sdk-comtrade, sdk-cashctrl) — before the update, move the
  tests of the source's own to `tests/test_tasks.py` or `tests/test_tasks_write.py`
  (sdk-comtrade's check that `mcp.py` and `http.py` name no task, if it keeps it;
  sdk-cashctrl's `test_the_organisation_list_is_on_the_read_server`,
  `test_write_tools_are_the_write_tasks_with_their_parameters` and
  `test_the_order_categories_are_on_the_read_server_and_the_router`) — the update deletes
  the file; the family check makes the rest.
- `tests/test_tasks_write.py` (sdk-cashctrl; source-owned, so the update leaves its copy
  as it is) — drop a write-server registration test, if the copy carries one, and the
  `async_fn` assertion of `test_every_write_task_is_a_sync_facade_with_confirm_last`
  unless a test of the source's own reads `async_fn`; keep `confirm` last and explained
  under `Args:` — the family check's `test_family_write_server_serves_the_write_tasks`
  makes the registration (conventions §8), and conventions §6 makes the async variant
  optional; the scaffold dropped both (Removed, above).
- The local test helpers core 0.2.1 provides (core's `docs/handover.md`, "Adopting
  core 0.2.1", names them per source) — `recorded()` in `tests/test_client.py`
  (sdk-usda-psd, sdk-usda-esr, sdk-usda-gats) and `tests/test_errors.py` (sdk-cashctrl) →
  `response_from_fixture(load_fixture(path))`; `_mount_recorded_404` in
  `tests/test_slices.py` (sdk-usda-psd, sdk-usda-esr) → `replay_fixture(..., url=...)`;
  the `retrieved_at` bracket in `tests/test_lists.py` (sdk-usda-psd, sdk-usda-esr,
  sdk-usda-gats) and `tests/test_tasks.py` (sdk-usda-gats) → `assert_time_between` with
  core's `CLOCK_SLACK`; the query of the last request (sdk-usda-nass `sent_query`,
  sdk-comtrade `_sent`, sdk-cashctrl inline) → `sent_query(route)`; the recorded query
  (sdk-comtrade `recorded_params` and `_recorded`, sdk-cashctrl `recorded_query`) →
  `recorded_query(fixture)` — conventions §15 items 3 and 4 (ADR-0023).

The update brings the rest with no hand edit: `-d core_version=0.2.1` renders
`xippios-core~=0.2.1` and its `mcp`, `http` and `testing` extras likewise; it deletes
`tests/test_layout.py` and `tests/test_adapters.py`, renders `tests/test_family.py`, drops
`anyio_backend` from `tests/conftest.py`, and brings `publish.yml` and `ci.yml` on the
release train with the two CI steps, `gates.yml` switched off until Johannes sets
`GATES_CALLER`, and the PR template. New repositories only, nothing to port: the comment
above the README's status table (an existing table the family check reads passes without
it), the `tests/test_tasks.py` scaffold's docstring and the `CHANGELOG.md` scaffold's
first entry.

**Updating from 0.2.0.** `/adopt-release v0.2.1` walks it; its step 3 runs
`uvx copier update --defaults --vcs-ref=v0.2.1 -d core_version=0.2.1 -d core_git_ref=`,
after the tests of the source's own leave `tests/test_adapters.py`. The adoption branch,
`chore/template-update-v0.2.1`, is exempt from the CHANGELOG step but still writes §15
item 9's line, and its family check needs core 0.2.1 installed. From the merge of the
adoption on, the source's next release PR tags itself through `publish.yml`. A repository
still on 0.1.5 (sdk-comtrade, until its v0.2.0 adoption) reads 0.2.0's paragraph as
well.

## [0.2.0] - 2026-10-25

Generated repositories depend on xippios-core 0.2.0 (conventions 1.13, ADRs to
ADR-0018) and use it instead of the workarounds earlier releases scaffolded; a source
adopts this release in one adoption PR (conventions §15), which `/adopt-release` walks.

### Added

- `/adopt-release` (`.claude/commands/adopt-release.md`) in every generated repository:
  it walks conventions §15's nine items in order for the source, from
  `.copier-answers.yml`'s `_commit` and `core_version` through this changelog's
  Hand-apply lists and "Updating from" paragraphs, the core release's ADRs and
  `docs/handover.md`, `copier update` with the new core minor and no pin, the deleted
  workarounds, the marked tests, the re-rendered enums, `mypy --strict` over `scripts/`,
  the conventions version and the CHANGELOG line, to one `chore/template-update-<tag>`
  PR whose body is the definition of done's Enforced-by-CI, Adoption PR and Process
  blocks, auto-merged after the reviewer's `ready` (ADR-0018). No step is a human's. It
  reads the template and core releases on GitHub, or from `../sdk-template` and
  `../sdk-core` when the family workspace is checked out beside the repository.
- Questions `rate_limit_burst` (default `1`) and `rate_limit_provenance` (`documented` or
  `self-imposed`, default `documented`). `_client.py` renders
  `RateLimit(per_minute=..., burst=...)` under a comment naming the provenance, and the
  generated CLAUDE.md's rate-limit row states pace, burst and provenance (ADR-0010
  decision 1).
- `_client.py`: a commented `QuotaPolicy` block after `config`, for an upstream that
  reports an hourly or daily quota: `policy = QuotaPolicy(window=..., limit_header=...,
  remaining_header=..., source=SOURCE)` and `config = policy.install(config)`, with which
  headers to name, the daily `window` and `classify`'s part; the generated CLAUDE.md
  points at it (ADR-0015, ADR-0010 decisions 3 and 4). A source without a quota adds
  nothing.
- Question `core_version` (default `0.2.0`, the current PyPI release): `pyproject.toml`
  depends on `xippios-core~=<core_version>`, the `mcp`, `http` and `testing` extras
  likewise, so a source depends on one core minor, normally from its `.0`, from the
  release that carries a pinned change once a core pin goes (conventions §12, ADR-0018,
  released with core 0.2.0).
- `xippios_placeholder_key_envs = ["<api_key_env>"]` under `[tool.pytest.ini_options]`
  for a keyed source: core's plugin sets the variable to its placeholder key in every
  test not marked `live` and pins `EnvKeyAuth.key` (ADR-0013). An open source sets none.
- Per-tool result caps: `mcp.py` passes `caps=getattr(tasks, "MCP_CAPS", None)` to
  `build_server`, `mcp_write.py` likewise from `tasks_write`, and `tasks.py` carries a
  commented `MCP_CAPS` scaffold whose `ResultCap` import is guarded, since
  `xippios.core.mcp` needs the `mcp` extra a base install lacks, and which gives a base
  install an annotated empty mapping (conventions §8, ADR-0016). It stays commented: a
  source without a cap of its own adds nothing, and its task layer never imports the
  MCP adapter.
- `scripts/refresh_reference.py`: `ID_LISTS` next to `LISTS`, for lists of integer ids
  and names. Their records are packaged under upstream's field names (a field's string
  `validation_alias`, else its name; the models set no serialisation alias, so
  `model_dump(by_alias=True)` would not restore them), as tables keep upstream's column
  names, and rendered through `id_name_pairs` and `render_int_enums`, one `IntEnum` per
  list, so a member equals the id in upstream's data (conventions §3, ADR-0008
  amendment). Each renderer writes a whole module, so the script refuses both mappings
  filled. `--render-only` regenerates `enums.py` from the packaged `reference/*.json`
  without a request or a key: `/adopt-release` runs it for conventions §15 item 6, so an
  adoption fetches nothing, and `/refresh-reference-data` names it.
- `.github/workflows/live.yml`, the one rendered workflow: every `live` test, write tests
  included (they act only on data kept for testing, ADR-0014), every night and on
  `workflow_dispatch`, one job, `contents: read` (conventions §10). The
  `uv run pytest -m live` step alone gets `XIPPIOS_LIVE_TESTS=1` and, for a keyed
  source, the org secret named by `api_key_env`; checkout, setup-uv and `uv sync` never
  see it. The start time derives from the slug: the hidden computed answer
  `live_schedule` in `copier.yml` folds it onto 01:00 to 05:59 UTC, so sources that
  share a key (ADR-0009) do not start together (usda-psd 01:25, usda-esr 05:40,
  usda-gats 02:57) and a repository keeps its time across updates; the generated
  CLAUDE.md names it ("nightly at HH:MM UTC").
- `tests/test_tasks_write.py` for write sources: core's `assert_write_tools` checks that
  the write server was built with `read_only=False`, that its tools are exactly the
  write tasks, each with `confirm: bool = False`, and that no write task is a tool of
  the read server or a route of the router; one parametrised test adds what it leaves
  out, that every write task is a sync facade whose last parameter is `confirm`,
  explained under `Args:` (conventions §8).
- `publish.yml` refuses to build a `pyproject.toml` that has `[tool.uv.sources]` (step
  "Refuse a pyproject with [tool.uv.sources]"), and `/release-prep` gains a step before
  the version bump that removes a core pin and raises `core_version` to the core release
  carrying the pinned change: `X.Y.Z` with `Z` the patch that shipped it, or `X.Y.0`
  when the minor itself did; still one minor (conventions §12). `copier.yml`'s help for
  `core_version` and `core_git_ref` and the `[tool.uv.sources]` comment say the same.
- This changelog, with a Hand-apply list per release.

### Changed

- `_skip_if_exists` is inverted for the client and the tests:
  `src/xippios/<pkg>/_client.py` and `src/xippios/<pkg>/__init__.py` are now the
  source's and never overwritten, and of `tests/` only `test_tasks.py`,
  `test_tasks_write.py`, `test_live.py` and `fixtures/` are, so `tests/conftest.py`,
  `tests/test_layout.py` and `tests/test_adapters.py` update with the template. The
  first update to this release merges those three files three ways once: a source's own
  lines in them, a fixture of its own in `conftest.py` say, conflict where they touch
  what the template changed, and the session keeps the template's side plus what the
  source added on purpose. The client's changes in this release reach existing
  repositories as Hand-apply bullets, not through the update.
- `tests/conftest.py` keeps `pytest_plugins` and `anyio_backend` only, the same for keyed
  and open sources: the placeholder key is core's plugin's (ADR-0013), the key variable
  named in `pyproject.toml`.
- `.github/workflows/ci.yml` is core 0.2.0's, byte for byte: after the tests it caches
  `~/.cache/pre-commit` and runs `uv run pre-commit run --all-files`, so the definition
  of done's Enforced-by-CI block holds (ADR-0018). The pull request template is core
  0.2.0's file, unchanged. The template tests pin both to core's v0.2.0 bytes.
- `rate_limit_per_minute` is the pace, documented or self-imposed, no longer "the
  documented limit", in `copier.yml`, the README and the generated docs (ADR-0010). A
  new repository's `_client.py` renders `burst=1` unless upstream documents a burst;
  an existing one ports it by hand (Hand-apply). On core 0.2.0 the test plugin skips the
  limiter's waits in offline tests, so a burst of 1 costs the replays nothing.
- The core bound: `xippios-core~=<core_version>` replaces the hard-coded `>=0.1.0`. With
  `core_git_ref` set the bound stays `~=`: uv takes core from the git pin and does not
  check the bound against it. The `[tool.uv.sources]` comment says how to unpin
  (`uvx copier update --defaults --vcs-ref=:current: -d core_git_ref= -d core_version=X.Y.Z`),
  and its `rev` line carries `# pragma: allowlist secret`, so a 40-character commit SHA
  no longer trips detect-secrets. Template-internal: the template tests render a
  40-character pin and run the generated repository's detect-secrets hook on it, so
  `detect-secrets` joins the template's dev group.
- `_client.py` renders `__all__` one sorted name per line with a trailing comma, so a
  source's extra export is a one-line change.
- mypy checks `scripts/` too (`files = ["src", "tests", "scripts"]`).
- The sdist ships no tests: `tests` leaves `[tool.hatch.build.targets.sdist] include`,
  and the `tests/fixtures` exclude goes with it. A small, consistent sdist; the tests
  live in the repository. The patterns are anchored (`/src`, `/README.md`, ...): hatch
  reads them gitignore-style, so a bare `README.md` also matched
  `tests/fixtures/README.md`.
- `http.py`'s docstring: `GET` for a task whose parameters are all scalars, `POST`
  otherwise (ADR-0007), as `tests/test_adapters.py` asserts.
- `docs/upstream/FETCHED.md` and `/refresh-upstream` (conventions §3 at 1.13, ADR-0003
  amendment): `Fetched` is the UTC time of the run in ISO 8601 with an explicit `Z`, an
  Attribution section holds the copyright line as the documentation states it, and a
  Note column says where a table with merged or nested cells is kept as HTML.
  `scripts/refresh_upstream.py` may change in the snapshot PR, and what it writes is
  checked against the same rules.
- `/refresh-reference-data`: a source need not package lists, a multi-tenant source
  packages no tenant data (ADR-0014), the refresh script runs with whatever the list
  endpoints need rather than a key as a given; it shows the two renderer paths, value
  lists through `render_str_enums` (with `member_names=` for a label that derives no
  identifier) and integer ids through `id_name_pairs` and `render_int_enums`; agents get
  one lookup task per list or the upstream's own lookup operation when it serves every
  list through one, with a cap of its own in `MCP_CAPS` where an agent needs the whole
  list (ADR-0016).
- The shipped `enums.py` starts as core 0.2.0's renderer starts it, "(conventions,
  section 3)", so the first refresh changes nothing but the lists.
- `/record-fixture`, `/add-endpoint` and the `models.py` docstring name no source
  (ADR-0008: nothing source-specific is scaffolded). The `models.py` docstring, the
  generated CLAUDE.md, `/add-endpoint` and `/record-fixture` carry ADR-0017: documented
  personal identifiers stay out of task projections and `meta.request`, and fixtures
  never carry their values, which `/record-fixture` scrubs with `Scrub` and greps for.
  `/add-endpoint` points a test that checks what was sent at `sent_urls(route)`, and
  names `IntEnum` for an enumeration of integer ids.
- Human step 2 (`_message_after_copy`, `scripts/new-source.sh`, `/new-source`): for a key
  several sources share (ADR-0009), add the repository to the existing org secret's
  repository access; never `gh secret set --repos`, which replaces the list.
- The generated CLAUDE.md names the provider level among the `__init__.py` files never
  to add, describes `live.yml` (its time, the one step that sees the key, the write
  tests it runs) and the write test, and points at this changelog's Hand-apply lists for
  template updates. It names conventions §15 and `/adopt-release` in Read first and the
  command list, the plugin's offline run with the markers `rate_limited` and `network`,
  `MCP_CAPS`, and template updates as one adoption PR in which `copier update`
  re-renders `conftest.py`, `test_layout.py` and `test_adapters.py` but never
  `_client.py`, `__init__.py` or the other files the package fills. It and
  `/adopt-release` name every one of those, `params.py`, `enums.py` and the write files
  included, in one list in `_skip_if_exists`'s order, which now follows the package
  layout.
- `/release-prep` and the generated Never list state ADR-0018's one exception: a session
  enables auto-merge on a `chore/template-update*` or `chore/release-*` PR after the
  reviewer's `ready`; the tag stays a human's. `/release-prep` and `/adopt-release` run
  it from the family workspace root as
  `gh pr merge --auto --squash -R xippios/sdk-<slug> <number>`, since the generated
  `.claude/settings.json`, core's copy, denies `gh pr merge` in the repository and `gh`
  cannot infer the repository at the root.
- The `CHANGELOG.md` scaffold names the write server for a write source; the README
  scaffold's cap sentence allows a tool's own cap.
- `/new-source` names core 0.2.0 as the default and the adoption PRs that bring later
  core minors and template releases.
- Template-internal: `scripts/prove.sh` runs `scripts/refresh_reference.py --render-only`
  on the generated repository and requires the shipped `enums.py` unchanged.

### Removed

- `placeholder_api_key` and `PLACEHOLDER_KEY` in `tests/conftest.py`, with the import of
  `API_KEY_ENV` and `auth` that served only them: core's plugin pins the key on
  `EnvKeyAuth` for every auth object (ADR-0013).
- `test_replay_tests_send_the_placeholder_key` in `tests/test_tasks.py`, with
  `AuthReport`, `send_through_auth`, `SHELL_KEY` and the imports of `os`, `httpx`,
  `base64` and `NamedTuple`: core's plugin and its own tests guarantee the placeholder
  (conventions §10).
- The step of `/refresh-reference-data` that formatted `enums.py` after a refresh: core
  0.2.0's renderers write it ruff-clean (sdk-core#20, ADR-0008 amendment).
- Template-internal: `scripts/prove.sh` no longer reruns the generated suite with the key
  variable set to a dummy value; the placeholder is core's to guarantee, and the
  template tests assert the ini option that names the variable.

### Fixed

- `_skip_if_exists` names the package directory in the patterns inside the package,
  `src/xippios/{{ package_dir }}/...`, which copier renders: `src/xippios/**/api/**`
  also matched the whole package of a slug ending in `-api` (`xippios/example/api/`), so
  `copier update` never re-rendered any file of that package, `mcp.py` and `http.py`
  among them. No family source has such a slug; the template tests render one.
- `scripts/refresh_reference.py` passes `mypy --strict`: `LISTS` holds coroutine
  functions, which is what `xippios.core.sync` takes.
- `tests/test_layout.py` stops at the `xippios` directory and fails with a message when
  there is none, instead of looping for ever.
- `tests/test_live.py`: the reachability check sends no key, so it spends no quota call
  on a keyed gateway; a keyless source's docstring mentions no quota.
- `.secrets.baseline`, generated and the template's own, drops the `is_swagger_file`
  filter, which exempted every path containing "swagger" (verbatim upstream Swagger
  snapshots among them) from the scan; sdk-core dropped it too.

### Hand-apply

`_client.py` and `__init__.py` are under `_skip_if_exists` from this release on, so this
release's `_client.py` changes are ported by hand by every repository updating from
0.1.5; `__init__.py` is unchanged. `tests/conftest.py`, `tests/test_layout.py` and
`tests/test_adapters.py` left the list: the update carries their changes, merged three
ways once (see Changed), and they need no bullet.

- `src/xippios/<pkg>/_client.py` — `RATE_LIMIT = RateLimit(per_minute=<pace>, burst=<burst>)`
  matching the `rate_limit_*` answers (it had `burst = per_minute`), under the comment
  that names the provenance ("Paced within the limit upstream documents" or "A
  self-imposed pace: upstream documents no limit", ADR-0010 decision 1), and `__all__`
  one sorted name per line with a trailing comma — ADR-0010 decision 1, and
  `copier update` no longer renders the file once it exists.
- `src/xippios/<pkg>/tasks.py` — add `MCP_CAPS` only if a tool needs a cap of its own,
  next to `__all__`, its `ResultCap` import guarded and a base install given
  `MCP_CAPS: "Mapping[str, ResultCap]" = {}`, as the scaffold's comment shows; the
  adapter reads it with `getattr`, so a source without one adds nothing — ADR-0016.
- `src/xippios/<pkg>/models.py` — the module docstring says the read models stay
  faithful while projections, `meta.request` echoes and fixtures leave documented
  personal identifiers out (ADR-0017), and names `IntEnum` for integer ids — guidance
  only; port it if the file still carries the scaffold docstring.
- `src/xippios/<pkg>/reference/README.md` — the lookup rule reads "one lookup task per
  list, `list_<thing>`, ..., or the upstream's own lookup operation when it serves every
  list through one", a rule says a multi-tenant source packages no tenant data, the
  enums rule names both renderers, `render_str_enums` and `render_int_enums`, and a rule
  says files keep upstream's names (a table its columns, an id list its record fields) —
  the per-list rule did not fit a source whose upstream serves every list through one
  operation (ADR-0014 for the tenant rule, ADR-0008 amendment for the renderers).
- `scripts/refresh_reference.py` — `LISTS` is typed
  `dict[str, Callable[[], Coroutine[Any, Any, list[str]]]]` (imports `Coroutine` and
  `Any` instead of `Awaitable`), the docstring asks for whatever the list endpoints
  need, not the API key, and says a multi-tenant source packages no tenant data; the
  flag `--render-only` regenerates `enums.py` from the packaged `reference/*.json`
  without a request (`read`, `render` and `render_only` next to `refresh`, `main`
  parsing the flag); where the source packages integer-id lists, the `ID_LISTS` path
  (`id_name_pairs`, `render_int_enums`, the records under upstream's field names through
  `upstream_record`) replaces a renderer of its own — the updated `pyproject.toml` has
  mypy check `scripts/`, where the old annotation fails `--strict` twice at
  `values = sync(fetch)()`, and §15 item 6 re-renders `enums.py` with `--render-only`,
  fetching nothing; port it in the update PR itself, before that re-render, together
  with any other script there that `mypy --strict` now reports (ADR-0008 amendment for
  the renderer).
- `tests/test_tasks.py` (keyed sources) — delete `test_replay_tests_send_the_placeholder_key`,
  `AuthReport`, `send_through_auth`, `SHELL_KEY` and the imports only they used — core's
  plugin pins the key and its own tests prove it (ADR-0013); a module that tests key
  resolution defines a `placeholder_api_key` fixture that pins nothing instead.
- `tests/test_tasks_write.py` (write sources) — new: `assert_write_tools(write_server,
  WRITE_TASKS.values(), source=SOURCE, read_server=server, router=router)` and a test
  that every write task is a sync facade taking `confirm` last, explained under `Args:`
  — conventions §8 had no generated test. `copier update` creates the file where there
  is none; a source with a `tests/test_tasks_write.py` of its own (sdk-cashctrl, which
  checks this with core's `assert_write_tools` in `tests/test_adapters.py`) keeps its
  file and adds only the checks it lacks.
- `tests/test_live.py` — `test_upstream_answers` sends a plain `httpx.AsyncClient` GET to
  `BASE_URL` (the family User-Agent and the client's timeouts, redirects followed) and
  asserts `status_code < 500` — through the package's client it sent the key to `/`,
  which a keyed gateway answers with 404 while counting a quota call.
- `docs/upstream/FETCHED.md` — `Fetched` as the UTC time of the run with `Z`
  (`2026-10-24T09:15:00Z`), an Attribution section with the copyright line, a Note
  column for tables kept as HTML — conventions §3 at 1.13 (ADR-0003 amendment); the next
  `/refresh-upstream`, or the source's `scripts/refresh_upstream.py`, writes it so.

New repositories only, nothing to port: the commented `QuotaPolicy` block in
`_client.py` (a source with a quota installs its policy as core's `docs/handover.md`
says), the `CHANGELOG.md` scaffold's write-server clause, the source-neutral example in
the `models.py` docstring, the cap sentence of the `README.md` scaffold, the docstring
of `tests/test_tasks.py` that points at `sent_urls`, and the first line of the shipped
`enums.py`, which §15 item 6's re-render brings to an existing repository.

**Updating from 0.1.5.** The update brings `/adopt-release` itself, so run its step 3 by
hand, `uvx copier update --defaults --vcs-ref=v0.2.0 -d core_version=0.2.0 -d core_git_ref=`,
adding `-d rate_limit_provenance=self-imposed` where upstream documents no limit
(usda-nass, usda-psd) and `-d rate_limit_burst=N` where the source deliberately bursts;
then the command takes over from step 4. 0.1.5 recorded neither answer, and the
generated CLAUDE.md's rate-limit row renders from them ("within the limit documented by
upstream" and burst 1 otherwise); `_client.py` is no longer rendered, so port its bullet
above to match the same answers. The first update merges `tests/conftest.py`,
`tests/test_layout.py` and `tests/test_adapters.py` three ways: the template's side drops
the placeholder fixture, and a source's own lines there either stay (sdk-cashctrl's
demo-only handling and the write-server checks in its `test_adapters.py`) or are
workarounds this adoption deletes anyway (sdk-comtrade's `replay_query`, sdk-usda-psd's
`fresh_quota`, as core's `docs/handover.md` lists). `pyproject.toml` gains
`xippios_placeholder_key_envs` naming `api_key_env`; sdk-cashctrl keeps its
`["CASHCTRL_DEMO_API_KEY"]` in the merge. `scripts/` is now under `mypy --strict`, so
every script in the repository must pass, not only `refresh_reference.py`. A
multi-tenant source (sdk-cashctrl) reads neither `<api_key_env>` nor that org secret:
its live tests need the reserved test tenant's variables (ADR-0014), so it replaces the
rendered variable on the pytest step of `live.yml` with the test tenant's variables by
hand; the template renders no tenant variables.

## [0.1.5] - 2026-10-23

### Added

- `.gitattributes` with `docs/upstream/** -text`: the upstream snapshot stays byte for
  byte (CRLF, mixed endings).
- `tests/test_tasks.py` in keyed sources: `test_replay_tests_send_the_placeholder_key`
  checks the request the client's auth sends outside a live test.
- Template-internal: `scripts/prove.sh` runs the generated suite once more with the key
  variable set to a dummy value, so the placeholder path is proven on every template
  change.

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
  — proves on the outgoing request that the pin holds; superseded by 0.2.0, whose form
  is no test at all: core's plugin owns the pin, so the test is deleted.
- `src/xippios/<pkg>/models.py` — the module docstring recommends
  `Field(validation_alias=...)` and warns against `alias=` — guidance only; port it if the
  file still carries the scaffold docstring.
- `src/xippios/<pkg>/reference/README.md` — each packaged list gets a `list_<thing>`
  lookup task, added by `/refresh-reference-data` where missing — port the 0.2.0
  wording, which supersedes it.
