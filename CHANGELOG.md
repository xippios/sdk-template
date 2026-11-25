# Changelog

All notable changes to sdk-template are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the template uses
[Semantic Versioning](https://semver.org/). Each change brings its entry as a fragment under
`changelog/`, which the release assembles into its section here, as
[changelog/README.md](changelog/README.md) lays it out, with a `Hand-apply:` note under the
bullet of a change that a source ports by hand.
[Updating generated repositories](README.md#updating-generated-repositories) in the README
says how a source takes a release.

This file holds the releases after 0.4.0. The sections of 0.4.0 and of every release before
it stand in `CHANGELOG.md` at the tag `v0.4.0`:
https://github.com/xippios/sdk-template/blob/v0.4.0/CHANGELOG.md.

## [0.5.0] - 2026-11-25

### Added

- `copier.yml` asks `shape`, `source` by default, and `general` renders the general part of a
  repository alone, its CI, release train, changelog, decision records, organization's checks
  and `/release-prep` around a package with its version, for a package of the family that
  wraps no API: none of a source's other files and none of its seven questions of an
  upstream, a `repository_name` that defaults to `sdk-<slug>`, and a `pyproject.toml` that is
  the repository's once rendered. Where its package holds a key, which `api_key_env` names in
  this shape too, it renders `_client.py`, which declares the key in `ENV_VARS`, holds no
  client and is the package's to fill, and beside it `tests/test_built_answers.py`, the one
  line that collects core's check of a built answer's mark, the package's too, since such a
  package builds answers in its tests (conventions §12, sdk-core ADR-0064). A source's update
  records `shape: source` and changes no other file. (ADR-0003,
  https://github.com/xippios/sdk-template/issues/302,
  https://github.com/xippios/sdk-core/issues/538,
  https://github.com/xippios/sdk-template/issues/351)

### Changed

- The rendered `pyproject.toml` names the import path of each package of
  `source_dependencies` beside `xippios.core` in ruff's `known-third-party`, the slug with
  dots as `import_path`'s default, so a dependency's imports sort with core's by the
  template's line. In the general shape, whose `pyproject.toml` is the repository's, the line
  comes at the first render. A source that added the line by hand takes it from the update,
  which renders it the same. (https://github.com/xippios/sdk-template/issues/317)
- The generated `CLAUDE.md`'s "Depends on" row says what each kind of dependency serves: a
  source package's task layer and its models, and a publisher's shared package's public
  names, since a shared package has no tasks. The help of `source_dependencies` and its row
  in this repository's README say the same, and so does a new source's first `CHANGELOG.md`
  entry for each dependency, which reaches new repositories only. (sdk-core ADR-0021,
  sdk-core ADR-0065, https://github.com/xippios/sdk-template/issues/335)
  - Hand-apply: `CLAUDE.md` — sdk-usda-psd and sdk-usda-gats, which declare their dependency
    on the shared package `xippios-usda-fas` at their adoption of core 0.5.0, write the row
    as a render of this release has it, and sdk-usda-esr keeps the row it has worded — the
    update never writes a source's `CLAUDE.md`, and the row said that a dependency serves its
    task layer alone.
- This repository's `README.md` and `CLAUDE.md` say each thing once: the README tells the
  questions, the files that both shapes render, the workflows of a render, the tests' variants
  and the proofs, and `CLAUDE.md` lays out the repository and holds the rules a change of the
  template follows, citing the README for the rest. `CHANGELOG.md` holds the releases after
  0.4.0 and names the tag whose file holds the older sections, and nothing that a source
  renders changes. (https://github.com/xippios/sdk-template/issues/300)
- An adoption of this release brings xippios-core 0.5.0, and the Hand-apply note below
  carries, ready to adapt, the entries that a source's changelog takes for it, first the
  adoption's own, `breaking` with its three versions, since a core minor is a breaking
  change of the source, then for each change of core 0.5.0 that the source's callers see
  the entries that the list "The changes that a source's callers see" under "Adopting core
  0.5.0" of sdk-core's `docs/handover.md` at its tag `v0.5.0` names, each in its group.
  The pull request that brings a change, the adoption's or a later one of the source's
  patch, copies the entry where it holds, as a fragment of its own, and words it for the
  source's own tasks and names. Where an entry and the handover's list part, the list
  holds. (https://github.com/xippios/sdk-core/issues/485)
  - Hand-apply: `changelog/breaking-<slug>.md` — The package depends on
    `xippios-core~=0.5.0`, its extras likewise, is updated to sdk-template v0.5.0 and
    applies conventions 1.30. (`https://github.com/xippios/<repository>/issues/<n>`) —
    every source's adoption, by conventions §15 item 9, its citation the URL of the
    adoption's issue.
    `changelog/changed-<slug>.md` — Every refusal of a call as given says `Nothing was
    sent.` after its first sentence, the MCP adapter's refusal of an argument among them,
    while a refusal after a request says what was sent, and a list of codes is checked by
    one call, which names the first code it refuses and refuses an empty list. The
    refusals' classes are unchanged.
    (https://github.com/xippios/sdk-core/issues/481) — every source, its own refusals and
    core's.
    `changelog/changed-<slug>.md` — `<write task>` is sent once, after a 429 or a renewing
    bearer's 401 too: its error after a 5xx or a failure in transit says that the request
    was sent once and that its outcome is unknown, or that nothing was sent where the
    connection failed, while a 4xx keeps upstream's words, and its docstring names the read
    that shows whether a failed write was applied. `<billed read>`, which upstream bills, is
    sent once too, a 5xx no longer repeating it.
    (https://github.com/xippios/sdk-core/issues/480) — each write task, and each read that
    upstream bills.
    `changelog/changed-<slug>.md` — The description of `<tool>` is its task's docstring
    before `Args:`, under 1,000 characters, and the text of each of its arguments stands
    in its input schema. (https://github.com/xippios/sdk-core/issues/485) — each tool whose
    description the adoption trims.
    `changelog/breaking-<slug>.md` — `<tool>` takes no `offset`: its task pages upstream
    itself, and a caller pages it by the task's own `start`.
    (https://github.com/xippios/sdk-core/issues/476) — each tool of a task that takes
    `start` whose cap was paged.
    `changelog/added-<slug>.md` — The answer of `<task>` names the codes of its rows in
    `meta.names`, and a row's code that the packaged list lacks is left out of the names and
    said in `meta.notes`, so no answer is withheld for it. `meta.notes` holds one sentence
    for each fact the task says about its answer.
    (https://github.com/xippios/sdk-core/issues/478) — each task whose record's code field
    declares its packaged list or the field in which upstream sends the name, and each
    task's notes.
    `changelog/changed-<slug>.md` — A decimal without fractional digits is a JSON integer
    in the answers, `16217` where it read `16217.0`.
    (https://github.com/xippios/sdk-core/issues/478) — each task whose answer holds such a
    decimal.
    `changelog/changed-<slug>.md` — `meta.retrieved_at` of `<task>` is the client's time of
    the answer, the oldest where it assembles several.
    (https://github.com/xippios/sdk-core/issues/479) — each task whose `retrieved_at` read
    another time.
    `changelog/changed-<slug>.md` — `<task>` sends no request at or past upstream's count,
    and where it needs more than `<n>` pages it refuses with `InvalidRequestError` and
    returns nothing, naming the count, the bound, the paging argument, the requests sent,
    the page reached and the total of pages. (https://github.com/xippios/sdk-core/issues/480)
    — each task that walks offset pages, with its bound.
    `changelog/breaking-<slug>.md` — `<task>` is renamed, takes the arguments that
    identify a record by position in the order of upstream's path and every other by
    keyword, or leaves, by the boundary of a source package. `<field>` holds a time that
    upstream prints in the type that keeps all it sends, naive where upstream states no
    zone, with no text beside it. (https://github.com/xippios/sdk-core/issues/474,
    https://github.com/xippios/sdk-usda-esr/issues/60) — each task, argument or field
    renamed or removed.
    `changelog/changed-<slug>.md` — The answers are kept in core's cache, each for the
    lifetime of the longest path prefix that its path starts with, none where no prefix
    matches, an expired answer dropped and the bodies held under a bound of bytes.
    (https://github.com/xippios/sdk-core/issues/479) — a read-only source of public
    data, in `added` where it kept no cache before.
    `changelog/changed-<slug>.md` — The refusal before a request into a spent quota says
    "quota" with the policy's source and no longer names the key's variable.
    (https://github.com/xippios/sdk-core/issues/485) — a source whose quota other sources
    share under one key.
    `changelog/changed-<slug>.md` — A tenant's client is kept until the registry is reset,
    so a tenant's changed variable takes effect at the next start, and a value that the
    source checks is refused by its own `ConfigError`, which names the variable and no
    value. (https://github.com/xippios/sdk-core/issues/475) — a multi-tenant source whose
    running server built a new client when a variable changed.
    `changelog/changed-<slug>.md` — Both servers are named `xippios-<source>`, the help of
    `--allow-remote` takes core's one wording, and the server's instructions come from the
    tasks module. (https://github.com/xippios/sdk-core/issues/476) — a source whose server
    took another name, the write server of a source that named it.
    `changelog/changed-<slug>.md` — The client reads each answer within one read timeout,
    60 s by default, and connects, writes and waits for a connection within 10 s each.
    (https://github.com/xippios/sdk-core/issues/475) — a source whose timeouts change.
- The five commands keep their steps and cite, for each mechanism, the section of sdk-core's
  conventions and the name of xippios-core 0.5.0 that serves it, in place of restating them:
  213 of their 790 lines leave. They name the `Answer` of `get_answer` that a wrapper
  returns, `record` and `send_once` under their plain names, a task's recording by the
  source's own capture, the walk `fetch_pages`, `check` with one code or a list, `NamedBy`,
  `check_dest`, `read_json`, `Lists` and `run`, and no longer `record_task`, `naive_time`,
  `array_key`, `UNNAMED_CODES` or `NO_TENANT_TASKS`.
  `/record-fixture` records with a source's own recorder, `scripts/record_fixture.py`, where
  it has one, and its step 1 names the variables of `live_secrets` beside the key, and
  `/refresh-upstream` holds `--check` as the one comparison of the snapshot with upstream,
  since core's family check no longer judges `FETCHED.md` against `SNAPSHOT`.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/310,
  https://github.com/xippios/sdk-template/issues/333,
  https://github.com/xippios/sdk-core/issues/483)
- The generated `CLAUDE.md` keeps what the package wraps, its layout, its commands with the
  live run, how a template release reaches it and its specifics, and restates no rule that
  sdk-core's conventions hold: `## Code rules`, `## When something is unclear`, the offline
  paragraphs of `## Commands` and the two file lists of `## Template updates` leave it, the
  section naming `_skip_if_exists` of `copier.yml` in place of the lists. The nine rules of
  `## Never` move into `.claude/rules/never.md`, a file of the template's that every update
  writes again and that Claude Code loads at launch by its place, and the Layout moves into
  `docs/layout.md`, the source's own, which `CLAUDE.md` imports and which holds what the
  source adds to the family's tree, laid out once in this repository's README. The Never
  file's rule on credentials names the tenants' key pattern only where the tenants hold the
  key, since the template knows no variable of tenants that hold another credential.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/233,
  https://github.com/xippios/sdk-template/issues/301)
  - Hand-apply: `CLAUDE.md` — delete `## Code rules`, `## When something is unclear` and
    `## Never`, the paragraph after the code block of `## Commands` that says the tests run
    offline and, where the source has a key, the one after it on the key's placeholder, the
    Layout's code block with the paragraph below it and the two file lists of
    `## Template updates`, then write the intro, `## Layout` with its import line
    `@docs/layout.md` and `## Template updates` as a render of this release has them, and
    move each line of the source's own from what leaves into its
    `## <source name> specifics` and each entry of its Layout that this repository's README
    does not lay out, a module of `api/` or `parse/` or a script or test of its own, into
    `docs/layout.md`, which takes about 130 lines out of a render's file and about 1,680 out
    of the twelve sources' files together, an estimate. Then search what stays, and the
    lines moved into `docs/layout.md`, for each name below, which a render of v0.4.0 or
    v0.4.1, the template's proofs or a source's own tests held and which this release or
    core 0.5.0's family check takes out, and reword or delete each line that names one the
    source no longer holds: `organization.yml`, `xippios_placeholder_key_envs`, the answers
    `api_base_url`, `api_key_location`, `api_key_name`, `rate_limit_per_minute`,
    `rate_limit_burst`, `rate_limit_provenance`, `gateway`, `tenant_credential_env` and
    `human`, `INSTRUCTIONS` and `BOUND_INSTRUCTIONS` of `mcp.py`, `READERS` and `ALLOWED`
    of `tests/test_built_answers.py`, `test_upstream_answers` of `tests/test_live.py`,
    `LEVEL` of `ci.yml`, `tests/test_contract.py`, whose package contract core's family
    check holds, and the proof shapes `--gateway` and `--tenants-keyless`. The names that
    leave core stand in core's list, "The names that left" under "Adopting core 0.5.0" of
    sdk-core's `docs/handover.md` at its tag `v0.5.0`, which names
    `xippios_placeholder_key_envs` too, as the render held it —
    sdk-core's conventions hold the rules, the template's Never file keeps the rules no
    change breaks in what Claude Code loads, a change that adds a module then updates a
    file of the source's own, and a line that names what left points its reader to nothing.
    `docs/layout.md` — fill it with what the package adds to the family's tree, which this
    repository's README lays out once, in a code block laid out as that tree is, a line per
    file or directory with what it holds, from the entries that the item above moves out of
    the Layout of `CLAUDE.md`, each module of `api/` or `parse/` and each script or test of
    the source's own among them — the update creates the file where the repository has
    none, holding the render's stub, which says what the file holds and that the change
    that adds a module updates it, and it is the source's from this release on, so no later
    update writes it again.
- `tests/conftest.py` and `.secrets.baseline` are the source's from this release on: they
  stand under `_skip_if_exists`, so an update merges no line of the template's into a
  source's own there, and a later change of core's baseline or of the plugin's line reaches a
  source by a Hand-apply note. The render's README names neither `published_at` nor `vintage`
  among what every response carries and says under `## Workflows`, for each workflow the
  render holds, what it checks, when it runs, what the calling file hands over and what
  switches it, and a keyless `_client.py` declares no `API_KEY_ENV`. For new repositories
  only, the stub of `docs/upstream/FETCHED.md` keeps its title and one paragraph, since core's
  frame writes the file whole at the first refresh, and `scripts/refresh_upstream.py`
  declares no `reduce` of its own, so core's default keeps each page as fetched.
  (https://github.com/xippios/sdk-template/issues/300,
  https://github.com/xippios/sdk-template/issues/308)
  - Hand-apply: `README.md` — in the first paragraph, say that every response carries its
    metadata (source, endpoint, retrieved_at, request), naming `published_at` and `vintage`
    only where every task sets them, and add `## Workflows` before `## Documents` as a render
    of this release holds it with the source's answers, one paragraph for each workflow the
    repository holds — core's `ResultMeta` leaves both fields to the task that knows them,
    and the organization's rule has the README say what each workflow does, since the
    workflow files carry no comment.
    `src/xippios/<import path>/_client.py` — in sdk-eurostat, sdk-faostat, sdk-google-mail,
    sdk-usda-esmis and sdk-usda-wasde, delete the line `API_KEY_ENV: str | None = None` and
    the name `"API_KEY_ENV"` in `__all__` — a source without a key declares no key's
    variable, and `ENV_VARS` names what a host sets.
    `src/xippios/<import path>/errors.py` — delete it where it still holds the scaffold's
    `__all__: list[str] = []` and no class — a stub that the source never filled says
    nothing, and an update leaves it deleted.
    `src/xippios/<import path>/enums.py` — delete it where it still holds the scaffold's
    `__all__ = []` and no enum — the same.
    `tests/conftest.py` — nothing to port: the file is the source's from this release on —
    an update no longer merges the template's lines into it.
    `.secrets.baseline` — nothing to port: the file is the source's from this release on —
    an update no longer merges the template's lines into the entries the source audited.
- The template's own CI proves every shape by one call, `scripts/prove.sh --all`, which
  holds the list of the shapes, runs each proof in a process of its own, goes on after one
  that failed and fails where one fails, so a shape added or removed changes the script,
  never the workflow. Its steps and the script no longer liken a shape to a source of the
  family. (https://github.com/xippios/sdk-template/issues/302,
  https://github.com/xippios/sdk-template/issues/304)
- The template's own workflows carry no comment but the version after a pinned action,
  as the workflows it renders as its own, and its README says what the release run does,
  how a run that failed is finished, why a release waits for no other push to `main` and
  why the run's one checkout keeps its credentials.
  (https://github.com/xippios/sdk-template/issues/307)
- The generated `live.yml` and `siblings.yml` carry no comment but the version after a
  pinned action, as the organization decided for every workflow file, and the template's
  README says what their comments said: what each checks, when it runs, what it is handed
  and why `siblings` is a workflow of its own beside `ci.yml`. `copier update` takes the
  comments out, and `ci.yml` and `publish.yml` keep sdk-core's bytes.
  (https://github.com/xippios/.github/issues/111,
  https://github.com/xippios/sdk-template/issues/265)

### Removed

- `copier.yml` no longer asks `gateway`, `tenant_credential_env` or `human`: an update drops
  the three recorded answers from `.copier-answers.yml` and copies `.github/CODEOWNERS` as it
  stands, each path that steers a source owned by `jdidaskalu`. The scaffold's `_client.py`
  renders no gateway, so a source behind api.data.gov keeps `api_key_env` and imports the
  gateway from its publisher's shared package, `xippios.usda.fas`. A multi-tenant source whose
  tenants hold no key names that credential's variables in `live_secrets`, the reserved
  tenant's first, as sdk-google-mail's update passes them,
  `-d "live_secrets=[GOOGLE_DEMO_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]"`, by
  the release's list of the answers each source passes, which keeps the bytes of its
  `live.yml`. (ADR-0002,
  https://github.com/xippios/sdk-template/issues/301,
  https://github.com/xippios/sdk-template/issues/302)
  - Hand-apply: `src/xippios/<import path>/_client.py` — in sdk-usda-psd, sdk-usda-esr and
    sdk-usda-gats, import `Gateway` from `xippios.usda.fas` in place of
    `xippios.core.data_gov` — the gateway leaves core for its publisher's shared package, and
    the file is the source's once rendered.
- `copier.yml` no longer asks `api_base_url`, `api_key_location`, `api_key_name`,
  `rate_limit_per_minute`, `rate_limit_burst` and `rate_limit_provenance`, and refuses
  `has_reference_data: true` beside `tenant_param`: an update drops the recorded answers from
  `.copier-answers.yml` and the fixture cap's `LEVEL` variable from `ci.yml`, and changes no
  file a source fills. A new repository's `_client.py` keeps a marked place for the base URL,
  the key's auth and the pace, as its `CLAUDE.md` does for their rows, and its first pull
  request fills them from upstream's documentation as it fills `tasks.py`, which matters to
  new repositories only. The reference script's multi-tenant branch and the Layout entry of
  a flat source with a dependency in the generated `CLAUDE.md` leave with them.
  (https://github.com/xippios/sdk-template/issues/301)

### Breaking

- A render depends on xippios-core 0.5.0, `core_version`'s default, by the bound
  `xippios-core~=0.5.0`, its extras likewise, and the six files it copies from sdk-core,
  `ci.yml`, `publish.yml`, `.pre-commit-config.yaml`, `.secrets.baseline`, `.python-version`
  and `LICENSE`, follow core's bytes at 0.5.0. `ci.yml` and `publish.yml` carry no comment
  but the version after a pinned action, the template's own lines among them, as core's
  bytes carry none (conventions §13), and the render's `pyproject.toml` names no
  `xippios_placeholder_key_envs`, since core's plugin sets each secret variable of the
  package's `ENV_VARS` in `_client.py` to its placeholder. A source takes them by its
  adoption, whose update passes `-d core_version=0.5.0`.
  (https://github.com/xippios/sdk-template/issues/312, https://github.com/xippios/sdk-core/issues/475,
  https://github.com/xippios/sdk-core/issues/505)
  - Hand-apply: `pyproject.toml` — in sdk-faostat, delete the line
    `xippios_placeholder_key_envs = [...]` that it wrote by hand under
    `[tool.pytest.ini_options]`, with its comment, which the update keeps as the source's
    own line — core's plugin reads `ENV_VARS`, which declares both variables, and no longer
    reads the option.
    `README.md` — in the paragraph on `publish.yml` under `## Workflows`, say that its job
    `tag` holds the one checkout of the repository that keeps its credentials, since it
    pushes the tag with the job's token, and that every other checkout sets
    `persist-credentials: false` — conventions §13 has the README name that exception, which
    the workflow's comment named before.
    `tests/conftest.py` — where its comment says that a key's variable is named under
    `xippios_placeholder_key_envs` in `pyproject.toml`, say that core's plugin reads it from
    `ENV_VARS` in `_client.py` — the option leaves core.
- The rendered `scripts/refresh_reference.py` declares its lists in one `Lists` of
  xippios-core, with the package, the lists it ships, its client and the quota header, and
  its `main` calls core's `run(LISTS, argv)`, while its commented examples, which reach a
  new render alone, hold a list of values whose fetch makes its records from the values in
  its wrapper's `Answer`, since core's frame refuses an `Answer` of plain values.
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
- The rendered `mcp.py` and `mcp_write.py` hold no line of a source: `build()` returns the
  tool set that xippios-core builds from the tasks module, `ToolSet.from_tasks`, `run()`
  calls core's one `main`, with the registry and the check for a multi-tenant source, and
  `http.py` passes `tool_functions(tasks)`, the list that `mcp.py` serves. An update renders
  the three files again and merges a source's own edit of its earlier render into them, as
  into every file of the template's, silently where this release leaves the lines around the
  edit alone and as a conflict where it changes them, so a source takes the render's text by
  hand. The scaffolds of `tasks.py` and `tasks_write.py` hold the server's instructions as
  `MCP_INSTRUCTIONS`, and a multi-tenant source's bound text as `MCP_BOUND_INSTRUCTIONS`, the
  scaffold of `__init__.py` re-exports the tenant list task where `tasks.py` lists it, and
  for new repositories only the comments of `_client.py` name core's one `KeyAuth`.
  (ADR-0002, https://github.com/xippios/sdk-core/issues/476)
  - Hand-apply: `src/xippios/<import path>/tasks.py` — move the instructions that `mcp.py`
    held, `INSTRUCTIONS`, into `MCP_INSTRUCTIONS`, and a multi-tenant source's
    `BOUND_INSTRUCTIONS` into `MCP_BOUND_INSTRUCTIONS`, declare in sdk-google-mail
    `MCP_LOOPBACK_ONLY = True` for its read server held to loopback, and give
    `mcp_apply_options` where it is declared, as in sdk-usda-gats and sdk-usda-nass, core's
    signature, `mcp_apply_options(namespace) -> None`, without the server — core reads them
    from the tasks module, and the render's `mcp.py` holds none of them.
    `src/xippios/<import path>/tasks_write.py` — move the write server's instructions into
    `MCP_INSTRUCTIONS` likewise, and a multi-tenant source's bound text into
    `MCP_BOUND_INSTRUCTIONS` — the same, for `mcp_write.py`.
    `src/xippios/<import path>/_client.py` — in sdk-cashctrl, pass its noun for a tenant
    as `Tenants(noun=...)` — core's `main` reads the noun from the registry.
    `src/xippios/<import path>/__init__.py` — import and list in `__all__` each task of
    `tasks.__all__` and `tasks_write.__all__` that it does not re-export yet — core's
    family check holds that every task is the package's own.
    `src/xippios/<import path>/mcp.py` — after the update, compare it with a render of this
    release with the source's answers and take the render's text wherever the two part, a
    line of the source's that the update kept without a conflict included — the update
    merges a source's own edit into the render and says nothing where this release leaves
    the lines around it alone, and no line of the file is a source's (ADR-0002, decision 9).
    `src/xippios/<import path>/mcp_write.py` — the same, where the source has a write
    server, and in sdk-cashctrl, whose update keeps its line
    `server = build_server(build(), name=...)`, take the render's line
    `server = build_server(build())`, so that its write server takes the name
    `xippios-cashctrl` and keeps none of its own —
    the same, and both servers of a source are named `xippios-<source>`.
    `src/xippios/<import path>/http.py` — compare it with the render likewise and take the
    render's text — the same.

### Answers each source passes

- sdk-google-mail: `uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.5.0 -d core_version=0.5.0 -d core_git_ref= -d "live_secrets=[GOOGLE_DEMO_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]"`
- sdk-usda-esr: `uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.5.0 -d core_version=0.5.0 -d core_git_ref= -d 'source_dependencies=[{name: usda-fas, minor: "0.1", key_env: DATA_GOV_API_KEY}]'`
- sdk-usda-gats: `uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.5.0 -d core_version=0.5.0 -d core_git_ref= -d 'source_dependencies=[{name: usda-fas, minor: "0.1", key_env: DATA_GOV_API_KEY}]'`
- sdk-usda-psd: `uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.5.0 -d core_version=0.5.0 -d core_git_ref= -d 'source_dependencies=[{name: usda-fas, minor: "0.1", key_env: DATA_GOV_API_KEY}]'`
- sdk-usda-wasde: `uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.5.0 -d core_version=0.5.0 -d core_git_ref= -d 'source_dependencies=[{name: usda-esmis, minor: "0.4", key_env: ""}]'`

## [0.4.1] - 2026-11-23

A generated repository takes xippios-core 0.4.1 with this release, and its scripts run on
core's frames: the capture script declares the source's snapshot and the reference script
its packaged lists for `xippios.core.refresh`, the tests collect core's check of a built
answer and its nightly comparison of the packaged lists, and the commands name core
0.4.1's helpers and recorder. A render carries the organization's one ADR index script and
its release script, and starts the organization's checks from one trigger file each in
place of `organization.yml`. A source takes this release together with xippios-core 0.4.1
in one adoption before its next release, with the README's update command,
`copier update --defaults --vcs-ref=v0.4.1 -d core_version=0.4.1 -d core_git_ref=`, ports
what the Hand-apply notes name and copies the entries for core 0.4.1's changes from the
note that carries them. The release adds no question and no choice, so every source runs
that command as it stands.

### Added

- From this release on, a release of the template that adds a question to `copier.yml`, or
  a choice to one, ends its section with `### Answers each source passes`: an item per
  source whose update passes an answer that the README's update command does not, holding
  that update's command whole, with every `-d` argument it passes. An adoption copies its
  command from that list, never from the prose of an entry, and a source that the list
  leaves out runs the README's update command as it stands.
  (https://github.com/xippios/sdk-template/issues/245)
- A render collects xippios-core 0.4.1's check of a built answer's mark, as
  sdk-core ADR-0049 records it, in `tests/test_built_answers.py`, its one line followed by
  the source's `READERS` and `ALLOWED`, and `/add-endpoint` says how a test marks an answer
  it builds. The module is the source's once rendered, so `copier update` creates it where a
  source has none and leaves the source's declarations alone after. The template's rendered
  tests build no answer, so a new source passes the check before its first test.
  (conventions §10, https://github.com/xippios/sdk-template/issues/271)
  - Hand-apply: `CLAUDE.md` — name `test_built_answers.py` under `tests/` in the Layout,
    and `tests/test_built_answers.py` after `tests/test_live.py` among the files the
    package fills, as a render with the package's answers has them — the update creates the
    module and never writes the package's `CLAUDE.md`.
    `tests/test_built_answers.py` — where the source holds a module of that name of its
    own, as sdk-cashctrl does, replace its own check by the collecting line with the
    source's `READERS` and `ALLOWED` below it — the update keeps a file of that name as it
    stands.
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
- A render carries `scripts/release_prepare.py` and the assembler it loads by its path,
  `scripts/changelog_assemble.py`, the organization's one version of each, and
  `/release-prep` runs `python3 -I scripts/release_prepare.py <version> --date <YYYY-MM-DD>`
  in place of the assembly by hand. The script writes the release's section of
  `CHANGELOG.md` from the fragments, removes them and sets the version in `pyproject.toml`
  and on the package's own entry in `uv.lock`, with no `uv lock`, and a second run writes
  nothing. The rendered `pyproject.toml` leaves both scripts out of ruff, and its strict mypy
  checks them as they stand, with no override.
  (https://github.com/xippios/sdk-template/issues/247)
  - Hand-apply: `CLAUDE.md` — name `scripts/changelog_assemble.py` and
    `scripts/release_prepare.py` after `scripts/adr_index.py` among the files the update
    writes again, and lay both out under `scripts/` in `## Layout`, as a render has them —
    every update writes the two scripts again, and the Layout names each script the
    repository holds.

### Changed

- The rendered `/record-fixture` names `Rewrite`, the type of a source's rewrite step that
  `xippios.core.testing` exports, and says that the step writes `REDACTED` for a field of a
  request that the fixture must not keep and drops none, as sdk-core ADR-0048 records it, so
  that core's census of built answers compares a replay with its recording key by key.
  (conventions §10, https://github.com/xippios/sdk-template/issues/271)
- A new source's write scaffold declares its preview, `WritePreview` in `tasks_write.py`,
  tagged `performed: Literal[False]` with `reads`, the operations the preview read, as
  sdk-core ADR-0050 records it, and `/add-endpoint` asks each write task's docstring to say
  whether its preview reads and at what cost. The write server's test that `/add-endpoint`
  gives a source's first write task passes `preview_reads=True`. The scaffold matters to new
  repositories only, since `tasks_write.py` is the source's once rendered.
  (conventions §8, https://github.com/xippios/sdk-template/issues/271)
- The rendered `scripts/refresh_reference.py` is a short script on xippios-core 0.4.1's frame,
  `xippios.core.refresh` of sdk-core ADR-0051, which fetches the lists a source declares, one
  `Listed` each, writes their files, the provenance rows and `enums.py`, takes `--only` and
  `--render-only` and counts a request that ended in a transport error as sent. A
  multi-tenant render fetches through the reserved tenant's client and needs none of its
  variables for `--render-only`. `/refresh-reference-data` says what a source declares in a
  `Listed` and that the run writes the list's provenance row.
  (https://github.com/xippios/sdk-template/issues/239)
  - Hand-apply: `scripts/refresh_reference.py` — declare each list as a `Listed` in one
    `LISTS`, with an `origin` for each list whose provenance row names more than its
    endpoint, hand them to `xippios.core.refresh.run` with the package, `PACKAGED_LISTS`,
    the client and the quota header, delete the script's own fetches, writes, `render`,
    `Meter`, `metered` and `--only`, the port of the 0.4.0 metering among them, and run it
    once with `--render-only` — core 0.4.1 carries the frame of sdk-core ADR-0051, which
    counts a request that fails in transport as sent and writes the provenance rows from
    the declarations.
    `src/xippios/<package>/params.py` — where the docstring of `PACKAGED_LISTS` names the
    script's `LISTS`, `ID_LISTS` and `TABLES`, name its one `LISTS` of `Listed` — the port
    leaves the script one declaration.
- A render's `scripts/refresh_upstream.py` declares the source's `Snapshot` as `SNAPSHOT`,
  which the frame of xippios-core 0.4.1, `xippios.core.refresh`, fetches, checks and writes
  into `docs/upstream/`, in place of the template's skeleton of the whole capture. The
  rendered `/refresh-upstream` and `CLAUDE.md` say what a source fills in the declaration,
  and the converter its `reduce` uses is pinned in the dev group of `pyproject.toml` alone,
  since the script runs in the project's environment with no `# /// script` block. An
  adoption deletes its port of the skeleton and declares its pages, attribution and hooks
  on core's frame, whose `FETCHED.md` holds the table `Not fetched` and the row of
  `OBSERVED.md`, so it needs no decision of its own for either.
  (https://github.com/xippios/sdk-template/issues/235, https://github.com/xippios/sdk-template/issues/240, https://github.com/xippios/sdk-core/issues/363)
  - Hand-apply: `scripts/refresh_upstream.py` — delete the port of the 0.4.0 skeleton, its
    `# /// script` block among it, and declare the source's `Snapshot` as `SNAPSHOT` with
    its pages, attribution, pages left out, vocabulary, capture and hooks, run by
    `run(SNAPSHOT)` under `if __name__ == "__main__":` alone, as the source's part of
    "Adopting core 0.4.1" in sdk-core's `docs/handover.md` lists it — core's frame writes
    the table `Not fetched` and the row of `OBSERVED.md` from the first refresh on, so a
    source's row for the table closes with its patch.
    `CLAUDE.md` — write the Layout's line of `scripts/refresh_upstream.py` as the render
    has it — the line calls the source's filled script the template's skeleton.
- A render depends on xippios-core 0.4.1, `core_version`'s default, by the bound
  `xippios-core~=0.4.1`, its extras likewise, and the six files it copies from sdk-core
  follow core's bytes at v0.4.1. Of them only `publish.yml` changes, titled `Publish`, its
  first line citing sdk-core ADR-0039, decision 6, in place of the record that it
  supersedes. A source takes both by its adoption, whose update passes
  `-d core_version=0.4.1` as the README's update command does.
  (https://github.com/xippios/sdk-template/issues/242, https://github.com/xippios/sdk-core/issues/407)
- An adoption of this release brings xippios-core 0.4.1, and the Hand-apply note below
  carries, ready to adapt, the entries that a source's changelog takes for it, first the
  adoption's own, `changed` with its three versions, then for each change of core 0.4.1
  that the source's callers see the entries that the list under "Adopting core 0.4.1" of
  sdk-core's `docs/handover.md` names, each in its group, and in `changed` the one it names
  without a group. The pull request that brings a change, the adoption's or a later one
  of the source's patch, copies the entry where it holds, as a fragment of its own, and
  words it for the source's own tasks and names. Where an entry and the handover's list
  part, the list holds, and the source corrects its fragment before its release, which
  rewords no entry. (https://github.com/xippios/sdk-template/issues/238,
  https://github.com/xippios/sdk-template/issues/280)
  - Hand-apply: `changelog/changed-<slug>.md` — The package depends on
    `xippios-core~=0.4.1`, its extras likewise, is updated to sdk-template v0.4.1 and
    applies conventions 1.29. (`https://github.com/xippios/<repository>/issues/<n>`) —
    every source's adoption, by conventions §15 item 9, its citation the URL of the
    adoption's issue, and `breaking` in place of `changed` where the same pull request
    brings core 0.4.0 too, a core minor.
    `changelog/added-<slug>.md` — `<tool>` takes `offset`, the rows of a cut answer already
    shown, and answers the rows after them by running its task again. Every page carries
    its note, the last one too, and the note of every page but the last names the `offset`
    to continue with, so an answer without a note is whole.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap in `MCP_CAPS` is
    `ResultCap(paged=True)`.
    `changelog/changed-<slug>.md` — `<tool>` shows the newest rows of a cut series, ordered
    oldest first, in place of the oldest, and its `offset` walks to older rows.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap keeps the last
    rows, `ResultCap(keep="last")`.
    `changelog/changed-<slug>.md` — The note of a cut answer of `<tool>` names the `offset`
    to continue with in place of the narrower query it named before.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose note named a way
    around the cut before its cap took `paged=True`.
    `changelog/added-<slug>.md` — The answer of `<task>` names each `<parameter>` code it
    was called with in `meta.names`, by the name that its packaged list holds,
    `{"<parameter>": {"<code>": "<name>"}}`.
    (https://github.com/xippios/sdk-core/issues/316, https://github.com/xippios/sdk-core/issues/310)
    — each task that takes a country, area, reporter or partner code, by `names_codes`.
    `changelog/changed-<slug>.md` — `<task>` withholds its answer for a `<parameter>` code
    that its packaged list lacks, with the list's refusal, where it answered for such a
    code before. (https://github.com/xippios/sdk-core/issues/316) — each task that sent
    such a code upstream unchecked, as sdk-faostat's `get_series` sent a code of a domain
    outside its five area tables.
    `changelog/breaking-<slug>.md` — The tasks refuse an ISO alpha-3 code, which they
    resolved before the call, and the refusal names the UN Comtrade code it stands for,
    `"CHE"` refused naming `757 (Switzerland)`. The refusal ends with its hint and its
    reason, without the sentence that the packaged list may be out of date.
    (https://github.com/xippios/sdk-core/issues/375, https://github.com/xippios/sdk-core/issues/316)
    — sdk-comtrade alone, whose release this makes a minor by conventions §12.
    `changelog/changed-<slug>.md` — `<task>` refuses a query over upstream's limit of `<n>`
    records per call with core's `QueryTooLarge`, an `InvalidRequestError` whose message
    gives the count, the limit and what narrows the query, and answers a count of 0 with
    its empty answer, sending no data request. (https://github.com/xippios/sdk-core/issues/317)
    — each task that refuses with `QueryTooLarge`, by `fetch_counted` or by its `classify`
    of upstream's refusal, whose message names the request too, and sdk-comtrade's entry
    adds that the answer of `get_data` carries the count as `meta.total`.
    `changelog/breaking-<slug>.md` — `xippios.comtrade.errors` holds no `QueryTooLarge` of
    its own any more, so an import of it fails, and a caller catches core's
    `xippios.core.QueryTooLarge`, which the tasks raise.
    (https://github.com/xippios/sdk-core/issues/317) — sdk-comtrade alone, in the minor of
    its alpha-3 codes.
    `changelog/changed-<slug>.md` — `<task>` refuses a `<parameter>` code that its packaged
    list lacks by core's check, which names the list, its fetch date and the closest codes,
    and refuses a value of the other type than the list's codes with
    `InvalidRequestError`, naming the integer or the text to pass and ending with the
    task's reason. Another text given for integer codes is refused naming the codes that the
    task's strategy finds for it, else those whose name holds it. A value of the hint table
    of `<parameter>` is refused with its hint and its reason, without the sentence that the
    packaged list may be out of date. (https://github.com/xippios/sdk-core/issues/313) —
    each argument that `PackagedList.codes(...).check` now checks, worded by the refusals
    whose wording or class the tests of the port change, the hint table's sentence where
    the source keeps one.
    `changelog/changed-<slug>.md` — `<task>` refuses a `since` it cannot read in core's
    wording, `since must be the meta.vintage text of an earlier call, an ISO date and time without a time zone such as '2026-10-06T08:00:00'`,
    its class and its two reasons kept. (https://github.com/xippios/sdk-core/issues/318) —
    sdk-usda-esr alone, since sdk-usda-psd's wording stays as it is.
    `changelog/changed-<slug>.md` — `<task>` refuses a range over its ceiling of `<n>`
    `<unit>` in core's wording before the first request, naming the range, the ceiling, its
    unit, where the MCP server's ceiling is lower the option that raises it, and that
    nothing was sent, its class `InvalidRequestError` and the option's name unchanged. A
    request after the first that fails raises its error, its class kept, naming the periods
    answered before it by their count, the first and the last, and the task returns nothing.
    (https://github.com/xippios/sdk-core/issues/315) — each task on `fetch_periods`, but
    sdk-usda-nass's split of `year__GE` alone, whose refusal of its own says that the count
    was sent.
    `changelog/breaking-<slug>.md` — `tasks.<name>` and `tasks.set_<name>` are removed, so
    a caller's call of either fails, and one `Ceiling` of core's holds the task's ceiling of
    `<n>` `<unit>` in their place. (https://github.com/xippios/sdk-core/issues/315) —
    sdk-usda-nass's `split_ceiling` and `set_split_ceiling` and sdk-usda-gats's
    `series_ceiling` and `set_series_ceiling`, each making its source's release a minor by
    conventions §12, unless its port keeps the two names.
    `changelog/added-<slug>.md` — The preview of `<write task>` carries `reads`, the
    operations it read, `[]` for none, and the task's docstring says whether its preview
    reads first and what the read costs. (https://github.com/xippios/sdk-core/issues/182) —
    each write task, its preview held by `assert_write_tools` with `preview_reads`.
- The rendered `/add-endpoint` and `/record-fixture` describe the helpers and the recorder of
  xippios-core 0.4.1, which a source adopts with this release. `/add-endpoint` refuses a code
  that a packaged list lacks by the `check` of `PackagedList.codes(...)` in place of an
  `UnknownCode` raised by hand, names `names_codes` and `UNNAMED_CODES`,
  `ResultCap(paged=True)` and `keep="last"`, `newer_than`, `fetch_counted` with
  `QueryTooLarge` and `Ceiling` with `fetch_periods`, and in a render without reference data
  names no helper of a packaged list and no reference lookup. `/record-fixture` names
  `rewrite=`, `send_once` in place of a client built for one attempt, the recorder's refusal
  of a 1xx or a 3xx and `record_task` for every exchange of a task.
  (https://github.com/xippios/sdk-template/issues/250, https://github.com/xippios/sdk-template/issues/270)
- The comment above the changelog step of the rendered `ci.yml` and the rendered
  `/release-prep` state conventions §15 item 9 as it now reads: an adoption's fragment names
  the core bound, the template's tag and the conventions' version as they stand after the
  update, changed or not, `breaking` where it brings a core minor and `changed` where it
  brings none. `/release-prep` takes each entry as its fragment reads, under its fragment's
  group, and rewords or regroups none, since a wrong entry is corrected in its fragment
  before the release.
  (https://github.com/xippios/sdk-core/issues/355, https://github.com/xippios/sdk-template/issues/251)
- The template renders no test of the row of `OBSERVED.md` in `docs/upstream/FETCHED.md`,
  since xippios-core 0.4.1's family check holds that row in every source that keeps the
  file. sdk-usda-esmis, sdk-usda-wasde, sdk-usda-esr and sdk-cashctrl delete what their
  `tests/test_observed.py` holds of the row in their patches, as core 0.4.1's changelog lists
  for each. sdk-eurostat's test of the row in `tests/test_refresh_upstream.py` holds the row
  that its own capture script writes, not the committed one, and stays with that script.
  (https://github.com/xippios/sdk-template/issues/236)
- The rendered `/release-prep` cites the count of the live run's requests from the line
  `requests sent by the live run: <n>` that xippios-core 0.4.1's testing plugin prints in the
  log of `live.yml`, from a green run on the commit of `main` that the release starts from
  and never from a run on an earlier commit. The header of the rendered `tests/test_live.py`
  points to that line and states no count of its own.
  (https://github.com/xippios/sdk-core/issues/382, https://github.com/xippios/sdk-template/issues/237)
  - Hand-apply: `tests/test_live.py` — add to the module's docstring that core's testing
    plugin prints the run's requests as `requests sent by the live run: <n>`, the count in
    the log of `live.yml` that `/release-prep` cites, and delete a count the docstring
    states by hand — the plugin counts every run, so a count written by hand goes stale
    with the next live test.
- `scripts/adr_index.py` is the one version that the organization's repositories share, which
  opens each line of `docs/adr.md` with the anchor that a citation such as `docs/adr.md#0014`
  links to and lists the records in force before the superseded ones. The rendered
  `pyproject.toml` leaves the script out of ruff while mypy checks it, and every command runs
  it as `python3 -I`. A source writes its index again with the new script in its adoption pull
  request, since the check `adr-index` fails on the index that the old one wrote.
  (https://github.com/xippios/sdk-core/issues/357, https://github.com/xippios/sdk-template/issues/246)
  - Hand-apply: `CLAUDE.md` — write the index command of `## Commands` as
    `python3 -I scripts/adr_index.py --check` — the check `adr-index` runs the script
    isolated, and people run it as the check does.
    `docs/adr.md` — write it again with `python3 -I scripts/adr_index.py` — the new script
    opens each line with its record's anchor and lists the superseded records last.
- A generated repository starts the organization's checks from one trigger file each,
  `conventions.yml` and `adr-index.yml`, in place of `organization.yml`, which
  `copier update` deletes, so each check runs once after the adoption and keeps its name,
  `conventions / conventions` and `adr-index / adr-index`, while a push to `main` reports
  `range / range`. A variable `WORKFLOW_<NAME>` of `off`, the repository's over the
  organization's, switches off either check, `live.yml`, now titled `Live tests`, or
  `siblings.yml`, while `ci.yml` and `publish.yml` take no switch. This repository runs
  the same two trigger files on its own pull requests.
  (https://github.com/xippios/sdk-template/issues/249)
  - Hand-apply: `CLAUDE.md` — in the Layout's `.github/workflows/` entry, name
    `conventions.yml` and `adr-index.yml` in place of `organization.yml`, as a render of
    this release words them — the update deletes `organization.yml` and renders the two
    trigger files.
- The generated `CLAUDE.md` names, beside the files a source fills, the files that
  `copier update` writes again, `mcp.py` among them, so that a source keeps no text of its
  own in them. Its code rule on the three layers lets the tasks call reference data only
  where `has_reference_data` is `true`. A test holds the list equal to every rendered file
  outside `_skip_if_exists`, by path, so a file the template adds or renames outside
  `.github/` and `.claude/` is named in the same change.
  (https://github.com/xippios/sdk-template/issues/243, https://github.com/xippios/sdk-template/issues/244)
  - Hand-apply: `CLAUDE.md` — in `## Template updates`, follow the paragraph on the files
    the package fills with the paragraph on the files the update writes again, as a render
    with the package's answers has it, and where `has_reference_data` is `false`, as in
    sdk-x and sdk-google-mail, end the three-layer rule's clause at "the tasks call only
    wrappers" — `mcp.py` and the other files named there are written again at every
    update, and a source without reference data has none for its tasks to call.

### Fixed

- A multi-tenant source without a key names its live secrets after the reserved tenant's
  credential under `xippios_placeholder_key_envs` in `pyproject.toml`, since its own auth
  reads them, so core's plugin sets each in every test not marked live. A comment under
  `[project.scripts]` says that a script of the package's own goes after the servers' entry
  points, where an update keeps it while the template's lines beside it stay. Neither adds
  a question or a hidden answer, and sdk-google-mail, which wrote both by hand, keeps its
  script and list at its adoption and takes the render's comment above the list where its
  own wording conflicts. (https://github.com/xippios/sdk-template/issues/241)
