# Changelog

All notable changes to sdk-template are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the template uses
[Semantic Versioning](https://semver.org/). Each change brings its entry as a fragment under
`changelog/`, which the release assembles into its section here, as
[changelog/README.md](changelog/README.md) lays it out, with a `Hand-apply:` note under the
bullet of a change that a source ports by hand.
[Updating generated repositories](README.md#updating-generated-repositories) in the README
says how a source takes a release.

This file holds the releases after 0.4.0. The sections of 0.4.0 and of every release before
it stand in `CHANGELOG.md` at the tag `v0.4.0`:
https://github.com/xippios/sdk-template/blob/v0.4.0/CHANGELOG.md.

## [0.4.1] - 2026-11-23

A generated repository takes xippios-core 0.4.1 with this release, and its scripts run on
core's frames: the capture script declares the source's snapshot and the reference script
its packaged lists for `xippios.core.refresh`, the tests collect core's check of a built
answer and its nightly comparison of the packaged lists, and the commands name core
0.4.1's helpers and recorder. A render carries the organization's one ADR index script and
its release script, and starts the organization's checks from one trigger file each in
place of `organization.yml`. A source takes this release together with xippios-core 0.4.1
in one adoption before its next release, with the README's update command,
`copier update --defaults --vcs-ref=v0.4.1 -d core_version=0.4.1 -d core_git_ref=`, ports
what the Hand-apply notes name and copies the entries for core 0.4.1's changes from the
note that carries them. The release adds no question and no choice, so every source runs
that command as it stands.

### Added

- From this release on, a release of the template that adds a question to `copier.yml`, or
  a choice to one, ends its section with `### Answers each source passes`: an item per
  source whose update passes an answer that the README's update command does not, holding
  that update's command whole, with every `-d` argument it passes. An adoption copies its
  command from that list, never from the prose of an entry, and a source that the list
  leaves out runs the README's update command as it stands.
  (https://github.com/xippios/sdk-template/issues/245)
- A render collects xippios-core 0.4.1's check of a built answer's mark, as
  sdk-core ADR-0049 records it, in `tests/test_built_answers.py`, its one line followed by
  the source's `READERS` and `ALLOWED`, and `/add-endpoint` says how a test marks an answer
  it builds. The module is the source's once rendered, so `copier update` creates it where a
  source has none and leaves the source's declarations alone after. The template's rendered
  tests build no answer, so a new source passes the check before its first test.
  (conventions §10, https://github.com/xippios/sdk-template/issues/271)
  - Hand-apply: `CLAUDE.md` — name `test_built_answers.py` under `tests/` in the Layout,
    and `tests/test_built_answers.py` after `tests/test_live.py` among the files the
    package fills, as a render with the package's answers has them — the update creates the
    module and never writes the package's `CLAUDE.md`.
    `tests/test_built_answers.py` — where the source holds a module of that name of its
    own, as sdk-cashctrl does, replace its own check by the collecting line with the
    source's `READERS` and `ALLOWED` below it — the update keeps a file of that name as it
    stands.
- The rendered `tests/test_live.py` collects xippios-core 0.4.1's nightly comparison of each
  packaged list with the list upstream serves now, that of sdk-core ADR-0055, by one star
  import, with `LIVE_LISTS` and `NO_LIVE_LIST` declared empty at its top level, and a render
  without reference data collects none. `/refresh-reference-data` says that a new packaged
  list takes its entry in `LIVE_LISTS`, or in `NO_LIVE_LIST` with the reason it is not
  compared, which core's family check holds.
  (https://github.com/xippios/sdk-template/issues/252)
  - Hand-apply: `tests/test_live.py` — add `from xippios.core.testing.live import *  # noqa: F403`
    with `LIVE_LISTS` and `NO_LIVE_LIST` at the top level, an entry for each packaged list,
    delete the source's own comparison of a packaged list and move a skip at the module's
    import into the tests or fixtures that need it — core's family check, by
    sdk-core ADR-0055, fails a packaged list in neither declaration and a module that skips
    at its import.
- A render carries `scripts/release_prepare.py` and the assembler it loads by its path,
  `scripts/changelog_assemble.py`, the organization's one version of each, and
  `/release-prep` runs `python3 -I scripts/release_prepare.py <version> --date <YYYY-MM-DD>`
  in place of the assembly by hand. The script writes the release's section of
  `CHANGELOG.md` from the fragments, removes them and sets the version in `pyproject.toml`
  and on the package's own entry in `uv.lock`, with no `uv lock`, and a second run writes
  nothing. The rendered `pyproject.toml` leaves both scripts out of ruff, and its strict mypy
  checks them as they stand, with no override.
  (https://github.com/xippios/sdk-template/issues/247)
  - Hand-apply: `CLAUDE.md` — name `scripts/changelog_assemble.py` and
    `scripts/release_prepare.py` after `scripts/adr_index.py` among the files the update
    writes again, and lay both out under `scripts/` in `## Layout`, as a render has them —
    every update writes the two scripts again, and the Layout names each script the
    repository holds.

### Changed

- The rendered `/record-fixture` names `Rewrite`, the type of a source's rewrite step that
  `xippios.core.testing` exports, and says that the step writes `REDACTED` for a field of a
  request that the fixture must not keep and drops none, as sdk-core ADR-0048 records it, so
  that core's census of built answers compares a replay with its recording key by key.
  (conventions §10, https://github.com/xippios/sdk-template/issues/271)
- A new source's write scaffold declares its preview, `WritePreview` in `tasks_write.py`,
  tagged `performed: Literal[False]` with `reads`, the operations the preview read, as
  sdk-core ADR-0050 records it, and `/add-endpoint` asks each write task's docstring to say
  whether its preview reads and at what cost. The write server's test that `/add-endpoint`
  gives a source's first write task passes `preview_reads=True`. The scaffold matters to new
  repositories only, since `tasks_write.py` is the source's once rendered.
  (conventions §8, https://github.com/xippios/sdk-template/issues/271)
- The rendered `scripts/refresh_reference.py` is a short script on xippios-core 0.4.1's frame,
  `xippios.core.refresh` of sdk-core ADR-0051, which fetches the lists a source declares, one
  `Listed` each, writes their files, the provenance rows and `enums.py`, takes `--only` and
  `--render-only` and counts a request that ended in a transport error as sent. A
  multi-tenant render fetches through the reserved tenant's client and needs none of its
  variables for `--render-only`. `/refresh-reference-data` says what a source declares in a
  `Listed` and that the run writes the list's provenance row.
  (https://github.com/xippios/sdk-template/issues/239)
  - Hand-apply: `scripts/refresh_reference.py` — declare each list as a `Listed` in one
    `LISTS`, with an `origin` for each list whose provenance row names more than its
    endpoint, hand them to `xippios.core.refresh.run` with the package, `PACKAGED_LISTS`,
    the client and the quota header, delete the script's own fetches, writes, `render`,
    `Meter`, `metered` and `--only`, the port of the 0.4.0 metering among them, and run it
    once with `--render-only` — core 0.4.1 carries the frame of sdk-core ADR-0051, which
    counts a request that fails in transport as sent and writes the provenance rows from
    the declarations.
    `src/xippios/<package>/params.py` — where the docstring of `PACKAGED_LISTS` names the
    script's `LISTS`, `ID_LISTS` and `TABLES`, name its one `LISTS` of `Listed` — the port
    leaves the script one declaration.
- A render's `scripts/refresh_upstream.py` declares the source's `Snapshot` as `SNAPSHOT`,
  which the frame of xippios-core 0.4.1, `xippios.core.refresh`, fetches, checks and writes
  into `docs/upstream/`, in place of the template's skeleton of the whole capture. The
  rendered `/refresh-upstream` and `CLAUDE.md` say what a source fills in the declaration,
  and the converter its `reduce` uses is pinned in the dev group of `pyproject.toml` alone,
  since the script runs in the project's environment with no `# /// script` block. An
  adoption deletes its port of the skeleton and declares its pages, attribution and hooks
  on core's frame, whose `FETCHED.md` holds the table `Not fetched` and the row of
  `OBSERVED.md`, so it needs no decision of its own for either.
  (https://github.com/xippios/sdk-template/issues/235, https://github.com/xippios/sdk-template/issues/240, https://github.com/xippios/sdk-core/issues/363)
  - Hand-apply: `scripts/refresh_upstream.py` — delete the port of the 0.4.0 skeleton, its
    `# /// script` block among it, and declare the source's `Snapshot` as `SNAPSHOT` with
    its pages, attribution, pages left out, vocabulary, capture and hooks, run by
    `run(SNAPSHOT)` under `if __name__ == "__main__":` alone, as the source's part of
    "Adopting core 0.4.1" in sdk-core's `docs/handover.md` lists it — core's frame writes
    the table `Not fetched` and the row of `OBSERVED.md` from the first refresh on, so a
    source's row for the table closes with its patch.
    `CLAUDE.md` — write the Layout's line of `scripts/refresh_upstream.py` as the render
    has it — the line calls the source's filled script the template's skeleton.
- A render depends on xippios-core 0.4.1, `core_version`'s default, by the bound
  `xippios-core~=0.4.1`, its extras likewise, and the six files it copies from sdk-core
  follow core's bytes at v0.4.1. Of them only `publish.yml` changes, titled `Publish`, its
  first line citing sdk-core ADR-0039, decision 6, in place of the record that it
  supersedes. A source takes both by its adoption, whose update passes
  `-d core_version=0.4.1` as the README's update command does.
  (https://github.com/xippios/sdk-template/issues/242, https://github.com/xippios/sdk-core/issues/407)
- An adoption of this release brings xippios-core 0.4.1, and the Hand-apply note below
  carries, ready to adapt, the entries that a source's changelog takes for it, first the
  adoption's own, `changed` with its three versions, then for each change of core 0.4.1
  that the source's callers see the entries that the list under "Adopting core 0.4.1" of
  sdk-core's `docs/handover.md` names, each in its group, and in `changed` the one it names
  without a group. The pull request that brings a change, the adoption's or a later one
  of the source's patch, copies the entry where it holds, as a fragment of its own, and
  words it for the source's own tasks and names. Where an entry and the handover's list
  part, the list holds, and the source corrects its fragment before its release, which
  rewords no entry. (https://github.com/xippios/sdk-template/issues/238,
  https://github.com/xippios/sdk-template/issues/280)
  - Hand-apply: `changelog/changed-<slug>.md` — The package depends on
    `xippios-core~=0.4.1`, its extras likewise, is updated to sdk-template v0.4.1 and
    applies conventions 1.29. (`https://github.com/xippios/<repository>/issues/<n>`) —
    every source's adoption, by conventions §15 item 9, its citation the URL of the
    adoption's issue, and `breaking` in place of `changed` where the same pull request
    brings core 0.4.0 too, a core minor.
    `changelog/added-<slug>.md` — `<tool>` takes `offset`, the rows of a cut answer already
    shown, and answers the rows after them by running its task again. Every page carries
    its note, the last one too, and the note of every page but the last names the `offset`
    to continue with, so an answer without a note is whole.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap in `MCP_CAPS` is
    `ResultCap(paged=True)`.
    `changelog/changed-<slug>.md` — `<tool>` shows the newest rows of a cut series, ordered
    oldest first, in place of the oldest, and its `offset` walks to older rows.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap keeps the last
    rows, `ResultCap(keep="last")`.
    `changelog/changed-<slug>.md` — The note of a cut answer of `<tool>` names the `offset`
    to continue with in place of the narrower query it named before.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose note named a way
    around the cut before its cap took `paged=True`.
    `changelog/added-<slug>.md` — The answer of `<task>` names each `<parameter>` code it
    was called with in `meta.names`, by the name that its packaged list holds,
    `{"<parameter>": {"<code>": "<name>"}}`.
    (https://github.com/xippios/sdk-core/issues/316, https://github.com/xippios/sdk-core/issues/310)
    — each task that takes a country, area, reporter or partner code, by `names_codes`.
    `changelog/changed-<slug>.md` — `<task>` withholds its answer for a `<parameter>` code
    that its packaged list lacks, with the list's refusal, where it answered for such a
    code before. (https://github.com/xippios/sdk-core/issues/316) — each task that sent
    such a code upstream unchecked, as sdk-faostat's `get_series` sent a code of a domain
    outside its five area tables.
    `changelog/breaking-<slug>.md` — The tasks refuse an ISO alpha-3 code, which they
    resolved before the call, and the refusal names the UN Comtrade code it stands for,
    `"CHE"` refused naming `757 (Switzerland)`. The refusal ends with its hint and its
    reason, without the sentence that the packaged list may be out of date.
    (https://github.com/xippios/sdk-core/issues/375, https://github.com/xippios/sdk-core/issues/316)
    — sdk-comtrade alone, whose release this makes a minor by conventions §12.
    `changelog/changed-<slug>.md` — `<task>` refuses a query over upstream's limit of `<n>`
    records per call with core's `QueryTooLarge`, an `InvalidRequestError` whose message
    gives the count, the limit and what narrows the query, and answers a count of 0 with
    its empty answer, sending no data request. (https://github.com/xippios/sdk-core/issues/317)
    — each task that refuses with `QueryTooLarge`, by `fetch_counted` or by its `classify`
    of upstream's refusal, whose message names the request too, and sdk-comtrade's entry
    adds that the answer of `get_data` carries the count as `meta.total`.
    `changelog/breaking-<slug>.md` — `xippios.comtrade.errors` holds no `QueryTooLarge` of
    its own any more, so an import of it fails, and a caller catches core's
    `xippios.core.QueryTooLarge`, which the tasks raise.
    (https://github.com/xippios/sdk-core/issues/317) — sdk-comtrade alone, in the minor of
    its alpha-3 codes.
    `changelog/changed-<slug>.md` — `<task>` refuses a `<parameter>` code that its packaged
    list lacks by core's check, which names the list, its fetch date and the closest codes,
    and refuses a value of the other type than the list's codes with
    `InvalidRequestError`, naming the integer or the text to pass and ending with the
    task's reason. Another text given for integer codes is refused naming the codes that the
    task's strategy finds for it, else those whose name holds it. A value of the hint table
    of `<parameter>` is refused with its hint and its reason, without the sentence that the
    packaged list may be out of date. (https://github.com/xippios/sdk-core/issues/313) —
    each argument that `PackagedList.codes(...).check` now checks, worded by the refusals
    whose wording or class the tests of the port change, the hint table's sentence where
    the source keeps one.
    `changelog/changed-<slug>.md` — `<task>` refuses a `since` it cannot read in core's
    wording, `since must be the meta.vintage text of an earlier call, an ISO date and time without a time zone such as '2026-10-06T08:00:00'`,
    its class and its two reasons kept. (https://github.com/xippios/sdk-core/issues/318) —
    sdk-usda-esr alone, since sdk-usda-psd's wording stays as it is.
    `changelog/changed-<slug>.md` — `<task>` refuses a range over its ceiling of `<n>`
    `<unit>` in core's wording before the first request, naming the range, the ceiling, its
    unit, where the MCP server's ceiling is lower the option that raises it, and that
    nothing was sent, its class `InvalidRequestError` and the option's name unchanged. A
    request after the first that fails raises its error, its class kept, naming the periods
    answered before it by their count, the first and the last, and the task returns nothing.
    (https://github.com/xippios/sdk-core/issues/315) — each task on `fetch_periods`, but
    sdk-usda-nass's split of `year__GE` alone, whose refusal of its own says that the count
    was sent.
    `changelog/breaking-<slug>.md` — `tasks.<name>` and `tasks.set_<name>` are removed, so
    a caller's call of either fails, and one `Ceiling` of core's holds the task's ceiling of
    `<n>` `<unit>` in their place. (https://github.com/xippios/sdk-core/issues/315) —
    sdk-usda-nass's `split_ceiling` and `set_split_ceiling` and sdk-usda-gats's
    `series_ceiling` and `set_series_ceiling`, each making its source's release a minor by
    conventions §12, unless its port keeps the two names.
    `changelog/added-<slug>.md` — The preview of `<write task>` carries `reads`, the
    operations it read, `[]` for none, and the task's docstring says whether its preview
    reads first and what the read costs. (https://github.com/xippios/sdk-core/issues/182) —
    each write task, its preview held by `assert_write_tools` with `preview_reads`.
- The rendered `/add-endpoint` and `/record-fixture` describe the helpers and the recorder of
  xippios-core 0.4.1, which a source adopts with this release. `/add-endpoint` refuses a code
  that a packaged list lacks by the `check` of `PackagedList.codes(...)` in place of an
  `UnknownCode` raised by hand, names `names_codes` and `UNNAMED_CODES`,
  `ResultCap(paged=True)` and `keep="last"`, `newer_than`, `fetch_counted` with
  `QueryTooLarge` and `Ceiling` with `fetch_periods`, and in a render without reference data
  names no helper of a packaged list and no reference lookup. `/record-fixture` names
  `rewrite=`, `send_once` in place of a client built for one attempt, the recorder's refusal
  of a 1xx or a 3xx and `record_task` for every exchange of a task.
  (https://github.com/xippios/sdk-template/issues/250, https://github.com/xippios/sdk-template/issues/270)
- The comment above the changelog step of the rendered `ci.yml` and the rendered
  `/release-prep` state conventions §15 item 9 as it now reads: an adoption's fragment names
  the core bound, the template's tag and the conventions' version as they stand after the
  update, changed or not, `breaking` where it brings a core minor and `changed` where it
  brings none. `/release-prep` takes each entry as its fragment reads, under its fragment's
  group, and rewords or regroups none, since a wrong entry is corrected in its fragment
  before the release.
  (https://github.com/xippios/sdk-core/issues/355, https://github.com/xippios/sdk-template/issues/251)
- The template renders no test of the row of `OBSERVED.md` in `docs/upstream/FETCHED.md`,
  since xippios-core 0.4.1's family check holds that row in every source that keeps the
  file. sdk-usda-esmis, sdk-usda-wasde, sdk-usda-esr and sdk-cashctrl delete what their
  `tests/test_observed.py` holds of the row in their patches, as core 0.4.1's changelog lists
  for each. sdk-eurostat's test of the row in `tests/test_refresh_upstream.py` holds the row
  that its own capture script writes, not the committed one, and stays with that script.
  (https://github.com/xippios/sdk-template/issues/236)
- The rendered `/release-prep` cites the count of the live run's requests from the line
  `requests sent by the live run: <n>` that xippios-core 0.4.1's testing plugin prints in the
  log of `live.yml`, from a green run on the commit of `main` that the release starts from
  and never from a run on an earlier commit. The header of the rendered `tests/test_live.py`
  points to that line and states no count of its own.
  (https://github.com/xippios/sdk-core/issues/382, https://github.com/xippios/sdk-template/issues/237)
  - Hand-apply: `tests/test_live.py` — add to the module's docstring that core's testing
    plugin prints the run's requests as `requests sent by the live run: <n>`, the count in
    the log of `live.yml` that `/release-prep` cites, and delete a count the docstring
    states by hand — the plugin counts every run, so a count written by hand goes stale
    with the next live test.
- `scripts/adr_index.py` is the one version that the organization's repositories share, which
  opens each line of `docs/adr.md` with the anchor that a citation such as `docs/adr.md#0014`
  links to and lists the records in force before the superseded ones. The rendered
  `pyproject.toml` leaves the script out of ruff while mypy checks it, and every command runs
  it as `python3 -I`. A source writes its index again with the new script in its adoption pull
  request, since the check `adr-index` fails on the index that the old one wrote.
  (https://github.com/xippios/sdk-core/issues/357, https://github.com/xippios/sdk-template/issues/246)
  - Hand-apply: `CLAUDE.md` — write the index command of `## Commands` as
    `python3 -I scripts/adr_index.py --check` — the check `adr-index` runs the script
    isolated, and people run it as the check does.
    `docs/adr.md` — write it again with `python3 -I scripts/adr_index.py` — the new script
    opens each line with its record's anchor and lists the superseded records last.
- A generated repository starts the organization's checks from one trigger file each,
  `conventions.yml` and `adr-index.yml`, in place of `organization.yml`, which
  `copier update` deletes, so each check runs once after the adoption and keeps its name,
  `conventions / conventions` and `adr-index / adr-index`, while a push to `main` reports
  `range / range`. A variable `WORKFLOW_<NAME>` of `off`, the repository's over the
  organization's, switches off either check, `live.yml`, now titled `Live tests`, or
  `siblings.yml`, while `ci.yml` and `publish.yml` take no switch. This repository runs
  the same two trigger files on its own pull requests.
  (https://github.com/xippios/sdk-template/issues/249)
  - Hand-apply: `CLAUDE.md` — in the Layout's `.github/workflows/` entry, name
    `conventions.yml` and `adr-index.yml` in place of `organization.yml`, as a render of
    this release words them — the update deletes `organization.yml` and renders the two
    trigger files.
- The generated `CLAUDE.md` names, beside the files a source fills, the files that
  `copier update` writes again, `mcp.py` among them, so that a source keeps no text of its
  own in them. Its code rule on the three layers lets the tasks call reference data only
  where `has_reference_data` is `true`. A test holds the list equal to every rendered file
  outside `_skip_if_exists`, by path, so a file the template adds or renames outside
  `.github/` and `.claude/` is named in the same change.
  (https://github.com/xippios/sdk-template/issues/243, https://github.com/xippios/sdk-template/issues/244)
  - Hand-apply: `CLAUDE.md` — in `## Template updates`, follow the paragraph on the files
    the package fills with the paragraph on the files the update writes again, as a render
    with the package's answers has it, and where `has_reference_data` is `false`, as in
    sdk-x and sdk-google-mail, end the three-layer rule's clause at "the tasks call only
    wrappers" — `mcp.py` and the other files named there are written again at every
    update, and a source without reference data has none for its tasks to call.

### Fixed

- A multi-tenant source without a key names its live secrets after the reserved tenant's
  credential under `xippios_placeholder_key_envs` in `pyproject.toml`, since its own auth
  reads them, so core's plugin sets each in every test not marked live. A comment under
  `[project.scripts]` says that a script of the package's own goes after the servers' entry
  points, where an update keeps it while the template's lines beside it stay. Neither adds
  a question or a hidden answer, and sdk-google-mail, which wrote both by hand, keeps its
  script and list at its adoption and takes the render's comment above the list where its
  own wording conflicts. (https://github.com/xippios/sdk-template/issues/241)
