# Changelog fragments

Every change to the template brings its changelog entry as a file of its own in this folder, a
fragment, so that two pull requests never edit the same lines of `CHANGELOG.md`. The release
assembles the fragments into its section of `CHANGELOG.md` and deletes them. This README stays.
A generated repository gets the same folder, its rule in `template/changelog/README.md`.

## A fragment

- **Its name.** `changelog/<group>-<slug>.md`, one file per change. `<group>` is one of
  `added`, `changed`, `fixed`, `removed`, `security` and `breaking`, and `<slug>` names the
  change in lowercase letters and digits, its words joined by hyphens.
- **Its bullet.** The file holds one bullet, as it will stand in the release's section: its
  first line starts with `- `, and a line it continues is indented by two spaces. The lead
  sentence says what changes for a generated repository, or for this one, and up to two more
  say how it is used or what it replaces. Its citations close it in parentheses: an
  `ADR-NNNN` it follows, and the URL of the issue it answers.
- **Its Hand-apply note.** A change to a generated file under `_skip_if_exists` in
  `copier.yml`, which `copier update` never touches once it exists, adds one line under its
  bullet, indented by two spaces, `` - Hand-apply: `<path>` — <what> — <why> ``: the port a
  source makes by hand in its adoption. The note continues on lines indented by four spaces,
  and a change has one at most. A change that matters to new repositories only, such as a
  scaffold's starting text, says so in its bullet instead.
- **When.** Every pull request that changes more than the documentation adds one. A pull
  request that changes an entry not yet released edits its fragment.

`changelog/changed-fixture-path-in-claude-md.md`:

```markdown
- The generated `CLAUDE.md` gives the fixtures' path as `<wrapper>/<case>.json`, as
  conventions §10 does. (https://github.com/xippios/sdk-template/issues/99)
  - Hand-apply: `CLAUDE.md` — write the `fixtures/` line's path as `<wrapper>/<case>.json`
    — conventions §10 names a fixture's directory after its wrapper.
```

## The release

The release's pull request writes `## [X.Y.Z] - YYYY-MM-DD` into `CHANGELOG.md` in place of
`## [Unreleased]`, or above the last release where there is none, and deletes the fragments
it took. The section holds:

- the groups in the order above, each under its heading, `### Added`, `### Changed` and so
  on, and only those with an entry;
- in each group the fragments newest first, by the commit that added each, then the entries
  that `## [Unreleased]` held under that heading;
- after them, any other group that `## [Unreleased]` held, as it stood, such as the
  `### Hand-apply` list that closed a release before the notes;
- each Hand-apply note under its bullet.

The section may gain a lead paragraph above its groups. Its merge runs
`.github/workflows/release.yml`, which tags `vX.Y.Z` from that heading.
