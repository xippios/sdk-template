# sdk-template — instructions for Claude Code

This repository is the copier template that generates every `xippios-<source>` package
repository. It is not a Python package. What it generates must satisfy the documents
listed under [`## Documents` in the README](README.md#documents): sdk-core's conventions,
ADRs, definition of done and review checklist, and this repository's own decisions and
changelog rules. Read those first, then the rest of `README.md`, which says once what the
template asks, what it renders in each of its two shapes, how a render's workflows run, how a
generated repository updates, and how the template is developed and released. This file lays
out the repository and holds the rules a change of the template follows; it cites the README
for the rest.

## Layout

```
copier.yml               the questions and copier's settings: subdirectory, envops, the general
                         shape's _exclude and the files a source owns, _skip_if_exists
template/                the tree of the README's What gets generated, in both shapes: a .jinja
                         file is rendered, any other copied verbatim, and a file rendered on an
                         answer holds its condition in its name
scripts/prove.sh         generates one shape from the working tree with copier copy and runs every
                         check on it; --all proves every shape of its list `shapes`, as the
                         README's Developing the template says
scripts/adr_index.py     writes docs/adr.md and docs/adr.json from the records in docs/adr/; --check
                         fails while either is stale
tests/                   the template's tests: conftest.py renders each variant once, helpers.py
                         holds their answers, the tools a test runs on a render and the readers
                         of a rendered module, test_template.py checks the renders, ruff on the
                         output, the answers' rules and skip-if-exists behaviour, and a module of
                         its own holds each later concern: test_helpers, test_capture,
                         test_reference_data, test_repository_files, test_core_adoption,
                         test_contract, test_citations, test_release_script, test_general_shape
docs/adr/                this repository's design decisions, one NNNN-<slug>.md record each, laid
                         out in its README.md and cited as ADR-NNNN, sdk-core's as
                         `sdk-core ADR-NNNN`: ADR-0002 holds the answers that render the package
                         contract's variants and what the template asks, in place of ADR-0001,
                         and ADR-0003 the general shape
docs/adr.md, docs/adr.json  their index, written by scripts/adr_index.py, never by hand
docs/reports/            dated reports, the evidence a decision cites, laid out in its README.md
CHANGELOG.md             template releases, each section assembled from changelog/; the file names
                         the tag that holds the sections before its first
changelog/               the next release's entries, one fragment per change; README.md lays them out
pyproject.toml, uv.lock  the development tooling; version names the latest release
.github/workflows/ci.yml       the template's own CI: the tests, then scripts/prove.sh --all
.github/workflows/conventions.yml, .github/workflows/adr-index.yml  the organization's
                         checks on this repository's own pull requests; byte for byte the
                         render's (Rules)
.github/workflows/release.yml  tags vX.Y.Z from the top CHANGELOG heading, as the README's
                         Releasing the template says
.claude/settings.json    what Claude Code may run here: the checks, the proofs and local git
```

## Rules

- A render passes its checks out of the box, before an endpoint is added, as the README's
  Generating a source repository says. `scripts/prove.sh --all` is the proof, in every shape
  of its list `shapes`, as the README's Developing the template says, on the core that its
  default `--core-ref` names: run it before every pull request and paste its tail into the
  description.
- The tests render each variant that the README's Developing the template lists once per
  run; a check no answer changes reads one render, and an answer outside the variants, such
  as `has_reference_data: false`, a core pin, a name at its bound or an `import_path`
  override, is tested by its own rule. The tests assert mechanics, never rendered prose: a
  file rendered or not, a name present, no Jinja left, a digest equal, a script's behaviour.
  A new concern's tests take a module of their own beside `tests/test_template.py` and
  import what the modules share from `tests/helpers.py`.
- The files a source fills with its own content stand under `_skip_if_exists` in
  `copier.yml`, which the README's Updating generated repositories names, so that
  `copier update` never writes them once they exist. Copier renders the patterns, so those
  inside the package name `{{ package_dir }}`, never `**`, which would match a whole package
  named like a protected directory (`example-api`'s `xippios/example/api/`). They read as
  gitignore lines: `/README.md` is the root's alone, since `changelog/README.md` is every
  source's, and the two refresh scripts stand where `scripts/` would also protect
  `scripts/adr_index.py` and the two release scripts, the template's; a script of the
  source's own is never rendered, so no update touches it. The general shape leaves a
  source's files out by the one conditional entry of `_exclude`, so no file changes its
  name by the shape (ADR-0003).
  Every other rendered file is the template's and updates with it, the commands under
  `.claude/commands/`, the Never file `.claude/rules/never.md`, `scripts/adr_index.py` and
  `tests/test_family.py` among them: keep in those only what every source shares. A line
  that a source keeps its facts in belongs in a file the source owns once rendered, such as
  `CLAUDE.md.jinja`, `README.md.jinja` or `docs/layout.md.jinja`, and no file of the
  template's holds a line of a source (ADR-0002, decision 9). A file the template stops
  rendering is deleted by the update, a source's lines in it included, as the README says,
  so the change's CHANGELOG entry says first where they move.
  `scripts/adr_index.py` is the one version that the organization's repositories share, the
  same bytes here and in `template/scripts/`: it changes by that version's next one, never by
  an edit of a copy, the tests pin its digest, and the ruff of this repository and of a render
  leaves it alone while a render's mypy checks it. Every command runs it as `python3 -I`.
  `scripts/release_prepare.py` and the assembler it loads by its path,
  `scripts/changelog_assemble.py`, are the organization's one version too, rendered alone,
  with no copy at this repository's root: they change by that version's next one, never by
  an edit of a copy. The tests pin their blob ids and run the script on a render, the
  render's ruff leaves them alone, and its mypy checks both as they stand.
  `/release-prep` runs `python3 -I scripts/release_prepare.py`, which sets the version in
  `uv.lock` with no `uv lock`.
  What every source shares and can be tested belongs in core's family check, not in a
  rendered test.
- A command under `template/.claude/commands/` keeps what the README says of the commands:
  its steps and the paths that the answers render, and for each mechanism the section of
  sdk-core's conventions and the name of xippios-core that serve it, restating neither. An
  example in a command names no real source.
- Workflow files are copied verbatim, no `.jinja`, so GitHub's `${{ }}` never meets Jinja,
  with one exception: `live.yml.jinja` is rendered, because the secrets its pytest step reads
  are named by the answers, as the README's The workflows of a render says, and its start
  time comes from `live_schedule`, a hidden answer `copier.yml` computes from the slug. It
  writes GitHub's own expressions as `{{ '${{' }}` and `{{ '}}' }}`; `tests/test_template.py`
  checks that no Jinja survives, that the pytest step names each secret exactly once, in
  the order that section gives, that one with no key names no key, and that the step runs
  `uv run pytest -m live --tb=short --assert=plain`.
  `.github/workflows/conventions.yml` and `.github/workflows/adr-index.yml` are verbatim
  too and the template's own, each written in the form that the README of xippios/.github
  shows, with no comment. This repository runs the same two files, byte for byte, on its own
  pull requests, and the tests hold them equal.
  `siblings.yml` and the script it runs, `.github/scripts/check-siblings.sh` (executable;
  copier keeps the bit), are verbatim, and only their names hold Jinja: the name of the
  script's directory is the conditional one, so a flat render gets no empty directory. They
  stay outside `_skip_if_exists`, so `copier update` keeps a source's copy equal to the
  render, and the sibling check stands in a workflow of its own, so that `ci.yml` stays
  core's file.
- The files copied from sdk-core, `ci.yml`, `publish.yml`, `.pre-commit-config.yaml`,
  `.secrets.baseline`, `.python-version` and `LICENSE`, mirror sdk-core at the core release
  that `core_version` defaults to, at the commit of its candidate that `scripts/prove.sh`
  names until that release is on PyPI. The template carries neither core's caller of the
  retired gates nor core's pull-request template. `tests/test_template.py` pins `ci.yml` and
  `publish.yml` to core's bytes once the template's own lines below are taken out, and
  `tests/test_core_adoption.py` pins the other four to their digests. When sdk-core changes
  one of them, change it here too and bump the template: `copier update` carries it into the
  generated repositories but `.secrets.baseline`, which is the source's from 0.5.0 on and
  takes the change by a Hand-apply note. The map `SUPERSEDED` of `tests/test_citations.py`
  holds the records that sdk-core's index lists as superseded at the release the template
  adopts, which `SUPERSEDED_AT` names, and a test fails while `core_version`'s default
  names another, until the map follows that release's `docs/adr.md`. Two of the copies
  carry the exclusion of `.copier-answers.yml`, in the detect-secrets hook's `exclude` in
  `.pre-commit-config.yaml` and in `should_exclude_file` in `.secrets.baseline`, because
  the answers file names the key's variable and trips the keyword check on commit and on a
  baseline rescan alike; sdk-core carries the same exclusion since core 0.2.0.
  `publish.yml` deviates by one step, in its `tag` job before the tag, which refuses a
  pinned core (conventions §12); core has no pin to guard. `ci.yml` deviates by
  `fetch-depth: 0` and the two steps after the checkout that read the pull request, the
  CHANGELOG entry and the fixture cap; the README's The workflows of a render says what each
  does. `.github/PULL_REQUEST_TEMPLATE.md` is the template's own, no copy of core's: it links
  sdk-core's definition of done where core's copy repeats it, so it cannot lag, and the
  tests pin its sections.
- Commit subjects follow Conventional Commits: the rule binds a pull request's own commits,
  not the commit that lands the pull request on `main`, whose subject GitHub writes.
- Every PR that changes more than the documentation brings its `CHANGELOG.md` entry (Keep a
  Changelog) as a fragment, with the Hand-apply note of a change to a file under
  `_skip_if_exists`, as `changelog/README.md` lays them out; the release assembles the
  fragments into its section.
- Jinja renders with `trim_blocks` and `lstrip_blocks`, so a line holding only a block tag
  disappears, and a block tag at the end of a line takes that line's newline with it. A
  block tag therefore stands alone on its line or opens and closes there, before the
  line's end; the tests check every `.jinja` file for it. Mind blank lines in generated
  Python: the formatter check is strict.
- Keep `copier.yml`'s questions mechanical: every answer comes from the upstream
  documentation or the person who asks for the source, never a guess, as the README's
  Generating a source repository says, and ADR-0002, decision 6, says what the template asks.
- `detect-secrets` may flag a line of the template as if it held a key. Known false
  positives live in `.secrets.baseline`; after changing such a line, run
  `uv run detect-secrets scan --baseline .secrets.baseline` and commit the updated
  baseline. Never add a real value to silence it.

## Commands

The commands that develop the template, its tests, its proofs, its lint and the check of its
ADR index, stand in the README's [Developing the template](README.md#developing-the-template).

## Releases

- A release follows the README's
  [Releasing the template](README.md#releasing-the-template), and what a release adds to its
  section for the sources, the list of the answers each passes and a core release's entries,
  follows its [Updating generated repositories](README.md#updating-generated-repositories)
  and `changelog/README.md`.
- The entries of a core release stand in one fragment of the release, one entry per item of
  its Hand-apply note: first the adoption's own, in the group and with the three versions of
  conventions §15 item 9, then, for each change of the list that sdk-core keeps for the
  adoption of that release, which the README names, every entry the list names for it, each
  in the group the list gives it, each item saying where its entry holds. An entry that the
  list names without a group takes the group of what it does to the source's callers, and
  the pull request of the fragment names that group in a decision. Core's list stays the one
  place of those changes, which core's review checklist holds an adoption against: where an
  entry and the list part, the list holds, and a wrong entry is corrected in its fragment
  before the template's release.
- Never push a tag by hand, and never touch a secret.
- Never read or print `.envrc`, `.env`, or any variable ending in `_API_KEY`, `_TOKEN` or
  `_SECRET` (conventions §7).
