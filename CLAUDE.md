# sdk-template — instructions for Claude Code

This repository is the copier template that generates every `xippios-<source>` package
repository. It is not a Python package. What it generates must satisfy the family's
documents on sdk-core's `main`: the conventions,
https://github.com/xippios/sdk-core/blob/main/docs/conventions.md, the ADRs,
https://github.com/xippios/sdk-core/tree/main/docs/adr, the definition of done,
https://github.com/xippios/sdk-core/blob/main/docs/definition-of-done.md, and the review
checklist, https://github.com/xippios/sdk-core/blob/main/docs/review-checklist.md. Read
those first, then `README.md` here.

## Layout

```
copier.yml               questions and copier settings (subdirectory, skip-if-exists, envops)
template/                what gets generated; *.jinja files are rendered, others copied verbatim
  src/xippios/{{ package_dir }}/  the package (import_path as directories, ADR-0006): _client, errors, models, tasks, api/, mcp, http, reference/
  tests/                 conftest (plugin), test_family (core's family check, one line), task replay
                         tests, live smoke
  .claude/commands/      add-endpoint, record-fixture, refresh-upstream, refresh-reference-data, release-prep,
                         adopt-release (walks conventions §15 for an adoption PR)
  .claude/family.md.jinja  the family rules a generated repo's CLAUDE.md imports; no Jinja, the same in every source
  CLAUDE.md.jinja        the facts of a generated repo, importing the family rules; the source's once rendered
  .github/, .pre-commit-config.yaml, .secrets.baseline, LICENSE   copied from sdk-core, verbatim but for the deviations in Rules
  .github/workflows/live.yml.jinja   the nightly live workflow, the one rendered workflow (Rules)
  .github/workflows/{% if '.' in import_path %}siblings.yml{% endif %}, .github/{% if '.' in import_path %}scripts{% endif %}/check-siblings.sh
                         the sibling proof of ADR-0006, verbatim, only their names rendered (Rules)
  scripts/refresh_upstream.py.jinja  the capture skeleton a source fills (/refresh-upstream)
  tests/test_family.py   one line collecting xippios.core.testing.family
  .gitattributes         docs/upstream/** -text: the snapshot stays byte for byte (CRLF, mixed endings)
scripts/new-source.sh    generate + checks + GitHub repo + PR (the /new-source command)
scripts/prove.sh         generate sdk-example-api (--keyless: sdk-example; --keyless-nested: sdk-example-files)
                         from the working tree and run every check on it
tests/test_template.py   the family's variants, each rendered once; ruff on the output, the answers' rules,
                         skip-if-exists behaviour
CHANGELOG.md             template releases, each with its Hand-apply list (Rules)
.github/workflows/ci.yml       the template's own CI: tests and the three proofs
.github/workflows/release.yml  tags vX.Y.Z from the top CHANGELOG heading on push to main (Workflow rules)
.github/workflows/gates.yml    core's gates.yml, byte for byte the template's copy, off until GATES_CALLER (Rules)
.claude/commands/new-source.md
```

## Rules

- Generated code must pass `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`
  and `pre-commit` out of the box. `scripts/prove.sh` is the proof, in the family's three
  shapes: keyed and nested (no flag), keyless and flat (`--keyless`), keyless and nested
  (`--keyless-nested`); CI runs all three. Run them before every PR and paste their tails
  into the PR description.
- `tests/test_template.py` renders each of the family's variants once per session, keyed
  nested, keyless flat and keyless nested; a check no answer changes reads one render,
  and an answer outside the variants (a key location, a core pin, a name at its bound,
  an `import_path` override) is tested by its own rule. The tests assert mechanics, never rendered prose: a file
  rendered or not, a name present, no Jinja left, a digest equal, a script's behaviour.
- Files a session fills with source content (`__init__.py`, `_client.py`, `errors.py`,
  `models.py`, `api/`, `tasks.py`, `params.py`, `enums.py`, `reference/`, `scripts/`,
  `tests/test_tasks.py`, `tests/test_live.py`, `tests/fixtures/`, `docs/upstream/`,
  `README.md`, `CHANGELOG.md`, `CLAUDE.md`) are listed in `_skip_if_exists` so
  `copier update` never overwrites them; copier renders the patterns, so those inside the
  package name `{{ package_dir }}`, never `**`, which would match a whole package named
  like a protected directory (`example-api`'s `xippios/example/api/`).
  Every other rendered file is the template's and updates with it, `.claude/family.md`,
  `tests/conftest.py` and `tests/test_family.py` among them: keep in those only what every
  source shares. `.claude/family.md.jinja` holds no Jinja, so every source renders the same
  file, which the tests check; a line that depends on an answer belongs in
  `CLAUDE.md.jinja`, which a source owns once rendered and keeps its facts in.
  What every source shares and can be tested belongs in core's family check, not in a
  rendered test. A template-owned file the template removes is deleted by `copier update`,
  a source's own lines in it included: the CHANGELOG says where they move first. So is a
  file under `_skip_if_exists` the template stops rendering, where the repository's
  earlier render had it, `_skip_if_exists` notwithstanding (copier 9.19.1).
- Workflow files are copied verbatim (no `.jinja`) so GitHub's `${{ }}` never meets Jinja,
  with one exception: `live.yml.jinja` is rendered, because the secret its pytest step
  reads is named by the `api_key_env` answer and its start time comes from
  `live_schedule`, a hidden answer `copier.yml` computes from the slug. It writes GitHub's
  own expressions as `{{ '${{' }}` and `{{ '}}' }}`; `tests/test_template.py` checks that
  no Jinja survives, that a keyed source names its secret exactly once, on the pytest
  step, and that an open one names none. Two verbatim files render only where the import
  path nests, so only their names hold Jinja: `.github/workflows/siblings.yml` and the
  script it runs, `.github/scripts/check-siblings.sh` (executable; copier keeps the
  bit), the sibling proof of ADR-0006. They stay outside the skip-listed `scripts/`, so
  the merge classes trust a source's copy identical to the render, and the name of the
  script's directory is the conditional one, so a flat render gets no empty directory.
  `siblings` is a visible job the ruleset does not require: `ci.yml` stays core's file.
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
  template ("Template v0.2.1: the two family checks that are CI steps"); from v0.3.0 the
  CHANGELOG step exempts a release and Dependabot only, no longer an adoption, whose line
  conventions §15 item 9 requires.
- Every template release has an entry in `CHANGELOG.md` (Keep a Changelog), and every
  entry ends with a `### Hand-apply` list: one bullet per generated file under
  `_skip_if_exists` that the release changes, `` - `<path>` — <what> — <why> ``, because
  `copier update` never touches those files once they exist. A PR that changes such a
  file adds its bullet under Unreleased; a change that matters to new repositories only
  (a scaffold's starting text) says so instead of a bullet.
- Jinja renders with `trim_blocks` and `lstrip_blocks`, so a line holding only a block tag
  disappears, and a block tag at the end of a line takes that line's newline with it. A
  block tag therefore stands alone on its line or opens and closes there, before the
  line's end; the tests check every `.jinja` file for it. Mind blank lines in generated
  Python: the formatter check is strict.
- Keep `copier.yml` questions mechanical: every answer must come from the upstream
  documentation or the human, never be guessed by a session.
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
  no file outside conventions §12's release subset (`CHANGELOG.md`, and `README.md` or
  `CLAUDE.md` where a sentence names the release). The section may gain a lead paragraph
  and says internal labels (decisions, queue rows, plan items) in plain words, since it
  becomes the tag's message. Its merge runs `.github/workflows/release.yml`, which tags
  `vX.Y.Z` on the merge commit with that section as the message. No session pushes a tag.
- Never tag, merge, release or touch secrets from a session; the one exception is
  enabling auto-merge on a `chore/release-*` PR whose merge class is `auto`, after the
  reviewer's `ready` (ADR-0018, amendments (a) and (e)).
- Never read or print `.envrc`, `.env`, or any variable ending in `_API_KEY`.
