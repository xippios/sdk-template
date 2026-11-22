# sdk-template — instructions for Claude Code

This repository is the copier template that generates every `xippios-<source>` package
repository. It is not a Python package. What it generates must satisfy the documents
listed under [`## Documents` in the README](README.md#documents): sdk-core's conventions,
ADRs, definition of done and review checklist, and this repository's own decisions and
changelog rules. Read those first, then the rest of `README.md`, which also says how a
source is generated.

## Layout

```
copier.yml               questions and copier settings (subdirectory, skip-if-exists, envops)
template/                what gets generated; *.jinja files are rendered, others copied verbatim
  src/xippios/{{ package_dir }}/  the package (import_path as directories, sdk-core ADR-0006):
                         _client, errors, models, tasks, api/, mcp, http; params, enums and
                         reference/ where has_reference_data, tasks_write and mcp_write where
                         write_server, only their names conditional
  tests/                 conftest (plugin; the strip of every tenant but demo where tenant_param),
                         test_family (core's family check, one line), task replay tests, live smoke,
                         test_built_answers (core's check of a built answer's mark, one line,
                         then the source's READERS and ALLOWED; the source's once rendered)
  .claude/commands/      add-endpoint, record-fixture, refresh-upstream, release-prep,
                         refresh-reference-data where has_reference_data
  .claude/settings.json  what Claude Code may run in a source: its checks and local git
  CLAUDE.md.jinja        the facts and code rules of a generated repo; the source's once rendered
  README.md.jinja        a generated repo's README with its `## Documents`; the source's once rendered
  .github/workflows/{ci,publish}.yml, .pre-commit-config.yaml, .secrets.baseline, .python-version,
  LICENSE                copied from sdk-core, verbatim but for the deviations in Rules
  .github/workflows/live.yml.jinja   the nightly live workflow with --assert=plain, the one rendered
                         workflow (Rules)
  .github/workflows/conventions.yml, .github/workflows/adr-index.yml  the trigger files of
                         the organization's checks, one per check; verbatim, the template's
                         own (Rules)
  .github/PULL_REQUEST_TEMPLATE.md  the template's own, which links sdk-core's definition of done
  .github/CODEOWNERS.jinja  the paths that steer a generated repo, each owned by the human answer
  .github/workflows/{% if '.' in import_path or depends_on %}siblings.yml{% endif %},
  .github/{% if '.' in import_path or depends_on %}scripts{% endif %}/check-siblings.sh
                         the sibling proof of sdk-core ADR-0006 and sdk-core ADR-0021,
                         verbatim, only their names rendered (Rules)
  src/xippios/{{ package_dir }}/{% if has_files %}parse{% endif %}/__init__.py,
  tests/{% if has_files %}fixtures{% endif %}/files/README.md
                         the parsers' package and the samples' provenance table of a source
                         that parses files (sdk-core ADR-0020), skip-listed, only their names
                         conditional
  scripts/refresh_upstream.py.jinja  the snapshot script a source fills: its SNAPSHOT, which
                         core's frame, xippios.core.refresh, runs (/refresh-upstream)
  scripts/{% if has_reference_data %}refresh_reference.py{% endif %}.jinja  the reference
                         refresh a source fills (/refresh-reference-data)
  scripts/adr_index.py   writes and checks a source's ADR index; verbatim, this repository's file
  scripts/release_prepare.py, scripts/changelog_assemble.py  prepare a release (/release-prep)
                         and write its CHANGELOG section; verbatim, the organization's (Rules)
  docs/adr/README.md, docs/reports/README.md   a generated repo's decisions and reports, laid
                         out; verbatim, this repository's files
  docs/adr.md, docs/adr.json  the index of a render with no record yet; the source's once rendered
  tests/test_family.py   one line collecting xippios.core.testing.family
  changelog/README.md    a generated repo's changelog fragments; verbatim, the same in every source
  .gitattributes.jinja   docs/upstream/** -text, and tests/fixtures/files/** -text where has_files:
                         the snapshot and the samples stay byte for byte (CRLF, mixed endings)
scripts/prove.sh         generate sdk-example-api (--keyless: sdk-example; --keyless-nested:
                         sdk-example-files; --gateway: sdk-example-gov; --tenants:
                         sdk-example-tenants; --tenants-keyless: sdk-example-mail) from the working
                         tree with copier copy and run every check on it; -d key=value passes one
                         more answer (-d has_files=true)
scripts/adr_index.py     writes docs/adr.md and docs/adr.json from the records in docs/adr/; --check
                         fails while either is stale
tests/                   the template's tests: conftest.py renders each of the family's seven
                         variants once, helpers.py holds their answers and the tools a test runs on
                         a render, test_template.py checks the renders, ruff on the output, the
                         answers' rules and skip-if-exists behaviour, and a module of its own holds
                         each later concern: test_helpers, test_capture, test_reference_data,
                         test_client_answers, test_repository_files, test_core_adoption,
                         test_contract, test_citations, test_release_script
docs/adr/                this repository's design decisions, one NNNN-<slug>.md record each, laid
                         out in its README.md and cited as ADR-NNNN, sdk-core's as
                         `sdk-core ADR-NNNN`; ADR-0001 holds the answers of the package
                         contract's variants, write_server and tenant_param
docs/adr.md, docs/adr.json  their index, written by scripts/adr_index.py, never by hand
docs/reports/            dated reports, the evidence a decision cites, laid out in its README.md
CHANGELOG.md             template releases, each section assembled from changelog/ (Rules)
changelog/               the next release's entries, one fragment per change; README.md lays them out
pyproject.toml, uv.lock  the development tooling; version names the latest release (Releases)
.github/workflows/ci.yml       the template's own CI: tests and seven proofs
.github/workflows/conventions.yml, .github/workflows/adr-index.yml  the organization's
                         checks on this repository's own pull requests; byte for byte the
                         render's (Rules)
.github/workflows/release.yml  tags vX.Y.Z from the top CHANGELOG heading (Releases)
.claude/settings.json    what Claude Code may run here: the checks, the proofs and local git
```

## Rules

- Generated code must pass `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`
  and `pre-commit` out of the box. `scripts/prove.sh` is the proof, in the family's seven
  shapes: keyed and nested (no flag), keyless and flat (`--keyless`), keyless and nested
  (`--keyless-nested`), keyless and nested parsing files, with an empty `parse/`
  (`--keyless-nested -d has_files=true`), nested behind the api.data.gov gateway
  (`--gateway`), nested and multi-tenant with a write server, its tenants' keys sent as the
  basic user name (`--tenants`), and nested and multi-tenant with tenants that hold a
  refresh token, no key (`--tenants-keyless`). Every proof runs on core 0.4.1, the release
  `core_version` defaults to; 0.3.0 stays the first release with `xippios.core.data_gov`.
  CI runs all seven. Run them before every pull request and paste their tails into its
  description. `-d` adds an answer to a shape: `-d has_reference_data=false` proves a
  render without the reference scaffold, `-d api_key_location=basic
  -d rate_limit_provenance=below-documented` the client's answers.
  A dependent (`source_dependencies`) has no proof of its own, since a dependency that is
  not on PyPI cannot be installed; the template tests cover its render.
- The tests render each of the family's seven variants once per test run, by the fixtures
  of `tests/conftest.py` from the answers in `tests/helpers.py`: keyed nested, keyless
  flat, keyless nested, a dependent that parses files (keyless nested with
  `source_dependencies`, one open and one keyed, and `has_files`), one behind the
  api.data.gov gateway (`gateway`, which derives the key answers), a multi-tenant source
  with a write server whose tenants' keys go as the basic user name (`tenants`:
  `write_server`, `tenant_param`, `api_key_location: basic`) and one whose tenants hold a
  refresh token, no key (`tenants-keyless`: `tenant_credential_env`, `live_secrets`); a
  check no answer changes reads one render, and an answer outside the variants (a key
  location, a pace set under a documented limit, `has_reference_data: false`, a core pin,
  a name at its bound, an `import_path` override, a flat source with a dependency) is
  tested by its own rule. The tests assert mechanics, never rendered prose: a file
  rendered or not, a name present, no Jinja left, a digest equal, a script's behaviour.
  A new concern's tests take a module of their own beside `tests/test_template.py` and
  import what the modules share from `tests/helpers.py`.
- Files a source fills with its own content (`__init__.py`, `_client.py`, `errors.py`,
  `models.py`, `api/`, `parse/`, `tasks.py`, `tasks_write.py`, `params.py`, `enums.py`,
  `reference/`, `scripts/refresh_reference.py`, `scripts/refresh_upstream.py`,
  `tests/test_tasks.py`, `tests/test_live.py`, `tests/test_built_answers.py`,
  `tests/fixtures/`, `docs/upstream/`, `docs/adr.md`, `docs/adr.json`, `README.md`,
  `CHANGELOG.md`, `CLAUDE.md`) are listed in
  `_skip_if_exists` so `copier update` never overwrites them; copier renders the
  patterns, so those inside the package name `{{ package_dir }}`, never `**`, which would
  match a whole package named like a protected directory (`example-api`'s
  `xippios/example/api/`). They read as gitignore lines: `/README.md` is the root's alone,
  since `changelog/README.md` is every source's, and the two refresh scripts stand where
  `scripts/` would also protect `scripts/adr_index.py` and the two release scripts, the
  template's; a script of the source's own is never rendered, so no update touches it.
  Every other rendered file is the template's and updates with it, the commands under
  `.claude/commands/`, `scripts/adr_index.py`, `tests/conftest.py` and `tests/test_family.py`
  among them: keep in those only what every source shares. A line that depends on an
  answer, or that a source keeps its facts in, belongs in a file the source owns once
  rendered, `CLAUDE.md.jinja` or `README.md.jinja`.
  `scripts/adr_index.py` is the one version that the organization's repositories share, the
  same bytes here and in `template/scripts/`: it changes by that version's next one, never by
  an edit of a copy, the tests pin its digest, and the ruff of this repository and of a render
  leaves it alone while a render's mypy checks it. Every command runs it as `python3 -I`.
  `scripts/release_prepare.py` and the assembler it loads by its path,
  `scripts/changelog_assemble.py`, are the organization's one version too, rendered alone,
  with no copy at this repository's root: they change by that version's next one, never by
  an edit of a copy. The tests pin their blob ids and run the script on a render, the
  render's ruff leaves them alone, and its mypy checks them, taking a generic without
  arguments in `scripts/changelog_assemble.py` alone, where those bytes hold one.
  `/release-prep` runs `python3 -I scripts/release_prepare.py`, which sets the version in
  `uv.lock` with no `uv lock`.
  What every source shares and can be tested belongs in core's family check, not in a
  rendered test. A template-owned file the template removes is deleted by `copier update`,
  a source's own lines in it included: the CHANGELOG says where they move first. So is a
  file under `_skip_if_exists` the template stops rendering, where the repository's
  earlier render had it, `_skip_if_exists` notwithstanding (copier 9.19.1).
- Workflow files are copied verbatim (no `.jinja`) so GitHub's `${{ }}` never meets Jinja,
  with one exception: `live.yml.jinja` is rendered, because the secrets its pytest step
  reads are named by the answers, the keys first, `api_key_env`, or a multi-tenant
  source's reserved tenant's credential in its place, and the `key_env` of each
  `source_dependencies` entry (`key_envs`, a hidden answer), then each variable that
  `live_secrets` lists (`live_secret_names`, a hidden answer), and its start time comes
  from `live_schedule`, a hidden answer `copier.yml` computes from the slug. It writes
  GitHub's own expressions as `{{ '${{' }}` and `{{ '}}' }}`; `tests/test_template.py`
  checks that no Jinja survives, that the pytest step names each secret exactly once, in
  that order, that one with no key names no key, and that the step runs
  `uv run pytest -m live --tb=short --assert=plain`, so a failed assertion prints no value
  it compared, an upstream record among them, into a public log.
  `.github/workflows/conventions.yml` and `.github/workflows/adr-index.yml` are verbatim
  too and the template's own: the trigger files of the organization's checks, one per
  check, each named as the workflow of xippios/.github it calls at `@main` and written in
  the form that repository's README shows, with no comment. `conventions.yml` runs on a
  pull request's opening, push, reopening and edit, never on `labeled`, since GitHub
  reports a head's checks from its newest run, and on a push to `main` and a dispatch: its
  job `conventions` calls the review against the documents the README lists, which tells a
  release pull request by its own condition, and its job `range` the review of a range of
  commits. Each job's condition holds the event and the switch `WORKFLOW_CONVENTIONS`.
  `adr-index.yml` runs on the opening, a push and a reopening, and its one job, with no
  condition, calls the check of the ADR index, which reads its switch `WORKFLOW_ADR_INDEX`
  itself and runs the render's `scripts/adr_index.py --check`. The job ids name the checks
  the rulesets match, `conventions / conventions`, `adr-index / adr-index` and, on `main`,
  `range / range`. This repository runs the same two files, byte for byte, on its own pull
  requests, and the tests hold them equal.
  A variable `WORKFLOW_<NAME>`, `on` or `off`, switches a workflow: GitHub reads the
  repository's over the organization's and compares without case, so the workflow runs
  where neither is set. `live.yml` and `siblings.yml` hold theirs, `WORKFLOW_LIVE` and
  `WORKFLOW_SIBLINGS`, in their one job's condition, so on `off` the check reports as
  skipped and passes, as the ADR index does; the review on `off` reports no check, which a
  ruleset that requires it waits for. `ci.yml` and `publish.yml` hold none and always run. Every workflow takes
  its title by the organization's rule, `Live tests` and `Siblings` among them, and
  `publish.yml` its title `Publish` with core's bytes.
  Two verbatim files render only where the import path nests or the source declares a
  dependency, so only their names hold Jinja: `.github/workflows/siblings.yml` and the
  script it runs, `.github/scripts/check-siblings.sh` (executable; copier keeps the bit),
  the sibling proof of sdk-core ADR-0006, which installs and imports the declared
  dependencies too (sdk-core ADR-0021). They stay outside `_skip_if_exists`, so
  `copier update` keeps a source's copy equal to the render, and the name of the script's
  directory is the conditional one, so a flat render gets no empty directory.
  `siblings` is a visible job the ruleset does not require: `ci.yml` stays core's file.
- The files copied from sdk-core, `ci.yml`, `publish.yml`, `.pre-commit-config.yaml`,
  `.secrets.baseline`, `.python-version` and `LICENSE`, mirror sdk-core at the core release
  the template adopts, v0.4.1. The template carries neither core's caller of the retired
  gates nor core's pull-request template. `tests/test_template.py` pins `ci.yml` and
  `publish.yml` to core's bytes once the template's own lines below are taken out, and
  `tests/test_core_adoption.py` pins the other four to their digests at v0.4.1. When
  sdk-core changes one of them, change it here too and bump the template; `copier update`
  carries it into the generated repos. The map `SUPERSEDED` of `tests/test_citations.py`
  holds the records that sdk-core's index lists as superseded at the release the template
  adopts, which `SUPERSEDED_AT` names, and a test fails while `core_version`'s default
  names another, until the map follows that release's `docs/adr.md`. Two of the copies
  carry the exclusion of `.copier-answers.yml`, in the detect-secrets hook's `exclude` in
  `.pre-commit-config.yaml` and in `should_exclude_file` in `.secrets.baseline`, because
  the answers file names the key's variable and trips the keyword check on commit and on a
  baseline rescan alike; sdk-core carries the same exclusion since core 0.2.0.
  `publish.yml` deviates by one step: in its `tag` job, before the tag, it refuses a
  `pyproject.toml` that has `[tool.uv.sources]`, since a source that pins core to git
  cannot be published (conventions §12); core has no pin to guard. `ci.yml` deviates by
  `fetch-depth: 0` and the two steps after the checkout that read the pull request, the
  CHANGELOG entry and the fixture cap. The CHANGELOG step exempts Dependabot's pull
  request alone, so an adoption's, whose line conventions §15 item 9 requires, and a
  release's, which changes `CHANGELOG.md` itself, are read as any other; it takes a
  fragment the pull request adds or changes under `changelog/` as well as a change of
  `CHANGELOG.md`.
  `.github/PULL_REQUEST_TEMPLATE.md` is the template's own, no copy of core's: it links
  sdk-core's definition of done where core's copy repeats it, so it cannot lag, and the
  tests pin its sections.
- Commit subjects follow Conventional Commits: the rule binds a pull request's own commits,
  not the commit that lands the pull request on `main`, whose subject GitHub writes.
- Every PR that changes more than the documentation brings its `CHANGELOG.md` entry (Keep a
  Changelog) as a fragment, `changelog/<group>-<slug>.md` holding one bullet, as
  `changelog/README.md` lays it out; the release assembles the fragments into its section.
  A change to a generated file under `_skip_if_exists` adds a note under its bullet,
  `` - Hand-apply: `<path>` — <what> — <why>. ``, because `copier update` never touches
  those files once they exist; a change to several such files names each in its one
  note, an item per file on a line of its own, and a change that matters to new
  repositories only (a scaffold's starting text) says so in its bullet instead. Releases up to 0.3.2 end with
  a `### Hand-apply` list instead of the notes.
- Jinja renders with `trim_blocks` and `lstrip_blocks`, so a line holding only a block tag
  disappears, and a block tag at the end of a line takes that line's newline with it. A
  block tag therefore stands alone on its line or opens and closes there, before the
  line's end; the tests check every `.jinja` file for it. Mind blank lines in generated
  Python: the formatter check is strict.
- Keep `copier.yml` questions mechanical: every answer must come from the upstream
  documentation or the human, never be guessed; no URL and no rate limit is written from
  memory, and the README says where each answer's evidence goes.
- `detect-secrets` flags Jinja lines that mention `api_key_location` as if they held a
  key. Known false positives live in `.secrets.baseline`; after changing such a line, run
  `uv run detect-secrets scan --baseline .secrets.baseline` and commit the updated
  baseline. Never add a real value to silence it.

## Commands

```bash
uv sync                         # copier, pytest, ruff, pyyaml, detect-secrets, pathspec
uv run pytest                   # template tests (fast: generation + ruff on the output)
scripts/prove.sh                  # full proof against the xippios-core release on PyPI
scripts/prove.sh --keyless        # the same for a keyless flat source
scripts/prove.sh --keyless-nested # the same for a keyless nested source
scripts/prove.sh --keyless-nested -d has_files=true   # a keyless nested source that parses files
scripts/prove.sh --gateway        # the same for a nested source behind api.data.gov
scripts/prove.sh --tenants        # a multi-tenant source with a write server and basic auth
scripts/prove.sh --tenants-keyless  # one whose tenants hold a refresh token, no key
scripts/prove.sh -d has_reference_data=false   # a source that packages no reference data
scripts/prove.sh --core-ref main  # against sdk-core's main, before a core change is released
uv run ruff check . && uv run ruff format --check .
python3 -I scripts/adr_index.py --check   # this repository's ADR index matches its records
```

## Releases

- A generated repository records the template tag it was made from in
  `.copier-answers.yml`: `copier copy` takes the latest tag where no `--vcs-ref` names
  one, and core's family check fails a repository whose answers name no tag.
- Releases follow the release train (conventions §12, sdk-core ADR-0039 decision 6): a
  release assembles the fragments under `changelog/` into `## [X.Y.Z] - <date>` of
  `CHANGELOG.md`, as `changelog/README.md` lays it out, and deletes them. It sets
  `version` in `pyproject.toml` to `X.Y.Z`, locks again with `uv lock` and sets the
  README's `--vcs-ref` to `vX.Y.Z`, and changes no other file outside conventions §12's
  release subset: `CHANGELOG.md`, `pyproject.toml`, `uv.lock`, and `README.md` or
  `CLAUDE.md` where a sentence names the release. The section may gain a lead paragraph
  and says internal labels (decisions, rows, plan steps) in plain words, since it becomes
  the tag's message. `.github/workflows/release.yml` tags `vX.Y.Z` on the release's commit
  with that section as the message.
- The section of a release that adds a question to `copier.yml`, or a choice to one, ends
  with one list, as `changelog/README.md` lays it out: an item per source whose update
  passes an answer that the README's update command does not, a new question's answer
  other than its default or a new choice in place of the answer the source recorded among
  them, holding that update's command whole, with every `-d` argument it passes. An
  adoption copies its command from the list, never from the prose of an entry, and a
  source that the list leaves out runs the README's update command as it stands.
- The section of a release that brings a core release, by `core_version`'s default,
  carries, ready to adapt, the changelog entries that a source takes for the changes of that
  core release its callers see, from the list of those changes that sdk-core keeps for the
  adoption of that release, which the README names. One fragment of the release holds them,
  one entry per item of its Hand-apply note, as `changelog/README.md` lays it out: first the
  adoption's own, in the group and with the three versions of conventions §15 item 9, then,
  for each change of the list, every entry the list names for it, each in the group the
  list gives it, each item saying where its entry holds. An entry that the list names
  without a group takes the group of what it does to the source's callers, and the pull
  request of the fragment names that group in a decision. The pull request of a source that
  brings a change, its adoption's or a later one of its patch, copies the entry and words it
  for the source's own tasks. Core's list
  stays the one place of those changes, which core's review checklist holds an adoption
  against: where an entry and the list part, the list holds, and a wrong entry is corrected
  in its fragment before the template's release.
- Never push a tag by hand, and never touch a secret.
- Never read or print `.envrc`, `.env`, or any variable ending in `_API_KEY`, `_TOKEN` or
  `_SECRET` (conventions §7).
