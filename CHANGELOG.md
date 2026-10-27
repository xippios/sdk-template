# Changelog

All notable changes to sdk-template are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the template uses
[Semantic Versioning](https://semver.org/). A generated repository records the tag it
was made from in `.copier-answers.yml`.

Every release ends with a **Hand-apply** list. `copier update` carries a template change
into the files it renders, but never touches a file under `_skip_if_exists` in
`copier.yml` once that file exists (the package `__init__.py`, the client, models,
endpoint wrappers, the task layer, the packaged lists and enums, reference data,
scripts, the task and live tests and the fixtures, upstream snapshot, README, CHANGELOG
and, from 0.3.0, the package's errors and CLAUDE.md). Each change to such a file is one
bullet, `` - `<path>` — <what> — <why> ``; port it by hand in the same
`chore/template-update` PR. A new file under those patterns is created by the update
where the repository has no file of that name. The list starts with 0.1.5; earlier tags
are not listed.

## [Unreleased]

### Added

- `.claude/family.md`, template-owned: the family rules every source shares, moved out of
  the generated `CLAUDE.md`: what to read first, with the family documents' GitHub URLs;
  the three layers; the namespace packages; how to add an endpoint and record a fixture;
  the family commands; the workflow rules, with the files a source fills (`CLAUDE.md` now
  among them) and the release subset; the Never list; what to do when something is
  unclear. It holds no Jinja, so it renders the same in every source, and `copier update`
  carries every later change to it. The generated `CLAUDE.md` imports it with the line
  `@.claude/family.md`: Claude Code resolves an import relative to the importing file, in
  a worktree too, and never reads one inside backticks or a code block.
- `src/xippios/<package>/errors.py`, under `_skip_if_exists`: the package's own error
  classes, empty (`__all__: list[str] = []`), its docstring pointing at conventions §5
  and a commented `InvalidRequestError` subclass showing the pattern. `_client.py` gains
  `classify(response) -> XippiosError | None`, which returns `None`: the
  `ClientConfig.classify` hook of conventions §6, wired into `config` as
  `classify=classify` and exported, where a source maps its documented error shapes.
  `.claude/family.md`, `/adopt-release`, the generated `CLAUDE.md`'s Layout and this
  repository's documents name `errors.py` with the files a source fills.

### Changed

- The generated `CLAUDE.md` holds the facts of the package only: the title and intro, the
  import line right after the intro, the "What this package wraps" table with one line
  pointing at `docs/upstream/FETCHED.md`, the Layout as the starting text a source
  rewrites (the package's paths and namespace levels), the commands that depend on the
  answers (the live run with the key's variable, the MCP entry point, the placeholder key
  of a keyed source, the nightly start time and the secret the live workflow reads, or
  that it needs none) and an empty "`<source name>` specifics" section whose comment says
  what goes there; a source fills it or deletes it. `CLAUDE.md` joins `_skip_if_exists`:
  once rendered, it is the source's, and `copier update` leaves it as it is.
- The family documents are named by their GitHub URLs (sdk-core's conventions, ADRs,
  definition of done and review checklist) instead of `../sdk-core/docs/...` and
  `../CLAUDE.md`, which resolve neither from a worktree under `.worktrees/` nor on GitHub
  (sdk-usda-esr's scaffold review); the workspace's own `CLAUDE.md` is named without a
  path, since Claude Code loads it when a session works from the workspace.
- `/adopt-release` lists `CLAUDE.md` among the files a source fills and
  `.claude/family.md` among the template's, where a line of the source's own moves to
  `CLAUDE.md`; `/adopt-release` and `/release-prep` call the workspace root the directory
  that holds the workspace's own `CLAUDE.md`, no longer "the family `CLAUDE.md`".
- Template-internal: the tests read each text in the file that now holds it and check
  that `CLAUDE.md` renders the import line on its own line right after the intro, that
  `.claude/family.md` is the template file byte for byte in every variant, keyed and
  keyless, flat and nested, with no `../` path in either file, and that `CLAUDE.md` is
  skip-listed while `.claude/family.md` is rendered again.
- The scaffolds a source fills keep one pointer each instead of guidance: the docstrings
  of `__init__.py`, `_client.py`, `models.py`, `params.py`, `tasks.py`,
  `api/__init__.py`, `tests/test_tasks.py` and `tests/test_live.py` give the file's
  purpose in one sentence and the convention or command that explains it (conventions
  §2, §3, §6, §10, `/add-endpoint`, `/record-fixture`, `/refresh-reference-data`), and
  `reference/README.md` keeps one paragraph above its provenance table. The `QuotaPolicy`
  and `MCP_CAPS` comments point at conventions §6 and §8, and `MCP_CAPS` imports
  `ResultCap` from `xippios.core`, which exports it from core 0.3.0. The source's name
  leaves the summary lines (`__init__.py` names it on a line of its own below), where a
  long name broke ruff's line length in four files (sdk-usda-esmis's render).
- The six commands name the definition of done and the review checklist on sdk-core
  `main` by URL instead of repeating the PR-body rules, and their last step says the
  body is as the definition of done says; their examples name no source
  (`get_example by_year year=2024`). `/adopt-release` names the gates repository by its
  new name, `xippios/sdk-gates`, for the merge classes, and reads a local clone as
  `<workspace root>/sdk-template` or `<workspace root>/sdk-core`, since `../` resolves
  from no worktree (sdk-template's own review).
- `/add-endpoint`: a wrapper module per upstream operation, or per service where
  operation ids repeat across services, as the Layout says (sdk-eurostat); an
  enumeration written by hand for a documented value set lives in `models.py`,
  unexported, since `enums.py` is generated whole (sdk-usda-esr, sdk-eurostat); a test
  that checks what was sent compares `sent_query(route)` or `sent_urls(route)`, here and
  in `.claude/family.md`; a wrapper calls `get_json`, `get_answer` where the answer may
  come from the cache, or `get` then `decode_json`, maps error shapes in `classify` and
  keeps its own error classes in `errors.py`; core's `UnknownCode` refuses a code the
  packaged list lacks; a test reads a packaged list's fetch date and counts from the
  packaged file instead of pinning them (sdk-usda-nass). The write-task clause on
  `meta.request` goes, here and in `.claude/family.md`: the template renders read-only
  packages.
- `/record-fixture`: a source with a quota records through a client on
  `RetryPolicy(max_attempts=1)`, since core's `record` takes no `retry=`, so a 5xx
  spends no quota (sdk-usda-esr); a match of the key grep in upstream's own text is read
  by eye (sdk-usda-gats); values the scrub cannot name are rewritten in the source's own
  recorder step (ADR-0024); the fixture file stays under 256 KiB, a JSON array or a
  text body recorded with `max_bytes=`, a small real answer or sample for what the
  recorder will not cut (a JSON object, XML, ZIP, gzip, XLS, XLSX) (ADR-0019).
- `/refresh-upstream`: the snapshot is staged before `pre-commit run --all-files`,
  which scans only the files in git's index, and a capture script checks the
  attribution on every run (sdk-usda-gats).
- `/refresh-reference-data`: the refresh script's docstring gives the list shapes; the
  provenance table names the `docs/upstream/` file a table was rebuilt from
  (sdk-usda-nass); a step updates the counts and dates pinned in list-task docstrings
  and tests (sdk-usda-psd). `/adopt-release`: a refresh script of the source's own
  shape gains `--render-only` and passes `mypy --strict` without taking the template's
  shape (sdk-usda-nass); the re-rendered enums are committed as the script writes them.
- The generated `CLAUDE.md`: a self-imposed pace says upstream documents no per-second
  or per-minute limit, and the rate-limit row carries a comment to name a documented
  hourly or daily quota with its `QuotaPolicy` (sdk-usda-esr); the scaffold's
  `_client.py` comment and this README's question row say the same. The Layout names the
  key only for a keyed source (sdk-eurostat, sdk-usda-esmis), the packaged lists
  without a constant's name (sdk-usda-nass), `errors.py`, the optional
  `scripts/refresh_upstream.py` (sdk-usda-esmis, sdk-usda-gats) and the optional
  `tests/test_api.py` for the wrappers' own tests (sdk-usda-esmis); the start time's
  reason, sources sharing a key, is a keyed source's only (sdk-eurostat).
- `.claude/family.md`: `api/` by operation or by service, the Layout saying which
  (sdk-eurostat); the home of a hand-written enumeration (sdk-usda-esr, sdk-eurostat);
  a release PR changes no file outside the release subset, and its `CHANGELOG.md`
  section may gain a lead paragraph and says internal labels in plain words, since it
  becomes the tag's message (the template's v0.2.1 and v0.2.2 release reviews).
- The `README.md` scaffold: the MCP snippet of a keyless source closes the server on a
  line of its own (sdk-eurostat), and the terms sentence holds where upstream states no
  terms of use (sdk-usda-esmis). `docs/upstream/FETCHED.md`'s attribution placeholder
  speaks of the publisher's objection, a vendor's or a public body's, and of the capture
  script's check (sdk-usda-gats).
- `live.yml` names the secret and the shared key as the start time's reason, and
  `tests/conftest.py` points at `xippios_placeholder_key_envs`, only for a keyed source
  (sdk-eurostat); the reachability probe of `tests/test_live.py` "spends no keyed call",
  with or without a quota (sdk-usda-nass); the read server's instructions ask list tools
  for valid values rather than codes, since a list tool may list releases or agencies
  (sdk-usda-esmis); `pyproject.toml` sets `junit_family = "xunit1"`, so
  `record_property` raises no warning under `--junitxml` (sdk-usda-gats).
- Two blank lines a line-final Jinja tag took with it are back: in the generated
  `CLAUDE.md`'s Commands block and between `/record-fixture`'s steps 1 and 2.
- This repository's `CLAUDE.md` names sdk-core's documents by GitHub URL, and it and the
  README say a release PR changes no file outside conventions §12's release subset,
  its section perhaps with a lead and in plain words (the v0.2.2 release review).
- Template-internal: the tests check that both new scaffolds render in every variant,
  that the README's MCP snippet parses as JSON with the key's `env` only for a keyed
  source, that every command names the definition of done and the review checklist by
  URL and no `../` path, that the key, the shared-key reason and the conftest's ini
  pointer appear only for a keyed source, and that no fixtures directory is generated;
  the `long-name` variant carries sdk-usda-esmis's 64-character name, and its four
  formerly failing files pass `ruff check`.
- The answers in `copier.yml`. Every rendered file reads `import_path`, and its hidden
  alias `source_pkg` goes. The domain's GitHub topic is no answer any more but
  `new-source.sh`'s `--topic DOMAIN`, checked before anything is generated (required
  unless `--local-only`) and added with `gh repo edit --add-topic`; the generated
  `pyproject.toml`'s keywords no longer name it. `core_version`'s help names the bound,
  `xippios-core~=X.Y.Z` with `Z` 0 unless patch `Z` shipped what the source adopts
  (ADR-0018 amendment (c)), and `core_git_ref`'s says what the pin is and that a release
  carries none, neither telling what to answer for the other. `source_name` takes at
  most 77 characters, the bound that keeps the generated `http.py`'s first line, the
  longest that names it, within ruff's 100 columns (sdk-usda-esmis's render). The
  `rate_limit_provenance` choice and the pace's help say "no per-second or per-minute
  limit", as the generated `CLAUDE.md`'s row does (sdk-usda-esr). The README's question
  table follows.
- `new-source.sh` opens the scaffold PR with its body filled from the generated PR
  template instead of the bare template: the summary with the human steps; under
  Assumptions the answers as `.copier-answers.yml` records them, the topic and the
  evidence for the answers (`--evidence FILE`: the pages and the status-only probes they
  rest on); the "Enforced by CI" block ticked, since its checks passed; the Adoption PR
  block deleted. It writes the body before anything is created on GitHub, and
  `--local-only` prints it; `/new-source` passes the evidence and completes the body
  with `gh pr edit` (sdk-usda-esr's scaffold review). The human steps it prints are the
  one copy, the sessions' team in plain words: where the team does not exist yet, a
  step says to give it write access once it does.
- The generated `pyproject.toml`'s dev group pins `ruff==0.17.1`, the rev of the
  `ruff-pre-commit` hook, so a new lock no longer resolves a newer ruff than the hook
  runs (sdk-usda-esr's scaffold review).
- `live.yml`, the one job the org secret reaches in a keyed source, pins
  `actions/checkout` and `astral-sh/setup-uv` to the commits `ci.yml` pins, the version
  in a comment, and its checkout persists no credentials (conventions §13; sdk-eurostat's
  scaffold review).
- `ci.yml`'s CHANGELOG step exempts a release and Dependabot only: an adoption PR adds
  its line naming the core, template and conventions versions adopted (conventions §15
  item 9), as `.claude/family.md` and this README now say (sdk-eurostat's scaffold
  review).
- Every live run takes `--tb=short`: `live.yml`'s pytest step, the live command of the
  generated `CLAUDE.md` and `.claude/family.md`, and `/release-prep`'s step 8; and
  `.claude/family.md` says that pytest's assertion introspection still prints what an
  `assert` compares, so a live test asserts on shapes and counts, never on a raw
  payload. A failing parse printed its raw upstream payload in a traceback, which the
  nightly run writes into a public log (sdk-cashctrl; core 0.3.0 raises its validation
  errors without the payload).
- Template-internal: the tests render the variants without `domain_topic` and check
  that no answers file records `source_pkg`, `domain_topic` or `needs_write_tools`, that
  `new-source.sh` refuses a missing or malformed `--topic` and a missing evidence file
  before it generates, that the two core answers' help texts keep apart, that
  `source_name`'s bound follows from the template's longest Python line, that the dev
  group's ruff is the hook's, that `live.yml` takes `ci.yml`'s pins with
  `persist-credentials: false`, that no live command lacks `--tb=short`, and that the
  CHANGELOG step no longer exempts an adoption; `scripts/prove.sh` passes a topic and an
  evidence file, so the proof prints the PR body a real run opens.

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
- Template-internal: the template tests drop the `basic` case and every write
  assertion; the variants that carried the write side or `basic` stay under new names
  with their other answers (`header-key`, `long-name`, and `bearer-git-core`, a
  git-pinned core now with a bearer key). They check that copier refuses
  `api_key_location=basic` and that the generated `CLAUDE.md` calls the package
  read-only.
- `tests/fixtures/README.md`: the fixture rule lives in `/record-fixture` and
  conventions §10, and its grep differed from `/record-fixture`'s (sdk-usda-gats).
- The `domain_topic` question, now `new-source.sh`'s `--topic`, since the topic is set
  once on GitHub; `source_pkg`, the hidden alias of `import_path`; and
  `_message_after_copy`, which repeated the human steps `new-source.sh` prints.

### Hand-apply

- `CLAUDE.md` (every source, once, in its 0.3.0 adoption) — split it: the facts stay, the
  family rules go, and the line `@.claude/family.md` imports them — the family rules
  were repeated in every source's `CLAUDE.md`, and with the file skip-listed a family
  change would reach no source once the file became its own; now one template-owned file
  carries them and `copier update` keeps it current. `CLAUDE.md` joins `_skip_if_exists`
  with this release, so the update renders `.claude/family.md` and leaves the existing
  `CLAUDE.md` byte for byte as it is (checked with copier 9.19.1 on all eight sources'
  real tags, v0.1.5, v0.2.0 and v0.2.2, with their answers and files, and on v0.2.2
  renders: keyed and nested, keyless and flat, one with lines of its own inside the
  family sections and a section of its own, one with write tools; no conflict marker, no
  reject); until the hand edit the old family text stays in `CLAUDE.md` and
  `.claude/family.md` is not read. The recipe, conventions §15 item 2's conflicts
  resolved by hand:
  1. Run the update: it adds `.claude/family.md` and leaves `CLAUDE.md` untouched.
  2. Rewrite `CLAUDE.md`: keep the title, the intro line, the facts table, the Layout
     block as the source wrote it, which gains the line
     `.claude/family.md  the family rules, the template's, imported above`, the
     Commands lines that depend on the answers (the live run with the key's variable,
     the MCP entry point, the placeholder key sentence, the nightly start time and its
     secret) and every section of the source's own; add `@.claude/family.md` on a line
     of its own, outside backticks, as the first line after the intro; delete by
     heading the family sections `.claude/family.md` now holds, once step 3 has moved
     the source's own lines out of them: "Read first, in this order", "The one rule:
     three layers", "How to add an endpoint", "How to record a fixture", the family
     lines of "Commands", "Workflow rules", "Never" and "When something is unclear",
     with the Layout's "Never add one" sentence and the snapshot paragraph's sentences
     after its first. The scaffold, `template/CLAUDE.md.jinja` at this tag, shows the
     shape.
  3. Move the source's own lines that sit inside those family sections into a
     "`<source name>` specifics" section or the Layout:
     - sdk-usda-psd: add-endpoint step 6 on its test modules (`test_lists.py`,
       `test_slices.py`) and its `QuotaPolicy` sentence (`_client.py` installs the
       policy).
     - sdk-usda-esr: its `QuotaPolicy` sentence and the keyed-call count of its live run
       in Commands; its gateway paragraph sits in "What this package wraps", which
       stays, and may move to its specifics section.
     - sdk-comtrade: the keyed-call count of its live run in Commands; its family
       sections carry v0.1.5's wording, which `.claude/family.md` replaces whole.
     - sdk-cashctrl, which stays on its last template tag and applies this only if it
       ever updates: add-endpoint steps 2 to 4 and 6, its pagination, lookups and
       `classify` paragraphs, the whole record-fixture body, its Commands lines
       (`direnv exec`, `--org demo`, the write server, the demo organisation's secrets,
       `--tb=short`) and its extended Never bullets; its own sections stay where they
       are.
     - sdk-usda-nass, sdk-usda-gats, sdk-eurostat and sdk-usda-esmis: nothing to move;
       their family sections are the template's as rendered.
  4. The result stays under 40,000 characters (`wc -m CLAUDE.md`), where Claude Code
     cuts a file that loads on demand; `.claude/family.md` counts on its own.
  5. Nothing else moves: the facts and the source's own sections keep their wording.
- `src/xippios/<package>/errors.py` — new: the update creates it where the repository
  has none, and leaves an `errors.py` of the source's own byte for byte (checked with
  copier 9.19.1); nothing to port — the place for the package's own error classes
  (conventions §5).
- `src/xippios/<package>/_client.py` — add `classify(response: httpx.Response) ->
  XippiosError | None` returning `None` (`import httpx`, `XippiosError` from
  `xippios.core`), pass `classify=classify` to `ClientConfig` and export `"classify"`,
  unless the source has a `classify` of its own; where the file still carries the
  scaffold's text, its docstring becomes one sentence that mentions no cache, the
  `QuotaPolicy` comment points at conventions §6 and ADR-0015, and a self-imposed pace's
  comment says upstream documents no per-second or per-minute limit — the hook is where
  a source maps its documented error shapes (conventions §6), and the docstring named a
  cache no config sets (sdk-eurostat, sdk-usda-esmis).
- `src/xippios/<package>/__init__.py` — the docstring's summary line names no source,
  the name on a line of its own below it — a long name broke ruff's line length
  (sdk-usda-esmis); port it if the file still carries the scaffold docstring.
- `src/xippios/<package>/models.py` — the docstring is its purpose and a pointer to
  conventions §3 and `/add-endpoint` — guidance only, and a long name broke the summary
  line; port it if the file still carries the scaffold docstring.
- `src/xippios/<package>/params.py` — the docstring is its purpose and a pointer to
  conventions §3 and `/refresh-reference-data` — as for `models.py`.
- `src/xippios/<package>/tasks.py` — the docstring is its purpose and a pointer to
  conventions §2 and `/add-endpoint`; the `MCP_CAPS` comment imports `ResultCap` from
  `xippios.core` without a guard — core 0.3.0 exports it from `xippios.core`, so the
  `mcp` extra is no longer needed for it; an `MCP_CAPS` of the source's own may keep its
  guarded import.
- `src/xippios/<package>/api/__init__.py` — the docstring is its purpose and a pointer
  to conventions §2 and `/add-endpoint` — guidance only; port it if the file still
  carries the scaffold docstring.
- `tests/test_tasks.py` — the docstring is its purpose and a pointer to conventions §10,
  `/add-endpoint` and `/record-fixture`; the `sent_query` and `sent_urls` advice it
  carried is `/add-endpoint`'s step 6 — guidance only; port it if the file still carries
  the scaffold docstring.
- `tests/test_live.py` — the module docstring is its purpose and a pointer; a keyed
  source's reachability probe says it "spends no keyed call" instead of naming the
  key's quota — a keyed source need not have a quota (sdk-usda-nass); port it if the
  file still carries the scaffold's text.
- `src/xippios/<package>/reference/README.md` — the rules list goes (conventions §3 and
  `/refresh-reference-data` hold the rules), and the paragraph above the table says
  that Origin names the endpoint or URL a file was fetched from, or the `docs/upstream/`
  file it was rebuilt from, and Fetched that fetch's UTC time, or the snapshot's
  `Fetched` time — the table could not tell a file rebuilt from the snapshot from one
  fetched (sdk-usda-nass); port the provenance sentence and correct a rebuilt file's
  row.
- `tests/fixtures/README.md` — the update deletes it: copier 9.19.1 deletes a
  skip-listed file the template stops rendering, a line of the source's own included,
  with no conflict marker, and leaves the recorded fixtures beside it as they are
  (checked); every source's copy but sdk-cashctrl's is the template's text byte for
  byte, so nothing of its own is lost, and sdk-cashctrl, whose copy carries lines of its
  own, moves them first should it ever update — the fixture rule lives in
  `/record-fixture` and conventions §10.
- `CLAUDE.md` — the live command in Commands and the sentence on `live.yml`'s step read
  `uv run pytest -m live --tb=short` — the flag keeps a failing test's frame arguments,
  a raw upstream payload among them, out of the log; port it with the split above.

The scaffolds of `_client.py`, `README.md` and `CHANGELOG.md` lose their write and
`basic` branches and the README's status comment no longer names `tasks_write.__all__`,
which matters to new repositories only. The two files under `_skip_if_exists` the
template stops rendering, `src/xippios/<package>/tasks_write.py` and
`tests/test_tasks_write.py`, exist only in a repository generated with write tools,
sdk-cashctrl alone, which stays on its last template tag. `copier update` to this
release would delete both, a write task of its own included, with no conflict marker,
and `mcp_write.py` with them; drop the `-mcp-write` entry point from `pyproject.toml`;
turn its `basic` answer into the default `query` and add `api_key_name: key`, while the
skip-listed `_client.py` keeps `BasicKeyAuth` and the skip-listed `CLAUDE.md` its
credentials row (checked with copier 9.19.1).
No other repository has them.

New repositories only, nothing to port: the `README.md` scaffold's MCP snippet and terms
sentence (a keyless source's README may close the server's brace on a line of its own),
the generated `CLAUDE.md`'s rate-limit row, Layout lines and start-time sentence, which
the 0.3.0 split leaves as the source wrote them, and `docs/upstream/FETCHED.md`'s
attribution placeholder, which the next `/refresh-upstream` rewrites. The update carries
the rest: `.claude/family.md`, the six commands, `tests/conftest.py`, `live.yml` and
`ci.yml`, the read server's instructions in `mcp.py`, and `junit_family`, the ruff pin
and the keywords in `pyproject.toml`, merged three ways where a source changed them.

**Updating from 0.2.2.** `copier update` asks nothing new and drops `needs_write_tools`
and `domain_topic` from `.copier-answers.yml` (checked with copier 9.19.1 on v0.2.2
renders, keyed and keyless; `source_pkg` was never recorded); no `-d` answer is needed
for them. The domain's topic stays on the GitHub repository; the `pyproject.toml`
keywords lose it. Every source's `source_name` is within the new 77-character bound. The
update creates `errors.py` where the package has none and deletes
`tests/fixtures/README.md`; `uv lock` after it resolves ruff to the pinned 0.17.1.

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
