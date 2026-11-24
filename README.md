# sdk-template

[Copier](https://copier.readthedocs.io/) template for `xippios-<source>` repositories,
the per-source packages of the [xippios SDK family](https://github.com/xippios). A
generated repository conforms to the family's
[conventions](https://github.com/xippios/sdk-core/blob/main/docs/conventions.md) and
[ADRs](https://github.com/xippios/sdk-core/blob/main/docs/adr.md) out of the box: the
three-layer layout, `xippios-core` client and models, MCP server and FastAPI router wired
to the task layer, test harness with the live-test gate and core's family check, CI with
the required `ci` check, the release train with trusted publishing, the organization's
checks of a pull request, pre-commit, `docs/adr/` with its index, changelog fragments,
and, for Claude Code, slash commands, a `CLAUDE.md` of the package's facts that imports its
layout, `docs/layout.md`, and the rules no change breaks, `.claude/rules/never.md`.
Its second shape, the general part of a repository, renders that repository around a
package of the family that wraps no API, without tasks and servers
([The general part of a repository](#the-general-part-of-a-repository), ADR-0003).
The documents a change of the template follows are listed under [Documents](#documents).

## Generating a source repository

A source repository is generated with copier from this template's GitHub URL, which copier
checks out at its latest tag, so `.copier-answers.yml` records a tag that `copier update`
can reach from any machine. Every answer of the [Questions](#questions) comes from the
upstream documentation or from the person who asks for the source, never from memory. The
base URL, the auth and the pace are no answers: the render's `_client.py` keeps a marked
place for each, a host that never resolves, no auth and a pace of 60 requests a minute,
and the repository's first pull request fills it as it fills `tasks.py`. No URL and no
rate limit is guessed there either: the pace, the burst and whether the pace is
documented, set under a documented limit or self-imposed come from the documentation or
from that person (sdk-core ADR-0033).
Each value that rests on upstream has its evidence, the page and section that states the
base URL, the key and the pace, or the person's word, and the status a status-only probe of
the host returned; it goes under the Assumptions of the repository's first pull request.
`core_version` stays at its default unless the person names another core release, and
`core_git_ref` is left out but to build against unreleased core.
A repository of the general shape is generated the same way with `-d shape=general`, its
slug, its `source_name`, where it is not named `sdk-<slug>` its `repository_name`, where its
package holds a key its `api_key_env`, and no answer of an upstream.

```bash
uvx --from 'copier>=9.19' copier copy --defaults \
  -d "source_slug=usda-nass" \
  -d "source_name=USDA NASS Quick Stats" \
  -d "upstream_url=https://quickstats.nass.usda.gov" \
  -d "upstream_docs_url=https://quickstats.nass.usda.gov/api" \
  -d "api_key_env=NASS_API_KEY" \
  https://github.com/xippios/sdk-template.git sdk-usda-nass
```

The render passes its checks before an endpoint is added; run them in it before anything
else, as `scripts/prove.sh` does for the template's proofs:

```bash
cd sdk-usda-nass
uv sync --all-extras
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
git init -q -b main && git add -A && uv run pre-commit run --all-files
```

A check that fails on the render is the template's fault: fix the template and generate
again, never the render by hand. On GitHub the repository takes the topics `xippios-sdk`,
`python`, `mcp` and one for the domain, such as `agriculture` (conventions §13). Before
its first release, PyPI needs a pending trusted publisher for the project, owner
`xippios`, the repository, workflow `publish.yml` and environment `pypi`, and the
repository needs the environment `pypi` with a required reviewer, who approves each
publishing run of `publish.yml`. Its nightly `live.yml` reads the key, or the bearer
token, from the secret that `api_key_env` names, and each variable `live_secrets` lists
from the secret of the same name. A key several sources share (sdk-core ADR-0032) is one
organization secret whose repository access takes the new repository, never set with
`gh secret set --repos`, which replaces the list.

## Questions

| Question | Meaning | Example |
| --- | --- | --- |
| `shape` | what the repository holds, a choice of two names (ADR-0003): `source`, the default, a source package with its client, tasks and servers; `general`, the general part of a repository alone, for a package of the family that wraps no API, which asks no question of a source but the key's and owns its `pyproject.toml` once rendered | `general` |
| `source_slug` | provider, plus API when one provider has several; names the repo, the distribution and the import | `usda-nass` |
| `repository_name` | the general shape's alone: the repository's name on GitHub, which the package's URLs and the trusted publisher of `/release-prep` take; default `sdk-<slug>`, the name every source's repository has | `xippios-example` |
| `source_name` | human name; at most 77 characters, so every generated Python line stays within 100 columns, and no `"` or `\`, which the generated Python quotes. In the general shape, the package's description in a few words, which `pyproject.toml`'s description and the first sentence of `README.md` and `CLAUDE.md` take at the first render | `USDA NASS Quick Stats` |
| `import_path` | import path under `xippios`; defaults to the slug with dots, so multi-API providers nest (sdk-core ADR-0006); override for a hyphenated single-API provider | `usda.nass` |
| `upstream_url` | a source's, as are the six questions after it but `api_key_env`, `core_version`, `core_git_ref` and `source_dependencies`: provider page, linked from the README | `https://quickstats.nass.usda.gov` |
| `upstream_docs_url` | where `/refresh-upstream` fetches the documentation from | `https://quickstats.nass.usda.gov/api` |
| `api_key_env` | environment variable with the key; empty for open APIs, and for a multi-tenant source whose tenants hold another credential. In the general shape, the key that the package holds, such as the key of a gateway that its sources share, which renders `_client.py` (ADR-0003); empty, the default, for a package that holds none | `NASS_API_KEY` |
| `write_server` | whether the source writes to the upstream through a server of its own (conventions §8): `true` renders `mcp_write.py`, which serves `tasks_write.__all__` as confirm-gated tools, the `tasks_write.py` scaffold, the source's once rendered, and the entry points `xippios-<slug>-mcp-read` and `xippios-<slug>-mcp-write` in place of `xippios-<slug>-mcp`, with no alias for the old name; default `false` | `true` |
| `tenant_param` | the task parameter that names a tenant, for a multi-tenant source whose upstream serves each tenant under a credential of its own (conventions §7): it renders core's `Tenants` registry in `_client.py`, a client per tenant with its key in `<PREFIX>_<NAME>_API_KEY`, the prefix `api_key_env`'s without `_API_KEY`, the tenants listed in `<PREFIX>_<PARAM>S` and the reserved tenant `demo`, whose key the offline tests and `live.yml` take in place of `api_key_env`; the tenant list task, `build(lock)` and core's `main` with the registry in the servers, whose `--<param>` binds a server to one tenant, and `keep_reserved_tenants` in `tests/conftest.py`. A source whose tenants hold another credential, a refresh token say, answers no key and names that credential's variables in `live_secrets`, the reserved tenant's first, and its own `_client.py` reads them (ADR-0002). At most 20 characters, so every generated Python line stays within 100 columns; default empty, one tenant | `org` |
| `core_version` | the xippios-core release depended on, `X.Y.Z`, rendered as the bound `xippios-core~=X.Y.Z`, the extras likewise: one core minor, `Z` 0 unless patch `Z` shipped what the source adopts (conventions §12, sdk-core ADR-0039 decision 1); default `0.5.0`, the release the template adopts, rendered `~=0.5.0`; in the general shape at the first render alone, since `pyproject.toml` is then the repository's | `0.5.0` |
| `core_git_ref` | development only: depend on sdk-core at `main` or at the full 40-character SHA of a commit on `main` for an unreleased core change (anything else is refused); empty, the default, for no pin; a release carries none, since `/release-prep` removes it first, in a PR of its own; in the general shape at the first render alone, and the repository removes the pin from its own `pyproject.toml` | `main` |
| `source_dependencies` | the source packages this one uses the task layer of (sdk-core ADR-0021; one level, no cycles), a YAML flow list in a string, `{name: <slug>, minor: "X.Y", key_env: <VAR or "">}` per package: rendered as the bound `xippios-<slug>~=X.Y.0` in `pyproject.toml`, its key variable set to the placeholder in offline tests and passed to `live.yml` from its org secret, the package installed and imported beside the wheel by the sibling check; default `[]`, none. A string, so `.copier-answers.yml` records it on one line, `'[]'` at the default | `[{name: usda-esmis, minor: "0.1", key_env: ""}]` |
| `live_secrets` | the variables the live tests read beyond the keys, such as a username and a password, a YAML flow list of UPPER_SNAKE_CASE names in a string: `live.yml` passes each one to its pytest step from the secret of the same name, after the keys, and a multi-tenant source without a key names its tenants' credential here, the reserved tenant's first, each in `_client.py`'s `ENV_VARS` too, since its own auth reads them, so core's plugin sets them in every test not marked live; each name once, never a key (`api_key_env`'s or a dependency's `key_env`), `XIPPIOS_LIVE_TESTS` or a name with GitHub's `GITHUB_` prefix; default `[]`, none, recorded on one line | `[FAOSTAT_USERNAME, FAOSTAT_PASSWORD]` |
| `has_files` | whether the source parses the files it downloads (sdk-core ADR-0020): `true` renders `parse/`, one module per file kind, and `tests/fixtures/files/README.md`, one provenance row per sample file its parser tests read, both the source's once rendered, and a line of `.gitattributes` that keeps the samples byte for byte; a retrieval-only source, which lists releases and downloads files without parsing them, answers `false`, its download fixture the recorded exchange of the file's URL (sdk-core ADR-0040 decision 5); default `false` | `true` |
| `has_reference_data` | whether the source packages reference data, the code lists and tables upstream publishes for every caller alike (conventions §3): `true` renders the scaffold, `params.py`, `enums.py`, `reference/`, `scripts/refresh_reference.py` and `/refresh-reference-data`, whether or not a list is packaged yet; a source that packages none answers `false`, which renders none of it: an update with that answer deletes the files the template rendered, the source's lines in them included, leaves a file the source added under `reference/` for the source to delete, and brings none of the scaffold back; a multi-tenant source answers `false`, since the scaffold's refresh fetches through the one client of a source with one tenant; default `true`, which a source that predates the question takes on update | `false` |

## What gets generated

```
sdk-<slug>/
  src/xippios/<import path as directories>/   the package; each level above it a namespace
    __init__.py        the public surface: __version__ and the re-exported task functions
    py.typed           the PEP 561 marker, which a caller's mypy --strict needs
    _version.py        __version__ from the distribution's metadata
    _client.py         the configured AsyncClient with its base URL, auth and pace, ENV_VARS,
                       and classify, upstream's documented error shapes; where tenant_param,
                       the tenants' registry TENANTS, a client per tenant by client_for
    errors.py          the package's own error classes, where conventions §5 calls for one
    models.py          pydantic models of upstream's payloads (UpstreamModel), and a value set
                       written by hand that no packaged list renders
    api/__init__.py    the endpoint wrappers, one module per upstream operation (conventions §2)
    parse/__init__.py  where has_files: the file parsers, one module per file kind
    tasks.py           the task functions: __all__ is what the adapters serve, BULK_TASKS the
                       Python-only ones, MCP_INSTRUCTIONS the server's text, MCP_CAPS the
                       per-tool result caps
    mcp.py             the MCP server's entry point: build() the tool set core builds from
                       tasks.py, server, run(), core's main; no line of the source's
    http.py            the FastAPI router over the same tasks
    tasks_write.py     where write_server: the write tasks, each confirm-gated, and the write
                       server's MCP_INSTRUCTIONS
    mcp_write.py       where write_server: the write server's entry point, mcp.py then the
                       read server's
    params.py          where has_reference_data: the packaged lists, read from the files
    enums.py           where has_reference_data: StrEnums generated from those lists
    reference/README.md  where has_reference_data: the lists' files and their provenance
  tests/
    conftest.py        enables core's plugin, which keeps a run offline; where tenant_param,
                       the strip of every tenant but the reserved one
    test_family.py     core's family check, one line
    test_built_answers.py  core's check of a built answer's mark, one line
    test_tasks.py      the replay test of each task, from its recorded fixtures
    test_live.py       the live smoke test of each task, marked live
    fixtures/files/README.md  where has_files: the samples' provenance table
  scripts/
    refresh_upstream.py    declares SNAPSHOT, the source's pages, which core's frame
                           xippios.core.refresh fetches into docs/upstream/ (/refresh-upstream)
    refresh_reference.py   where has_reference_data: declares LISTS, core's Lists, which
                           core's frame fetches through api/ into the packaged lists and
                           their StrEnums
    adr_index.py           writes docs/adr.md and docs/adr.json from the records; --check
    release_prepare.py     prepares a release (/release-prep): its CHANGELOG section and the
                           version in pyproject.toml and uv.lock
    changelog_assemble.py  writes a release's CHANGELOG section from changelog/ and removes
                           the fragments; --notes prints the next section and writes nothing
  docs/upstream/       FETCHED.md, the list of the snapshot that core's frame writes
  docs/adr/README.md   the decision records, laid out; docs/adr.md and docs/adr.json, their
                       index, which scripts/adr_index.py writes
  docs/reports/README.md  the dated reports a decision cites, laid out
  docs/layout.md       the source's own: what it adds to this tree, which CLAUDE.md imports
  .claude/commands/    add-endpoint, record-fixture, refresh-upstream, release-prep,
                       refresh-reference-data where has_reference_data
  .claude/rules/never.md  the rules no change breaks, which Claude Code loads by its place
  .claude/settings.json   what Claude Code may run in the repository: its checks and local git
  .github/workflows/   ci.yml, publish.yml, live.yml, conventions.yml and adr-index.yml;
                       siblings.yml where the import path nests or the source declares a
                       dependency, with .github/scripts/check-siblings.sh, which it runs
  .github/PULL_REQUEST_TEMPLATE.md
  .github/CODEOWNERS   the paths that steer the repository, each owned by the human, jdidaskalu
  CLAUDE.md            what the package wraps, its commands and what only it knows
  README.md  CHANGELOG.md  LICENSE  pyproject.toml  .copier-answers.yml  .python-version
  .pre-commit-config.yaml  .secrets.baseline
  changelog/README.md  the changelog fragments: one file per change, assembled at the release
  .gitattributes       docs/upstream/** -text, and tests/fixtures/files/** -text where has_files,
                       so upstream files and the samples keep their bytes and line endings
  .gitignore           caches, builds, local env files, copier's leftovers and .local/, the
                       operator's own files
```

The commands under `.claude/commands/` keep the steps of the work on a source and the paths
that the answers render, and cite for each mechanism the section of sdk-core's conventions
and the name of xippios-core that serves it, restating neither, so that a rule of the family
stands once, in core's documents. `/record-fixture` records through core's recorder, and a
source with a recorder of its own, `scripts/record_fixture.py`, records with that.

The generated repository passes `ruff`, `mypy --strict`, `pytest` and `pre-commit`
before any endpoint is added. `tests/test_family.py`, one line, collects core's family
check, which then keeps the layout, the adapters, the task shapes, the README status
table, the template tag and the core bound honest as tasks are added.
`tests/test_built_answers.py` collects core's check of a built answer's mark the same way,
by its one line, and fails a place of the source's tests that builds an answer without
naming its kind of conventions §10 (sdk-core ADR-0064); it is the source's once rendered.
`mcp.py` carries the package contract by which a host serves a source (conventions §8,
sdk-core ADR-0063): `build()` returns the `ToolSet` that core builds from `tasks.py`,
whose `MCP_INSTRUCTIONS`, `MCP_CAPS` and option hooks it reads, `server` is
`build_server(build())`, `run()` calls core's one `main`, and `ENV_VARS`, which
`_client.py` declares from the key answers and `live_secrets` and which core's plugin
reads, stands beside `SOURCE`. No line of `mcp.py` or `mcp_write.py` is a source's: what a
source's server declares stands in its tasks module (ADR-0002). A generated package is read-only unless `write_server` answers `true`,
and serves one tenant unless `tenant_param` names its parameter. `ci.yml` also requires a
CHANGELOG entry on every pull request but Dependabot's, an adoption's (conventions §15
item 9) and a release's included, which changes `CHANGELOG.md` itself, as a fragment
under `changelog/` or a line in `CHANGELOG.md`, and fails on a fixture file over 256 KiB;
`publish.yml` is the release train. The organization's checks start from one trigger
file each, named as the workflow of xippios/.github it calls: `conventions.yml` runs the
review of a pull request against the documents the README lists, the check
`conventions / conventions`, and on a push to `main` the review of a range,
`range / range`, and `adr-index.yml` the check `adr-index / adr-index`, which runs the
render's `scripts/adr_index.py --check`. `live.yml`, the one workflow whose text the
answers render, runs every `live` test against the upstream every night and on demand,
never on a pull request, with `--tb=short --assert=plain`, so its public log holds neither a
failing test's frame arguments nor the values a failed assertion compared. Its start time derives from the slug, between 01:00 and 05:59 UTC, so sources that
share a key do not start together; only its pytest step sees the keys, from the org
secrets named by `api_key_env`, or a multi-tenant source's reserved tenant's key in
its place, and by `source_dependencies`' `key_env`, and the other variables `live_secrets`
names, each from the secret of the same name, so the checkout, setup-uv and `uv sync` see
none. Where the import
path nests or the source declares a dependency, `siblings.yml` runs
`.github/scripts/check-siblings.sh` on every pull request and push to `main`, handing it
the job's read-only token for the listing of the organization's repositories, since GitHub
limits the calls of a runner without one: it installs
the wheel beside every sibling on PyPI under the same provider namespace that shares its
core minor and beside the source packages it depends on, at their bound, and proves the
namespace levels stay portions (sdk-core ADR-0006, sdk-core ADR-0021), a visible check the
ruleset does not require; a declared dependency on another core minor fails it. It is a
workflow of its own beside `ci.yml`, never a job there, since `ci.yml` is core's file,
which `publish.yml` calls for a release, and a job there would tie the package's releases
to its siblings. Both workflows are hardened as every workflow of the family
(conventions §13): their actions pinned to the commits `ci.yml` pins, the checkout keeping
no credentials, the token reading only, and neither file carries a comment but the version
after a pinned action. A sibling
that depends on the source and pins its previous minor is left out with a warning that
names the pin, since it takes the new minor in its own adoption (conventions §12), so the
release of a minor stays green; one that pins another minor of the source fails it.
A variable `WORKFLOW_<NAME>` of `off`, the repository's over the organization's, switches
off `live.yml` by `WORKFLOW_LIVE`, `siblings.yml` by `WORKFLOW_SIBLINGS` and the two
checks by `WORKFLOW_CONVENTIONS` and `WORKFLOW_ADR_INDEX`, and a workflow runs where
neither sets one; `ci.yml` and `publish.yml` take no switch and always run. The
render's README says the same of each workflow the render holds, one paragraph each under
`## Workflows`: what it checks, when it runs, what the calling file hands over and what
switches it.
`scripts/refresh_upstream.py`, the capture script `/refresh-upstream` runs, declares the
source's `Snapshot` as `SNAPSHOT`, which xippios-core's frame `xippios.core.refresh` runs
(sdk-core ADR-0062), and no check of core reads it without a request; the frame refuses to
run it until the source names its pages, and its first run writes `docs/upstream/FETCHED.md` whole, where the
render's stub holds its title and one paragraph. The scaffold declares no `reduce`, so
core's default keeps each page as fetched until the source adds its converter.

### The general part of a repository

`-d shape=general` renders the general part of a repository alone, for a package of the
family that wraps no API, a publisher's shared package or a host of the sources (ADR-0003).
Of the tree above it renders `ci.yml`, `publish.yml`, `conventions.yml`, `adr-index.yml`,
and `siblings.yml` with `check-siblings.sh` where the import path nests or the package
declares a dependency; the changelog's files with `release_prepare.py` and
`changelog_assemble.py`; the decision records' files with `adr_index.py`; `/release-prep`,
the Never file, `.claude/settings.json`, `docs/layout.md`, `CLAUDE.md`, `README.md`,
`CHANGELOG.md`, `pyproject.toml`, `.copier-answers.yml` and the repository's small files;
and the package's `__init__.py`, `_version.py` and `py.typed`, with `tests/conftest.py`,
which enables core's plugin. One file renders in this shape alone, `test_package.py`, the
repository's own test under `_skip_if_exists`, which imports the package and compares its
version with its distribution's. Where the package holds a key, which `api_key_env` names,
the render keeps `_client.py`, the package's under `_skip_if_exists` as a source's is: it
declares `ENV_VARS` with the key, the keys of the packages it depends on after it, and
holds no client, configuration, pace or auth, and the package fills it with the code that
reads the key; a package that holds none renders no `_client.py` (ADR-0003). It renders
none of a source's 26 other files, which the list `_exclude` of `copier.yml` names with
`_client.py`: no model, task, server, router, reference scaffold, snapshot, fixture, live
workflow, `.gitattributes`, and none of the commands that add an endpoint, record a fixture
or refresh. A nested render holds 35 files, a flat one 33, and one more where the package
holds a key.
Its `pyproject.toml` declares the family's tables with the `testing` extra alone and no
entry point, and is the repository's once rendered, so the package keeps its own
dependencies, extras and scripts there and raises its core bound by hand. Its
`/release-prep` takes no pin out by an update, cites no live run and no refresh, and its
`README.md` and `CLAUDE.md` hold no section on tasks, servers or upstream terms. The
package's URLs, the documents' links and the trusted publisher name the repository by
`repository_name`.

## Updating generated repositories

A template release, and the xippios-core minor it carries, reach a generated repository
in one adoption PR before its next release (conventions §15, sdk-core ADR-0039), taken with
`copier update` run inside the generated repository:

```bash
uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.4.1 -d core_version=0.4.1 -d core_git_ref=
git diff                             # review; resolve conflicts
```

The template needs copier 9.19.0 or later (`_min_copier_version`), the release its tests
and proofs run on; `--from 'copier>=9.19'` keeps a stale tool cache from refusing it.
Answers are read from `.copier-answers.yml`; pass `-d key=value` to change one, as above
to raise the core minor and drop a core pin (`--vcs-ref=:current:` changes the answers
without moving the template). From 0.4.1 on, a release that adds a question or a choice
ends its section of [CHANGELOG.md](CHANGELOG.md) with `### Answers each source passes`, the whole update
command of each source that passes an answer the command above does not, and such a
source copies its command from there. From 0.4.1 on too, a release that brings a core
release carries, in the Hand-apply note of an entry of its own, the changelog entries for
the changes of that core release that a source's callers see, from the list of sdk-core's
`docs/handover.md`, and the pull request that brings each change copies the entry that
holds for it. Files listed under `_skip_if_exists` in `copier.yml` (the
package `__init__.py`, the client, the package's errors, models, endpoint wrappers, the
file parsers, the task layer and its write tasks, the packaged lists and enums, reference data, the two
refresh scripts, the conftest, the task, live and built-answer tests and the fixtures, upstream
snapshot, the ADR index, the layout, the secrets baseline, README, CHANGELOG and CLAUDE.md, and
in the general shape its package test and `pyproject.toml`) are never
overwritten once they exist, so a template fix to one of them does not reach existing repositories by itself; one the
template stops rendering, though, is deleted by the update where the repository's earlier
render had it, the source's content included.
[CHANGELOG.md](CHANGELOG.md) lists those fixes per release, path, change and reason, in a
**Hand-apply** list at the section's end or, from 0.3.3, in a `Hand-apply:` note under
the change's bullet; port each one by hand in the same PR. A new file under those
patterns is created by the update where the repository has none of that name. Every other
file is the template's: the commands under `.claude/commands/`, the rules of
`.claude/rules/never.md`, `scripts/adr_index.py` and `tests/test_family.py` among them are
re-rendered, and a source's own lines in them are
merged three ways, conflicts marked. From 0.5.0 on `tests/conftest.py` and
`.secrets.baseline` are the source's, so an update merges no line of the template's into
the lines a source holds there, and a later change of core's baseline or of the plugin's
line reaches a source by a Hand-apply note. A repository of the general shape records
`shape: general`, and every source records `shape: source`, the default, at its update. From 0.5.0 on, too, the update writes
`.claude/rules/never.md` at every release and creates `docs/layout.md` where the repository
has none, which the source then fills by hand. `pyproject.toml` is one: a
script the package adds goes under `[project.scripts]` after the servers' entry points, as
the comment there says, and the update keeps it while the template's lines beside it stay;
a change of `write_server`, which renames them, marks it as a conflict. In the general
shape it is the repository's, so the update never writes it. A template-owned
file a release removes is deleted by the update, a source's own lines in it included, so the
release's CHANGELOG says where they move first.

Before its update a source checks two things on its `main`. First, its own lines in the
template's files, against a render of the tag it records with the answers it records. In a
clean checkout, `copier recopy` renders that tag over every file but those under
`_skip_if_exists`, so `git diff` shows each such line as its removal:

```bash
uvx --from 'copier>=9.19' copier recopy --defaults --overwrite --vcs-ref=:current:
git diff                             # the source's own lines in the template's files
git checkout -- .
```

The update carries such a line into the new render silently where the release leaves its
place alone, and as a conflict where it changes it; a line every source shares belongs in
the template, and one of the source's own in a file it fills. Second, its answers in
`.copier-answers.yml`, which the update keeps as they stand, a wrong one included:
`has_files` is `true` for a source that parses the files it downloads, and one that answers
`false` lacks, among others, the file sample's item of `/add-endpoint`; `has_reference_data`
is `false` for a source that packages no reference data, so no update brings the scaffold
back, and `true` for one that does, since an update with `false` deletes the files the
template rendered, the source's lines in them included, and leaves a file the source added
under `reference/` for the source to delete. A wrong answer
changes in a pull request of its own, before the update, with `uvx --from 'copier>=9.19'
copier update --defaults --vcs-ref=:current: -d has_files=true`, which renders the
template's files again; the files the source fills, `CLAUDE.md` among them, take the
answer's lines by hand in the same pull request, as a render with the new answer has them.

## Developing the template

```bash
uv sync
uv run pytest           # renders the family's five variants and the general shape's two once each, and checks them
scripts/prove.sh --all  # every shape below, one proof each, as CI runs them; fails where one fails
scripts/prove.sh        # full proof: copier copy, uv sync, ruff, mypy, pytest, pre-commit, on
                        # the commit of core 0.5.0's candidate that --core-ref names until 0.5.0 is on PyPI
scripts/prove.sh --core-ref main   # against sdk-core's main, --all --core-ref main for every shape
scripts/prove.sh --core-ref ""     # against the core release on PyPI
scripts/prove.sh --keyless         # a keyless flat source instead of the keyed nested one
scripts/prove.sh --keyless-nested  # a keyless nested source
scripts/prove.sh --keyless-nested -d has_files=true   # one that parses files
scripts/prove.sh --tenants         # a nested multi-tenant source with a write server and a key per tenant
scripts/prove.sh --general         # the general shape: a publisher's shared package, nested
scripts/prove.sh --general-flat    # the general shape, flat, in a repository not named sdk-<slug>
scripts/prove.sh -d has_reference_data=false   # a source that packages no reference data
```

A pull request of the template runs `.github/workflows/ci.yml`, whose one job `ci` is the
check the organization's ruleset requires: it runs the tests, then `scripts/prove.sh
--all`, which proves each shape of the list `shapes` in that script, every shape above but
the one of `-d has_reference_data=false`, each in a process of its own, goes on after one
that failed and fails where one fails, so a failing proof blocks the merge. A shape added
or removed changes that list and the script, never the workflow. It also runs
`.github/workflows/conventions.yml` and `.github/workflows/adr-index.yml`,
byte for byte the files it renders into a source: the organization's conventions review,
which reads a release pull request against the documents listed under
[Documents](#documents), and the check of the ADR index.

## Releasing the template

Every change brings its CHANGELOG entry as a fragment under `changelog/`, one file per
change, as [changelog/README.md](changelog/README.md) lays it out. The template follows
the release train (conventions §12): a release PR assembles the fragments and what
`## [Unreleased]` holds into `## [X.Y.Z] - <date>` in `CHANGELOG.md`, the section perhaps
with a lead paragraph and its internal labels put into plain words, deletes the
fragments, and changes no other file outside conventions §12's release subset. It also
sets `version` in `pyproject.toml` to `X.Y.Z` and locks again with `uv lock`, which CI's
`uv sync --locked` checks, and sets the update command's `--vcs-ref` above to `vX.Y.Z`.
No package is built from the manifest, but it names the template's latest release, and
`tests/test_template.py` holds it to the top release heading of `CHANGELOG.md`.

The template publishes nothing to PyPI, so its release is the tag (conventions §12,
sdk-core ADR-0039 decision 6). The release PR's merge on `main` runs
`.github/workflows/release.yml`, which reads the top `## [X.Y.Z] - ` heading of
`CHANGELOG.md` and, where `vX.Y.Z` has no tag yet, tags the merge commit with that
section as the tag's message. Every other push to `main` finds the top heading tagged and
ends quietly. Nobody pushes the tag by hand. Generated repositories record the tag in
`.copier-answers.yml`, `copier copy` takes it as the latest, and `copier update` reaches
it. The run's job `tag` holds the one checkout of the repository without
`persist-credentials: false`, since it pushes the tag with the job's token
(conventions §13). A run that fails before its tag push is finished with GitHub's
"Re-run failed jobs", and a run started again once the tag exists ends quietly. The runs
are not serialised, since a concurrency group keeps one pending run and cancels it for the
next, which would tag its own commit. So two pushes to `main` close together can both find the
version untagged: the second run's tag push then fails red, or, where it runs first, it
tags the later commit, and the maintainer deletes that tag before a source adopts it and
runs the release again with "Re-run all jobs". A release is therefore not merged while
another push to `main` is in flight, which keeps two runs from racing.

## Documents

- sdk-core: [docs/conventions.md](https://github.com/xippios/sdk-core/blob/main/docs/conventions.md) — the conventions every xippios source package follows, which a generated repository satisfies out of the box.
- sdk-core: [docs/adr.md](https://github.com/xippios/sdk-core/blob/main/docs/adr.md) — the index of the family's architecture decisions, which the conventions and this template cite.
- sdk-core: [docs/definition-of-done.md](https://github.com/xippios/sdk-core/blob/main/docs/definition-of-done.md) — what a change satisfies before its pull request is opened.
- sdk-core: [docs/review-checklist.md](https://github.com/xippios/sdk-core/blob/main/docs/review-checklist.md) — what the review of a pull request checks, in order.
- sdk-template: [docs/adr.md](https://github.com/xippios/sdk-template/blob/main/docs/adr.md) — the index of this template's own decisions, generated from the records in `docs/adr/`.
- sdk-template: [changelog/README.md](https://github.com/xippios/sdk-template/blob/main/changelog/README.md) — how a change writes its changelog entry as a fragment, its Hand-apply note included, and how a release assembles the fragments.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
