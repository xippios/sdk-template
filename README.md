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
and, for Claude Code, slash commands and a `CLAUDE.md` of the package's facts and rules.
The documents a change of the template follows are listed under [Documents](#documents).

## Generating a source repository

A source repository is generated with copier from this template's GitHub URL, which copier
checks out at its latest tag, so `.copier-answers.yml` records a tag that `copier update`
can reach from any machine. Every answer of the [Questions](#questions) comes from the
upstream documentation or from the person who asks for the source, never from memory: no
URL and no rate limit is guessed, and the pace, the burst and whether the pace is
documented or self-imposed come from the documentation or from that person (ADR-0010).
Each answer that rests on upstream has its evidence, the page and section that states the
base URL, the key and the pace, or the person's word, and the status a status-only probe of
the host returned; it goes under the Assumptions of the repository's first pull request.
`core_version` stays at its default unless the person names another core release, and
`core_git_ref` is left out but to build against unreleased core.

```bash
uvx --from 'copier>=9.19' copier copy --defaults \
  -d "source_slug=usda-nass" \
  -d "source_name=USDA NASS Quick Stats" \
  -d "upstream_url=https://quickstats.nass.usda.gov" \
  -d "upstream_docs_url=https://quickstats.nass.usda.gov/api" \
  -d "api_base_url=https://quickstats.nass.usda.gov/api" \
  -d "api_key_env=NASS_API_KEY" -d "api_key_location=query" -d "api_key_name=key" \
  -d "rate_limit_per_minute=30" -d "rate_limit_provenance=self-imposed" \
  https://github.com/xippios/sdk-template.git sdk-usda-nass
```

A source behind the api.data.gov gateway passes `-d "gateway=api.data.gov"` instead of
the three key answers, which the gateway answer derives. The render passes its checks
before an endpoint is added; run them in it before anything else, as `scripts/prove.sh`
does for the template's proofs:

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
from the secret of the same name. A key several sources share (ADR-0009) is one
organization secret whose repository access takes the new repository, never set with
`gh secret set --repos`, which replaces the list.

## Questions

| Question | Meaning | Example |
| --- | --- | --- |
| `source_slug` | provider, plus API when one provider has several; names the repo, the distribution and the import | `usda-nass` |
| `source_name` | human name; at most 77 characters, so every generated Python line stays within 100 columns, and no `"` or `\`, which the generated Python quotes | `USDA NASS Quick Stats` |
| `import_path` | import path under `xippios`; defaults to the slug with dots, so multi-API providers nest (ADR-0006); override for a hyphenated single-API provider | `usda.nass` |
| `upstream_url` | provider page, linked from the README | `https://quickstats.nass.usda.gov` |
| `upstream_docs_url` | where `/refresh-upstream` fetches the documentation from | `https://quickstats.nass.usda.gov/api` |
| `api_base_url` | base URL request paths join onto; required, usually not the provider page | `https://quickstats.nass.usda.gov/api` |
| `gateway` | the shared gateway the API sits behind: `api.data.gov` for an API it fronts, whose key, documented error answers and hourly quota the generated client takes from `xippios.core.data_gov`'s `Gateway` (ADR-0009), so `core_version` is 0.3.0 or later; then the three key answers below are derived, `DATA_GOV_API_KEY` in the `X-Api-Key` header, never asked, and recorded as if answered; default `none` | `none` |
| `api_key_env` | environment variable with the key; empty for open APIs; behind a gateway, the gateway's | `NASS_API_KEY` |
| `api_key_location` | `query`, `header` or `bearer`; behind a gateway, the gateway's | `query` |
| `api_key_name` | query parameter or header name; behind a gateway, the gateway's | `key` |
| `rate_limit_per_minute` | the pace, enforced client-side: upstream's documented per-minute (or per-second × 60) limit, or a self-imposed pace where upstream documents neither, an hourly or daily quota notwithstanding (ADR-0010) | `30` |
| `rate_limit_burst` | requests let through at once before the pace applies; `1` unless upstream documents a burst | `1` |
| `rate_limit_provenance` | `documented` or `self-imposed` (upstream documents no per-second or per-minute limit): where the pace comes from, named in the generated CLAUDE.md | `self-imposed` |
| `core_version` | the xippios-core release depended on, `X.Y.Z`, rendered as the bound `xippios-core~=X.Y.Z`, the extras likewise: one core minor, `Z` 0 unless patch `Z` shipped what the source adopts (conventions §12, ADR-0018 amendment (c)); default `0.3.0`, the release the template adopts, rendered `~=0.3.0` | `0.3.0` |
| `core_git_ref` | development only: depend on sdk-core at `main` or at the full 40-character SHA of a commit on `main` for an unreleased core change (anything else is refused); empty, the default, for no pin; a release carries none, since `/release-prep` removes it first, in a PR of its own | `main` |
| `source_dependencies` | the source packages this one uses the task layer of (ADR-0021; one level, no cycles), a YAML flow list in a string, `{name: <slug>, minor: "X.Y", key_env: <VAR or "">}` per package: rendered as the bound `xippios-<slug>~=X.Y.0` in `pyproject.toml`, its key variable set to the placeholder in offline tests and passed to `live.yml` from its org secret, the package installed and imported beside the wheel by the sibling check; default `[]`, none. A string, so `.copier-answers.yml` records it on one line, `'[]'` at the default | `[{name: usda-esmis, minor: "0.1", key_env: ""}]` |
| `live_secrets` | the variables the live tests read beyond the keys, such as a username and a password, a YAML flow list of UPPER_SNAKE_CASE names in a string: `live.yml` passes each one to its pytest step from the secret of the same name, after the keys; each name once, never a key (`api_key_env`'s or a dependency's `key_env`), `XIPPIOS_LIVE_TESTS` or a name with GitHub's `GITHUB_` prefix; default `[]`, none, recorded on one line | `[FAOSTAT_USERNAME, FAOSTAT_PASSWORD]` |
| `has_files` | whether the source parses the files it downloads (ADR-0020): `true` renders `parse/`, one module per file kind, and `tests/fixtures/files/README.md`, one provenance row per sample file its parser tests read, both the source's once rendered; a retrieval-only source, which lists releases and downloads files without parsing them, answers `false`, its download fixture the recorded exchange of the file's URL (ADR-0019 decision 5); default `false` | `true` |
| `human` | the GitHub login of the human, without the `@`. `.github/CODEOWNERS` names it as the owner of the paths that steer the repository, `.github/`, `CLAUDE.md`, `.claude/`, `rules/`, `pyproject.toml` and `.copier-answers.yml`, so a change to one waits for that human's review. Default `jdidaskalu`, a literal, which a source that predates the question takes on update | `jdidaskalu` |

## What gets generated

```
sdk-<slug>/
  src/xippios/<import path as dirs>/   __init__, py.typed, _version, _client, errors, models,
                       tasks, api/, mcp, http, reference/; parse/ where has_files
  tests/               conftest, test_family, test_tasks, test_live; fixtures/files/README.md,
                       the samples' provenance table, where has_files
  scripts/             refresh_reference.py, refresh_upstream.py (the capture skeleton),
                       adr_index.py (writes and checks the ADR index)
  docs/upstream/       FETCHED.md
  docs/adr/            README.md: the decision records; docs/adr.md and docs/adr.json, their index
  docs/reports/        README.md: the dated reports a decision cites
  .claude/commands/    add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep
  .claude/settings.json  .github/workflows/{ci,publish,live,organization}.yml
  .github/PULL_REQUEST_TEMPLATE.md
  .github/CODEOWNERS   the paths that steer the repository, each owned by the human answer
  CLAUDE.md  README.md  CHANGELOG.md  LICENSE  pyproject.toml  .pre-commit-config.yaml  .secrets.baseline
  changelog/README.md  the changelog fragments: one file per change, assembled at the release
  .gitattributes       docs/upstream/** -text, so upstream files keep their bytes and line endings
  .github/workflows/siblings.yml  .github/scripts/check-siblings.sh   where the import path nests
                       or the source declares a dependency
```

The generated repository passes `ruff`, `mypy --strict`, `pytest` and `pre-commit`
before any endpoint is added. `tests/test_family.py`, one line, collects core's family
check, which then keeps the layout, the adapters, the task shapes, the README status
table, the template tag and the core bound honest as tasks are added. A generated
package is read-only: the template renders no write tools. `ci.yml` also requires a
CHANGELOG entry on every pull request but Dependabot's, an adoption's (conventions §15
item 9) and a release's included, which changes `CHANGELOG.md` itself, as a fragment
under `changelog/` or a line in `CHANGELOG.md`, and fails on a fixture file over 256 KiB;
`publish.yml` is the release train. `organization.yml` calls the organization's checks of
a pull request: `conventions`, a review against the documents the README lists, and
`adr-index`, which runs the render's `scripts/adr_index.py --check`. `live.yml` runs every
`live` test every night and on demand with `--tb=short --assert=plain`, so its public log
holds neither a failing test's frame arguments nor the values a failed assertion
compared. Its start time derives from the slug, between 01:00 and 05:59 UTC, so sources that
share a key do not start together; only its pytest step sees the keys, from the org
secrets named by `api_key_env` and by `source_dependencies`' `key_env`, and the other
variables `live_secrets` names, each from the secret of the same name. Where the import
path nests or the source declares a dependency, `siblings.yml` runs
`.github/scripts/check-siblings.sh` on every pull request and push to `main`: it installs
the wheel beside every sibling on PyPI under the same provider namespace that shares its
core minor and beside the source packages it depends on, at their bound, and proves the
namespace levels stay portions (ADR-0006, ADR-0021), a visible check the ruleset does not
require; a declared dependency on another core minor fails it.
`scripts/refresh_upstream.py` is the skeleton of the capture script `/refresh-upstream`
runs; it refuses to run until the source fills it.

## Updating generated repositories

A template release, and the xippios-core minor it carries, reach a generated repository
in one adoption PR before its next release (conventions §15, ADR-0018), taken with
`copier update` run inside the generated repository:

```bash
uvx --from 'copier>=9.19' copier update --defaults --vcs-ref=v0.3.2 -d core_version=0.3.0 -d core_git_ref=
git diff                             # review; resolve conflicts
```

The template needs copier 9.19.0 or later (`_min_copier_version`), whose `ask` setting
lets the gateway answer derive the key answers and still record them; `--from
'copier>=9.19'` keeps a stale tool cache from refusing it.
Answers are read from `.copier-answers.yml`; pass `-d key=value` to change one, as above
to raise the core minor and drop a core pin (`--vcs-ref=:current:` changes the answers
without moving the template). Files listed under `_skip_if_exists` in `copier.yml` (the
package `__init__.py`, the client, the package's errors, models, endpoint wrappers, the
file parsers, the task layer, the packaged lists and enums, reference data, the two
refresh scripts, the task and live tests and the fixtures, upstream snapshot, the ADR
index, README, CHANGELOG and CLAUDE.md) are never overwritten once they exist, so a
template fix to one of them does not reach existing repositories by itself; one the
template stops rendering, though, is deleted by the update where the repository's earlier
render had it, the source's content included.
[CHANGELOG.md](CHANGELOG.md) lists those fixes per release, path, change and reason, in a
**Hand-apply** list at the section's end or, from 0.3.3, in a `Hand-apply:` note under
the change's bullet; port each one by hand in the same PR. A new file under those
patterns is created by the update where the repository has none of that name. Every other
file is the template's: the commands under `.claude/commands/`, `scripts/adr_index.py`,
`tests/conftest.py` and `tests/test_family.py` among them are re-rendered, and a source's
own lines in them are merged three ways, conflicts marked. A template-owned file a
release removes is deleted by the update, a source's own lines in it included, so the
release's CHANGELOG says where they move first.

## Developing the template

```bash
uv sync
uv run pytest           # renders the family's five variants once each and checks them, ruff included
scripts/prove.sh        # full proof against the released core: copier copy, uv sync, ruff, mypy, pytest, pre-commit
scripts/prove.sh --core-ref main   # against unreleased core
scripts/prove.sh --keyless         # a keyless flat source instead of the keyed nested one
scripts/prove.sh --keyless-nested  # a keyless nested source
scripts/prove.sh --keyless-nested -d has_files=true   # one that parses files
scripts/prove.sh --gateway         # a nested source behind api.data.gov; CI runs these five proofs
```

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
Its merge on `main` runs `.github/workflows/release.yml`, which tags `vX.Y.Z` on the
merge commit with that section as the tag's message; every other push to `main` finds
the top heading tagged and ends quietly. Nobody pushes the tag by hand.
Generated repositories record the tag in `.copier-answers.yml`; `copier copy` takes it as
the latest, and `copier update` reaches it.

## Documents

- sdk-core: [docs/conventions.md](https://github.com/xippios/sdk-core/blob/main/docs/conventions.md) — the conventions every xippios source package follows, which a generated repository satisfies out of the box.
- sdk-core: [docs/adr.md](https://github.com/xippios/sdk-core/blob/main/docs/adr.md) — the index of the family's architecture decisions, which the conventions and this template cite.
- sdk-core: [docs/definition-of-done.md](https://github.com/xippios/sdk-core/blob/main/docs/definition-of-done.md) — what a change satisfies before its pull request is opened.
- sdk-core: [docs/review-checklist.md](https://github.com/xippios/sdk-core/blob/main/docs/review-checklist.md) — what the review of a pull request checks, in order.
- sdk-template: [docs/adr.md](https://github.com/xippios/sdk-template/blob/main/docs/adr.md) — the index of this template's own decisions, generated from the records in `docs/adr/`.
- sdk-template: [changelog/README.md](https://github.com/xippios/sdk-template/blob/main/changelog/README.md) — how a change writes its changelog entry as a fragment, its Hand-apply note included, and how a release assembles the fragments.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
