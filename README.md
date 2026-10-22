# sdk-template

[Copier](https://copier.readthedocs.io/) template for `xippios-<source>` repositories,
the per-source packages of the [xippios SDK family](https://github.com/xippios). A
generated repository conforms to the family's
[conventions](https://github.com/xippios/sdk-core/blob/main/docs/conventions.md) and
[ADRs](https://github.com/xippios/sdk-core/tree/main/docs/adr) out of the box: the
three-layer layout, `xippios-core` client and models, MCP server and FastAPI router wired
to the task layer, test harness with the live-test gate, CI with the required `ci` check,
trusted publishing, pre-commit, and a `CLAUDE.md` plus slash commands for the sessions
that will maintain it.

## Creating a source repository

From Claude Code in this repository: `/new-source <slug>`. It collects the answers below,
then runs `scripts/new-source.sh`, which generates the repo, runs every check on it,
creates `github.com/xippios/sdk-<slug>` with topics and the `pypi` environment, and opens
the scaffold PR. The repository creation and the environment call raise permission
prompts the human approves. Three steps stay with a human and are printed at the end:
the PyPI pending publisher, the API key in `.envrc` and as an org secret, and the review.

By hand:

```bash
scripts/new-source.sh usda-nass \
  -d "source_name=USDA NASS Quick Stats" \
  -d "upstream_url=https://quickstats.nass.usda.gov" \
  -d "upstream_docs_url=https://quickstats.nass.usda.gov/api" \
  -d "api_base_url=https://quickstats.nass.usda.gov/api" \
  -d "api_key_env=NASS_API_KEY" -d "api_key_location=query" -d "api_key_name=key" \
  -d "rate_limit_per_minute=60" -d "domain_topic=agriculture"
```

Add `--local-only` to generate and check without touching GitHub.

## Questions

| Question | Meaning | Example |
| --- | --- | --- |
| `source_slug` | provider, plus API when one provider has several; names the repo, the distribution and the import | `usda-nass` |
| `source_name` | human name | `USDA NASS Quick Stats` |
| `upstream_url` | provider page, linked from the README | `https://quickstats.nass.usda.gov` |
| `upstream_docs_url` | where `/refresh-upstream` fetches the documentation from | `https://quickstats.nass.usda.gov/api` |
| `api_base_url` | base URL request paths join onto; required, usually not the provider page | `https://quickstats.nass.usda.gov/api` |
| `api_key_env` | environment variable with the key; empty for open APIs | `NASS_API_KEY` |
| `api_key_location` | `query`, `header`, `bearer` or `basic` | `query` |
| `api_key_name` | query parameter or header name | `key` |
| `rate_limit_per_minute` | upstream's documented limit, enforced client-side | `60` |
| `needs_write_tools` | adds `tasks_write.py` and the confirm-gated write server | `false` |
| `domain_topic` | GitHub topic for the domain | `agriculture` |
| `core_git_ref` | development only: depend on sdk-core at a git ref while it is not on PyPI | `main` |

## What gets generated

```
sdk-<slug>/
  src/xippios/<pkg>/   __init__, _version, _client, models, tasks, api/, mcp, http, reference/
                       (+ tasks_write, mcp_write when needs_write_tools)
  tests/               conftest, test_tasks, test_adapters, test_live, fixtures/
  docs/upstream/       FETCHED.md
  .claude/commands/    add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep
  .claude/settings.json  .github/workflows/{ci,publish}.yml  .github/PULL_REQUEST_TEMPLATE.md
  CLAUDE.md  README.md  CHANGELOG.md  LICENSE  pyproject.toml  .pre-commit-config.yaml  .secrets.baseline
```

The generated repository passes `ruff`, `mypy --strict`, `pytest` and `pre-commit` before
any endpoint is added; `tests/test_adapters.py` then keeps the adapters honest as tasks
are added.

## Updating generated repositories

Template changes roll out with `copier update`, run inside a generated repository:

```bash
uvx copier update                    # to the latest template tag; --vcs-ref HEAD for main
git diff                             # review, then open a chore/template-update PR
```

Answers are read from `.copier-answers.yml`; pass `-d key=value` to change one, for
example `-d core_git_ref=` once `xippios-core` is on PyPI. Files listed under
`_skip_if_exists` in `copier.yml` (the task layer, models, endpoint wrappers, tests,
README, CHANGELOG, upstream snapshot, reference data) are never overwritten.

## Developing the template

```bash
uv sync
uv run pytest           # generates variants into a temp dir and runs ruff on them
scripts/prove.sh        # full proof: generate sdk-example, uv sync, ruff, mypy, pytest, pre-commit
```

## Licence

Apache-2.0. See [LICENSE](LICENSE).
