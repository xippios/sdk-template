- A generated repository's README lists its documents under `## Documents`, each by its
  file on GitHub, and links its license by URL, and its `CLAUDE.md` says what the package
  wraps, its layout, its commands and its code rules, links that section, and names no
  branch, no tool that opens a pull request, no merge and no reviewer. `.claude/family.md`
  leaves, its rules now in the `CLAUDE.md`, the commands or sdk-core's documents, and
  `/add-endpoint` and `/release-prep` follow: neither calls a hand-written enumeration
  unexported any more, and the live run takes `--assert=plain`. The README's line above the
  status table reads as a released README does, for new repositories only.
  (https://github.com/xippios/sdk-template/issues/128,
  https://github.com/xippios/sdk-template/issues/82)
  - Hand-apply: `README.md` — add `## Documents` above `## Licence` with the six items of
    `template/README.md.jinja` at this tag, `sdk-<slug>` in the source's own two, link the
    license as `https://github.com/xippios/sdk-<slug>/blob/main/LICENSE`, and in the
    comment above the status table name `tasks_write.__all__` beside `tasks.__all__` — the
    README is the one list of the repository's documents, PyPI shows it with no repository
    around it to resolve a relative link, and core's family check reads both task lists.
    `CLAUDE.md` — delete the `@.claude/family.md` line and the sentence before it that names
    the file, then rewrite the rest once after `template/CLAUDE.md.jinja` at this tag. Take
    the intro's link to `README.md#documents`, the Layout's entries for `models.py`, `api/`,
    `scripts/adr_index.py`, `docs/`, `changelog/` and `CHANGELOG.md`, its
    `.github/workflows/` entry with `organization.yml` and the comma before `siblings.yml`,
    and the sentence on one module per service below it, the Commands with
    `--assert=plain` and the live run's secrets named after its keys, and the sections Code
    rules, Never, Template updates and When something is unclear, the secrecy rule naming
    each of the source's credential variables. Keep the table, the Layout's own entries and
    the specifics as the source wrote them, and move into the file any line the source had
    added to its `.claude/family.md` — the update deletes `.claude/family.md`, a source's
    own lines in it included, so its rules stand in the `CLAUDE.md` or in sdk-core's
    documents, and no file of the source names a branch, a merge or a reviewer.
