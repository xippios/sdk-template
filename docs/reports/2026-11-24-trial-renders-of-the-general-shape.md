# Trial renders of the general shape with its two consumers' answers, 2026-11-24

Both packages that take the general part of a repository can take it, which ADR-0003 rests on.
The shared package `sdk-usda-fas`, rendered new with its answers, passes every check of a
render. The host `xippios-mcp`, rendered over its own tree, keeps every file it owns and takes
the template's files of the general part, and its checks pass once its own `pyproject.toml`
leaves the three scripts of the organization out of ruff, as the rendered `pyproject.toml`
does: before that exclusion ruff fails on those three scripts alone.

## Basis

- The template: `copier.yml` and `template/` at
  https://github.com/xippios/sdk-template/commit/5d5d35601c458a791e744a2d2e8371489d129c51,
  committed into a repository of their own and tagged, since copier renders a git
  repository at a tag. `<template>` below stands for that repository and `<tag>` for its tag.
- copier 9.19.1 (https://pypi.org/project/copier/9.19.1/), uv and Python 3.12, offline but for
  the packages that `uv sync` installs from PyPI. No upstream was called.
- The host's tree: a clone of https://github.com/xippios/xippios-mcp at
  https://github.com/xippios/xippios-mcp/commit/1d3ee79566bbc02b966493df4a3527f6b08dffc0.
- The shared package has no repository yet, so its answers stand here. Its `source_name` and
  the host's are proposals that no record gives yet.
- The checks of a render, as the template's `scripts/prove.sh` runs them:
  `uv sync --all-extras`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy`, `uv run pytest`, `git init`, `git add -A` and
  `uv run pre-commit run --all-files`.

## The shared package

The render with the answers that `sdk-usda-fas` takes:

```bash
copier copy --defaults --vcs-ref <tag> \
  -d shape=general -d source_slug=usda-fas -d import_path=usda.fas \
  -d "source_name=USDA FAS" -d core_version=0.5.0 -d core_git_ref= \
  -d 'source_dependencies=[]' \
  <template> sdk-usda-fas
```

- It holds 35 files. `.copier-answers.yml` records 8 answers: `core_git_ref: ''`,
  `core_version: 0.5.0`, `import_path: usda.fas`, `repository_name: sdk-usda-fas`, the
  default, `shape: general`, `source_dependencies: '[]'`, `source_name: USDA FAS` and
  `source_slug: usda-fas`.
- `pyproject.toml` bounds core as `xippios-core~=0.5.0` and its `testing` extra as
  `xippios-core[testing]~=0.5.0`.

xippios-core 0.5.0 is not on PyPI yet, so the checks ran on the same answers with
`-d core_version=0.4.1`, which installs xippios-core 0.4.1
(https://pypi.org/project/xippios-core/0.4.1/):

| check | result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 9 files already formatted |
| `uv run mypy` | no issues in 7 source files |
| `uv run pytest` | 1 passed, `tests/test_package.py` |
| `uv run pre-commit run --all-files` | ruff check, ruff format, mypy --strict and detect-secrets passed |
| `XIPPIOS_SIBLINGS='' .github/scripts/check-siblings.sh` | the wheel alone: `xippios.usda.fas` 0.1.0 imports, `xippios` and `xippios.usda` stay namespace portions, every tracked file of the package ships in the wheel |

## The host

The render with the host's answers over its tree, which holds no `.copier-answers.yml`, so
`copier copy` with `--overwrite` takes the place of an update:

```bash
copier copy --defaults --overwrite --vcs-ref <tag> \
  -d shape=general -d source_slug=mcp -d import_path=mcp -d repository_name=xippios-mcp \
  -d "source_name=xippios SDK family" -d core_version=0.5.0 -d core_git_ref= \
  -d 'source_dependencies=[]' \
  <template> xippios-mcp
```

Of the 33 files that the render holds, flat as the host is:

- **Changed, 8:** `.claude/commands/release-prep.md`, `.github/CODEOWNERS`,
  `.github/workflows/ci.yml`, whose job `docker` the render does not hold,
  `.github/workflows/publish.yml`, `.gitignore`, `.pre-commit-config.yaml`,
  `docs/adr/README.md` and `scripts/adr_index.py`.
- **Added, 7:** `.copier-answers.yml`, `.claude/rules/never.md`,
  `.github/workflows/adr-index.yml`, `.github/workflows/conventions.yml`, `docs/layout.md`,
  `scripts/changelog_assemble.py` and `scripts/release_prepare.py`.
- **Kept by `_skip_if_exists`, 10:** `pyproject.toml`, `README.md`, `CLAUDE.md`,
  `CHANGELOG.md`, `docs/adr.md`, `docs/adr.json`, `.secrets.baseline`, `tests/conftest.py`,
  `tests/test_package.py`, the host's own, and `src/xippios/mcp/__init__.py`. The host's
  `docs/adr.json` and `.secrets.baseline` equal the render's.
- **Equal, 8:** `.claude/settings.json`, `.github/PULL_REQUEST_TEMPLATE.md`,
  `.python-version`, `LICENSE`, `changelog/README.md`, `docs/reports/README.md`,
  `src/xippios/mcp/_version.py` and `src/xippios/mcp/py.typed`.

The host's files that the render does not hold stand as they were, among them
`.github/workflows/organization.yml`, `Dockerfile`, `.dockerignore` and its own tests. The
checks ran on the core that the host's own `uv.lock` holds, xippios-core 0.3.0
(https://pypi.org/project/xippios-core/0.3.0/), since its `pyproject.toml` stays its own.

`uv run ruff check .` fails with 245 findings, all in the three scripts of the organization
that the render brings: 40 in `scripts/adr_index.py`, 130 in `scripts/changelog_assemble.py`
and 75 in `scripts/release_prepare.py`. Those scripts are one version that every repository
carries byte for byte, which the rendered `pyproject.toml` leaves out of ruff, while the
host's own `pyproject.toml` leaves out `docs` and `.claude` alone. With the three added to its
`extend-exclude`:

```toml
extend-exclude = [
  "docs",
  ".claude",
  "scripts/adr_index.py",
  "scripts/changelog_assemble.py",
  "scripts/release_prepare.py",
]
```

| check | result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 23 files already formatted |
| `uv run mypy` | no issues in 18 source files |
| `uv run pytest` | 161 passed |
| `uv run pre-commit run --all-files` | ruff check, ruff format, mypy --strict and detect-secrets passed |
