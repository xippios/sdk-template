# sdk-template

[Copier](https://copier.readthedocs.io/) template for `xippios-<source>` repositories,
the per-source packages of the [xippios SDK family](https://github.com/xippios). A
generated repository conforms to the family's
[conventions](https://github.com/xippios/sdk-core/blob/main/docs/conventions.md) and
[ADRs](https://github.com/xippios/sdk-core/tree/main/docs/adr) out of the box: the
three-layer layout, `xippios-core` client and models, MCP server and FastAPI router wired
to the task layer, test harness with the live-test gate and core's family check, CI with
the required `ci` check, the release train with trusted publishing, pre-commit, and a
`CLAUDE.md` plus slash commands for the sessions that will maintain it.

## Creating a source repository

From Claude Code in this repository: `/new-source <slug>`. It collects the answers below,
then runs `scripts/new-source.sh`, which generates the repo, runs every check on it,
creates `github.com/xippios/sdk-<slug>` with topics, auto-merge, branch deletion on merge,
the `sdk-sessions` team's write access where the team exists and the `pypi` environment,
and opens the scaffold PR. The repository creation and the environment call raise
permission prompts the human approves. Before it, a session owns `sdk-<slug>` in the
workspace's `coordination/owners.toml`, since the workspace's guard refuses work in a
directory no session owns. Three steps stay with a human and are printed at the end: the
PyPI pending publisher, which the first release's publish job needs; the API key, which
the nightly `live.yml` reads from an org secret (for a key several sources share,
ADR-0009, the new repository is added to the existing secret's repository access, never
with `gh secret set --repos`, which replaces the list; a new key goes into `.envrc` and a
new org secret); and the review and merge of the scaffold PR. Releases tag themselves:
the merge of a release PR runs the generated `publish.yml`, which tags the version and
waits for the approval of its `pypi` run.

By hand:

```bash
scripts/new-source.sh usda-nass \
  -d "source_name=USDA NASS Quick Stats" \
  -d "upstream_url=https://quickstats.nass.usda.gov" \
  -d "upstream_docs_url=https://quickstats.nass.usda.gov/api" \
  -d "api_base_url=https://quickstats.nass.usda.gov/api" \
  -d "api_key_env=NASS_API_KEY" -d "api_key_location=query" -d "api_key_name=key" \
  -d "rate_limit_per_minute=30" -d "rate_limit_provenance=self-imposed" \
  -d "domain_topic=agriculture"
```

Add `--local-only` to generate and check without touching GitHub. The script generates
from this template's GitHub URL at its latest tag, so `.copier-answers.yml` records a
source that `copier update` can reach from any machine. It refuses to create a repository
while the organisation's default branch is not `main`: the `sdk-main-protection` ruleset
enforces its `ci` check on branch creation, so `main` cannot be added to a repository
afterwards by rename or push.

## Questions

| Question | Meaning | Example |
| --- | --- | --- |
| `source_slug` | provider, plus API when one provider has several; names the repo, the distribution and the import | `usda-nass` |
| `source_name` | human name | `USDA NASS Quick Stats` |
| `import_path` | import path under `xippios`; defaults to the slug with dots, so multi-API providers nest (ADR-0006); override for a hyphenated single-API provider | `usda.nass` |
| `upstream_url` | provider page, linked from the README | `https://quickstats.nass.usda.gov` |
| `upstream_docs_url` | where `/refresh-upstream` fetches the documentation from | `https://quickstats.nass.usda.gov/api` |
| `api_base_url` | base URL request paths join onto; required, usually not the provider page | `https://quickstats.nass.usda.gov/api` |
| `api_key_env` | environment variable with the key; empty for open APIs | `NASS_API_KEY` |
| `api_key_location` | `query`, `header`, `bearer` or `basic` | `query` |
| `api_key_name` | query parameter or header name | `key` |
| `rate_limit_per_minute` | the pace, enforced client-side: upstream's documented per-minute (or per-second × 60) limit, or a self-imposed pace where upstream documents none (ADR-0010) | `30` |
| `rate_limit_burst` | requests let through at once before the pace applies; `1` unless upstream documents a burst | `1` |
| `rate_limit_provenance` | `documented` or `self-imposed`: where the pace comes from, named in the generated CLAUDE.md | `self-imposed` |
| `needs_write_tools` | adds `tasks_write.py` and the confirm-gated write server | `false` |
| `domain_topic` | GitHub topic for the domain | `agriculture` |
| `core_version` | the xippios-core release depended on, rendered `xippios-core~=<version>`, the extras likewise (one core minor, from its `.0` or from the patch that shipped what the source adopts: conventions §12, ADR-0018); default `0.2.1`, the release whose family check `tests/test_family.py` collects | `0.2.1` |
| `core_git_ref` | development only: depend on sdk-core at `main` or at the full 40-character SHA of a commit on `main` for an unreleased core change (anything else is refused); removing it before a release, in a PR of its own, raises `core_version` to the release that carries the pinned change: `X.Y.Z` with `Z` the patch that shipped it, or `X.Y.0` when the minor itself did; still one minor | `main` |

## What gets generated

```
sdk-<slug>/
  src/xippios/<import path as dirs>/   __init__, py.typed, _version, _client, models, tasks,
                       api/, mcp, http, reference/ (+ tasks_write, mcp_write when needs_write_tools)
  tests/               conftest, test_family, test_tasks, test_live, fixtures/
                       (+ test_tasks_write when needs_write_tools)
  docs/upstream/       FETCHED.md
  .claude/commands/    add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep,
                       adopt-release
  .claude/settings.json  .github/workflows/{ci,publish,gates,live}.yml  .github/PULL_REQUEST_TEMPLATE.md
  CLAUDE.md  README.md  CHANGELOG.md  LICENSE  pyproject.toml  .pre-commit-config.yaml  .secrets.baseline
  .gitattributes       docs/upstream/** -text, so upstream files keep their bytes and line endings
```

The generated repository passes `ruff`, `mypy --strict`, `pytest` and `pre-commit` before
any endpoint is added. `tests/test_family.py`, one line, collects core's family check,
which then keeps the layout, the adapters, the task shapes, the README status table, the
template tag, the core bound and the write server honest as tasks are added, while
`tests/test_tasks_write.py` checks each write task's `confirm` parameter and docstring. `ci.yml` also requires a CHANGELOG entry on every PR but a release, an
adoption or Dependabot's, and warns on a fixture file over 256 KiB; `publish.yml` is the
release train; `gates.yml` calls the merge gates as jobs once Johannes sets the
repository variable `GATES_CALLER`. `live.yml` runs every `live`
test, write tests included, every night and on demand. Its start time derives from the
slug, between 01:00 and 05:59 UTC, so sources that share a key do not start together;
only its pytest step sees the key, from the org secret named by `api_key_env`.

## Updating generated repositories

A template release, and the xippios-core minor it carries, reach a generated repository
in one adoption PR before its next release (conventions §15, ADR-0018): a
`chore/template-update-<tag>` PR whose description is the definition of done's Adoption
PR checklist; when its merge class is `auto` the session enables auto-merge after the
reviewer's `ready`, and a `human` adoption waits for Johannes. The generated
`/adopt-release <tag>` walks it step by step; at its core is `copier update`, run inside
the generated repository:

```bash
uvx copier update --defaults --vcs-ref=v0.2.1 -d core_version=0.2.1 -d core_git_ref=
git diff                             # review; resolve conflicts
```

Answers are read from `.copier-answers.yml`; pass `-d key=value` to change one, as above
to raise the core minor and drop a core pin (`--vcs-ref=:current:` changes the answers
without moving the template). Files listed under `_skip_if_exists` in `copier.yml` (the
package `__init__.py`, the client, models, endpoint wrappers, the read and write task
layers, the packaged lists and enums, reference data, scripts, the task, write and live
tests and the fixtures, upstream snapshot, README and CHANGELOG) are never overwritten
once they exist, so a template fix to one of them does not reach existing repositories by
itself. [CHANGELOG.md](CHANGELOG.md) lists those fixes per release under **Hand-apply**:
path, change, reason; port each one by hand in the same PR. A new file under those
patterns is created by the update where the repository has none of that name. Every other
file is the template's: `tests/conftest.py` and `tests/test_family.py` among them are
re-rendered, and a source's own lines in them are merged three ways, conflicts marked. A
template-owned file a release removes is deleted by the update, a source's own lines in
it included, so the release's CHANGELOG says where they move first.

## Developing the template

```bash
uv sync
uv run pytest           # generates variants into a temp dir and runs ruff on them
scripts/prove.sh        # full proof against the released core: generate, uv sync, ruff, mypy, pytest, pre-commit
scripts/prove.sh --core-ref main   # against unreleased core
scripts/prove.sh --keyless         # a keyless flat source instead of the keyed nested one
```

## Releasing the template

The template follows the release train (conventions §12): a `chore/release-X.Y.Z` PR
turns `## [Unreleased]` in `CHANGELOG.md` into `## [X.Y.Z] - <date>` and changes nothing
else, since the template has no version to bump. Its merge on `main` runs
`.github/workflows/release.yml`, which tags `vX.Y.Z` on the merge commit with that section
as the tag's message; every other push to `main` finds the top heading tagged and ends
quietly. No session and no human pushes the tag. Generated repositories record the tag in
`.copier-answers.yml`, and `copier update` reaches it.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
