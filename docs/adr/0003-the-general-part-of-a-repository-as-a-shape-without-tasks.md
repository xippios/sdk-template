# ADR-0003: The general part of a repository as a shape without tasks and servers

Status: Accepted · Date: 2026-11-24 · Decided by https://github.com/xippios/sdk-template/issues/302

## Context

The template rendered one shape, a source package: a client of one upstream API, its models,
tasks, MCP server and HTTP routes, their tests and fixtures, the snapshot of the upstream's
documentation and the nightly live tests, inside the general part of a repository that every
package of the family shares: CI, the release train, the changelog with its scripts, the
decision records, the organization's checks and `/release-prep`. Two packages of the family
wrap no API of their own and need that general part alone. The shared package of the three
sources behind the USDA Foreign Agricultural Service, `sdk-usda-fas`, holds their gateway and
their snapshot kit (sdk-core ADR-0032). The host `xippios-mcp`, which serves the sources'
tools, keeps its general part by hand. The first answer on
https://github.com/xippios/sdk-template/issues/302 makes the general part of a repository a
shape of the template, without tasks and servers, which both packages take, and a trial render
for each its proof; where the host could not take it, the shape would serve the shared
package alone.

The host's tree showed what the shape has to settle: its repository is named `xippios-mcp`,
not `sdk-<slug>`; its `pyproject.toml` holds its own extras, console script and run-time
dependencies, which no question of the template holds; its upstream URLs do not exist; and
its `ci.yml` carries a job of its own, the image build.

## Decision

1. **One answer names the shape.** `shape` is a choice of two names, never a switch, asked
   first: `source`, the default, renders a source package as before, and `general` the
   general part of a repository alone. Its default is a literal, so each source records
   `shape: source` at its update and nothing else of its render changes.
2. **The general shape leaves a source's 27 files out by one list.** It renders the general
   part around the package's `__init__.py`, `_version.py` and `py.typed`, with
   `tests/conftest.py`, the Never file and `docs/layout.md`, and no client, errors, models,
   endpoint wrappers, parsers, tasks, write tasks, servers, router, packaged lists, reference
   scaffold, refresh scripts, snapshot, `.gitattributes`, live workflow, fixtures, task, live,
   built-answer or family tests, nor the four commands that add an endpoint, record a fixture
   and refresh. One conditional entry of `_exclude` in `copier.yml` names the 27 paths, which
   copier 9.19 renders and matches against the rendered paths, so a source excludes nothing and
   no file of the template changes its name.
3. **The questions of an upstream are hidden by their condition.** `upstream_url`,
   `upstream_docs_url`, `api_key_env`, `write_server`, `tenant_param`, `live_secrets`,
   `has_files` and `has_reference_data` are asked where `shape` is `source` alone, never
   answered by a default, since the two URLs have none and refuse an empty value, and copier
   records no answer whose question it does not ask. A repository of the general shape records
   `shape`, `source_slug`, `repository_name`, `import_path`, `source_name`, `core_version`,
   `core_git_ref` and `source_dependencies`.
4. **The repository's name is an answer of the general shape.** `repository_name`, default
   `sdk-<slug>`, is asked in the general shape alone and names the repository in the three URLs
   of `pyproject.toml`, the trusted publisher of `/release-prep`, the links of `README.md` and
   the title of `CLAUDE.md`. Hidden, it takes its default, so a source renders `sdk-<slug>` as
   before and records no such answer.
5. **The manifest is the repository's.** In the general shape `pyproject.toml` stands under
   `_skip_if_exists`: it renders the family's tables with the `testing` extra alone, which
   core's plugin needs, and no entry point, and the repository keeps its own dependencies,
   extras and scripts there, which no question holds. `core_version` and `core_git_ref`
   therefore act at the first render alone, and `/release-prep` takes no pin out by an update:
   the repository raises its core bound and removes a pin by hand, and `publish.yml` refuses a
   pinned release as for a source. Its `/release-prep` cites no live run and no refresh either.
6. **`source_name` describes the package.** In the general shape it is the package's
   description in a few words, which the description of `pyproject.toml` and the first
   sentence of `README.md` and `CLAUDE.md` take at the first render, and no rendered file
   calls the package a source of an upstream.
7. **One test of the package's own.** The general shape renders `tests/test_package.py`, which
   imports the package and compares its version with its distribution's, under
   `_skip_if_exists`, so a repository that holds a test of that name keeps its own.
8. **No rendered file holds a job of one repository.** No answer renders a repository's own
   job, the host's image build among them: such a job stands in a workflow of the
   repository's own beside the rendered ones.
9. **Two consumers.** `sdk-usda-fas`, nested as `xippios.usda.fas` in the repository
   `sdk-usda-fas`, and `xippios-mcp`, flat as `xippios.mcp` in the repository `xippios-mcp`,
   take the general shape. The trial renders with each one's answers, the host's over its
   own tree, are reported in
   https://github.com/xippios/sdk-template/blob/main/docs/reports/2026-11-24-trial-renders-of-the-general-shape.md:
   the shared package's render passes every check. The host keeps every file it owns, and
   its checks pass once its own `pyproject.toml` leaves the organization's three scripts,
   `scripts/adr_index.py`, `scripts/changelog_assemble.py` and `scripts/release_prepare.py`,
   out of ruff, as the rendered manifest does; until then ruff fails on those three.

## Consequences

- Every source's update adds `shape: source` to `.copier-answers.yml` and changes no other
  file.
- `scripts/prove.sh` proves two more shapes of the invented source, `--general`, a
  publisher's shared package with a nested import path, and `--general-flat`, a flat package
  in a repository not named `sdk-<slug>`, and the template's tests render both in a module of
  their own beside the source's variants.
- The host takes the shape by its first render over its tree, which keeps its manifest,
  `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `tests/conftest.py`, its own
  `tests/test_package.py` and its baseline, and writes the template's workflows, scripts and
  commands. Before it, the host moves its image job into a workflow of its own; with it, it
  replaces its one trigger file of the organization's checks by the two rendered ones and
  leaves the three scripts of the organization out of its own ruff, as the rendered manifest
  does.
- `sdk-usda-fas` is made from the template by the general shape, and nothing of the template
  names its gateway's key: a placeholder of that key in its offline tests is its own, or
  core's plugin's.
- Core's family check holds no repository of the general shape, which renders no
  `tests/test_family.py`.
