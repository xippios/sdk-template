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
  tests/                 conftest (plugin), structural task tests, adapter tests, live smoke
  .claude/commands/      add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep,
                         adopt-release (walks conventions §15 for an adoption PR)
  CLAUDE.md.jinja        the contract a session gets in a generated repo; keep it readable by a new engineer
  .github/, .pre-commit-config.yaml, .secrets.baseline, LICENSE   copied from sdk-core, verbatim but for the deviations in Rules
  .github/workflows/live.yml.jinja   the nightly live workflow, the one rendered workflow (Rules)
  .gitattributes         docs/upstream/** -text: the snapshot stays byte for byte (CRLF, mixed endings)
scripts/new-source.sh    generate + checks + GitHub repo + PR (the /new-source command)
scripts/prove.sh         generate sdk-example from the working tree and run every check on it
tests/test_template.py   generation variants, ruff on the output, skip-if-exists behaviour
CHANGELOG.md             template releases, each with its Hand-apply list (Rules)
.claude/commands/new-source.md
```

## Rules

- Generated code must pass `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`
  and `pre-commit` out of the box. `scripts/prove.sh` is the proof; run it before every PR
  and paste its tail into the PR description.
- Files a session fills with source content (`_client.py`, `__init__.py`, `tasks.py`,
  `tasks_write.py`, `models.py`, `params.py`, `enums.py`, `api/`, `reference/`,
  `scripts/`, `tests/test_tasks.py`, `tests/test_tasks_write.py`, `tests/test_live.py`,
  `tests/fixtures/`, `README.md`, `CHANGELOG.md`, `docs/upstream/`) are listed in
  `_skip_if_exists` so `copier update` never overwrites them; copier renders the patterns,
  so those inside the package name `{{ package_dir }}`, never `**`, which would match a
  whole package named like a protected directory (`example-api`'s `xippios/example/api/`).
  Every other rendered file is the template's and updates with it, `tests/conftest.py`,
  `tests/test_layout.py` and `tests/test_adapters.py` among them: keep in those only what
  every source shares.
- Workflow files are copied verbatim (no `.jinja`) so GitHub's `${{ }}` never meets Jinja,
  with one exception: `live.yml.jinja` is rendered, because the secret its pytest step
  reads is named by the `api_key_env` answer and its start time comes from
  `live_schedule`, a hidden answer `copier.yml` computes from the slug. It writes GitHub's
  own expressions as `{{ '${{' }}` and `{{ '}}' }}`; `tests/test_template.py` checks that
  no Jinja survives, that a keyed source names its secret exactly once, on the pytest
  step, and that an open one names none.
- The verbatim files mirror sdk-core at the core release the template adopts (v0.2.0);
  `tests/test_template.py` pins `ci.yml` and `PULL_REQUEST_TEMPLATE.md` to its bytes.
  When sdk-core changes one of them, change it here too and bump the template;
  `copier update` carries it into the generated repos. Two carry the exclusion of
  `.copier-answers.yml`, in the detect-secrets hook's `exclude` in
  `.pre-commit-config.yaml` and in `should_exclude_file` in `.secrets.baseline`, because
  the answers file names the key's variable and trips the keyword check on commit and on
  a baseline rescan alike; sdk-core carries the same exclusion since core 0.2.0.
  `publish.yml` deviates by one step: before `uv build` it refuses a `pyproject.toml`
  that has `[tool.uv.sources]`, since a source that pins core to git cannot be published
  (conventions §12); core has no pin to guard.
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
  uses the latest tag (HEAD only while the template is untagged). Tagging is a human
  action: ask for a tag when a template change should roll out with `copier update`.
- Never tag, merge, release or touch secrets from a session.
- Never read or print `.envrc`, `.env`, or any variable ending in `_API_KEY`.
