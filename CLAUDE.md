# sdk-template — instructions for Claude Code

This repository is the copier template that generates every `xippios-<source>` package
repository. It is not a Python package. What it generates must satisfy the family's
documents in `../sdk-core/docs/` (conventions, ADRs, definition of done); read those first,
then `README.md` here.

## Layout

```
copier.yml               questions and copier settings (subdirectory, skip-if-exists, envops)
template/                what gets generated; *.jinja files are rendered, others copied verbatim
  src/xippios/{{ package_dir }}/  the package (import_path as directories, ADR-0006): _client, models, tasks, api/, mcp, http, reference/
  tests/                 conftest (plugin), test_family (core's family check, one line), task replay
                         tests, live smoke
  .claude/commands/      add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep,
                         adopt-release (walks conventions §15 for an adoption PR)
  CLAUDE.md.jinja        the contract a session gets in a generated repo; keep it readable by a new engineer
  .github/, .pre-commit-config.yaml, .secrets.baseline, LICENSE   copied from sdk-core, verbatim but for the deviations in Rules
  .github/workflows/live.yml.jinja   the nightly live workflow, the one rendered workflow (Rules)
  tests/test_family.py   one line collecting xippios.core.testing.family
  .gitattributes         docs/upstream/** -text: the snapshot stays byte for byte (CRLF, mixed endings)
scripts/new-source.sh    generate + checks + GitHub repo + PR (the /new-source command)
scripts/prove.sh         generate sdk-example-api (or, --keyless, sdk-example) from the working tree and run every check on it
tests/test_template.py   generation variants, ruff on the output, skip-if-exists behaviour
CHANGELOG.md             template releases, each with its Hand-apply list (Rules)
.github/workflows/ci.yml       the template's own CI: tests and scripts/prove.sh
.github/workflows/release.yml  tags vX.Y.Z from the top CHANGELOG heading on push to main (Workflow rules)
.github/workflows/gates.yml    core's gates.yml, byte for byte the template's copy, off until GATES_CALLER (Rules)
.claude/commands/new-source.md
```

## Rules

- Generated code must pass `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`
  and `pre-commit` out of the box. `scripts/prove.sh` is the proof; run it before every PR
  and paste its tail into the PR description.
- Files a session fills with source content (`__init__.py`, `_client.py`, `models.py`,
  `api/`, `tasks.py`, `tasks_write.py`, `params.py`, `enums.py`, `reference/`, `scripts/`,
  `tests/test_tasks.py`, `tests/test_tasks_write.py`, `tests/test_live.py`,
  `tests/fixtures/`, `docs/upstream/`, `README.md`, `CHANGELOG.md`) are listed in
  `_skip_if_exists` so `copier update` never overwrites them; copier renders the patterns,
  so those inside the package name `{{ package_dir }}`, never `**`, which would match a
  whole package named like a protected directory (`example-api`'s `xippios/example/api/`).
  Every other rendered file is the template's and updates with it, `tests/conftest.py`
  and `tests/test_family.py` among them: keep in those only what every source shares.
  What every source shares and can be tested belongs in core's family check, not in a
  rendered test. A template-owned file the template removes is deleted by `copier update`,
  a source's own lines in it included: the CHANGELOG says where they move first.
- Workflow files are copied verbatim (no `.jinja`) so GitHub's `${{ }}` never meets Jinja,
  with one exception: `live.yml.jinja` is rendered, because the secret its pytest step
  reads is named by the `api_key_env` answer and its start time comes from
  `live_schedule`, a hidden answer `copier.yml` computes from the slug. It writes GitHub's
  own expressions as `{{ '${{' }}` and `{{ '}}' }}`; `tests/test_template.py` checks that
  no Jinja survives, that a keyed source names its secret exactly once, on the pytest
  step, and that an open one names none.
- The verbatim files mirror sdk-core at the core release the template adopts (v0.2.1);
  `gates.yml` is core's file from after v0.2.1 (it calls `xippios/sdk-gates`);
  `tests/test_template.py` pins `gates.yml` and `PULL_REQUEST_TEMPLATE.md` to core's bytes,
  and `ci.yml` and `publish.yml` to core's bytes once the template's own steps below are
  taken out. sdk-template's own `.github/workflows/gates.yml` is the same file, byte for
  byte `template/.github/workflows/gates.yml`, which the tests check: the template carries
  the gates caller as every repository does, off until Johannes sets the repository
  variable `GATES_CALLER` to `1` on it. When sdk-core changes one of them, change it here
  too (`gates.yml` in both places) and bump the template; `copier update` carries it
  into the generated repos. Two carry the exclusion of `.copier-answers.yml`, in the
  detect-secrets hook's `exclude` in `.pre-commit-config.yaml` and in
  `should_exclude_file` in `.secrets.baseline`, because the answers file names the key's
  variable and trips the keyword check on commit and on a baseline rescan alike; sdk-core
  carries the same exclusion since core 0.2.0.
  `publish.yml` deviates by one step: in its `tag` job, before the tag, it refuses a
  `pyproject.toml` that has `[tool.uv.sources]`, since a source that pins core to git
  cannot be published (conventions §12); core has no pin to guard. `ci.yml` deviates by
  `fetch-depth: 0` and the two steps after the checkout that read the pull request, the
  CHANGELOG entry and the fixture cap, which core's `docs/handover.md` gives for the
  template ("Template v0.2.1: the two family checks that are CI steps").
- Every template release has an entry in `CHANGELOG.md` (Keep a Changelog), and every
  entry ends with a `### Hand-apply` list: one bullet per generated file under
  `_skip_if_exists` that the release changes, `` - `<path>` — <what> — <why> ``, because
  `copier update` never touches those files once they exist. A PR that changes such a
  file adds its bullet under Unreleased; a change that matters to new repositories only
  (a scaffold's starting text) says so instead of a bullet.
- Jinja renders with `trim_blocks` and `lstrip_blocks`, so a line holding only a block tag
  disappears. Mind blank lines in generated Python: the formatter check is strict.
- Keep `copier.yml` questions mechanical: every answer must come from the upstream
  documentation or the human, never be guessed by a session.
- `detect-secrets` flags Jinja lines that mention `api_key_location` as if they held a
  key. Known false positives live in `.secrets.baseline`; after changing such a line, run
  `uv run detect-secrets scan --baseline .secrets.baseline` and commit the updated
  baseline. Never add a real value to silence it.

## Commands

```bash
uv sync                         # copier, pytest, ruff, pyyaml, detect-secrets
uv run pytest                   # template tests (fast: generation + ruff on the output)
scripts/prove.sh                  # full proof against the xippios-core release on PyPI
scripts/prove.sh --core-ref main  # against unreleased core, before a core change lands
uv run ruff check . && uv run ruff format --check .
```

## Workflow rules

- Branch from `main` as `feature/<topic>`, `fix/<topic>`, `chore/<topic>` or `docs/<topic>`.
  Never commit to `main`.
- Conventional Commits; PR body is the definition-of-done checklist from sdk-core, ticked
  honestly (items about task functions and fixtures are n/a here; say so).
- `/new-source` is run by a session; `gh repo create` and the environment `PUT` inside
  `scripts/new-source.sh` are not on the allow list, so the human approves each in the
  permission prompt. Never run those commands outside the script.
- Generated repositories record the template tag they were made from; `new-source.sh`
  uses the latest tag (HEAD only while the template is untagged), and core's family
  check fails a repository whose `.copier-answers.yml` names no tag.
- Releases follow the release train (conventions §12, ADR-0018 amendment (b)): a
  `chore/release-X.Y.Z` PR turns `## [Unreleased]` into `## [X.Y.Z] - <date>` and changes
  nothing else; its merge runs `.github/workflows/release.yml`, which tags `vX.Y.Z` on the
  merge commit with that section as the message. No session pushes a tag.
- Never tag, merge, release or touch secrets from a session; the one exception is
  enabling auto-merge on a `chore/release-*` PR whose merge class is `auto`, after the
  reviewer's `ready` (ADR-0018, amendments (a) and (e)).
- Never read or print `.envrc`, `.env`, or any variable ending in `_API_KEY`.
