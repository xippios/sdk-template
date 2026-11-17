- The Hand-apply notes of 0.3.3 leave no decision open: where a source keeps one module per
  service, its own `api/` entry of the `CLAUDE.md` layout stands in place of the
  template's, and `## Documents` goes above the README's licence heading whatever its
  spelling. The same adoption rewrites the source's own files that still speak of the
  process before the repository worked alone, as the note below lists them.
  (https://github.com/xippios/sdk-template/issues/152,
  https://github.com/xippios/sdk-eurostat/issues/22)
  - Hand-apply: `CLAUDE.md` — where `api/` keeps one module per service, keep the layout's
    own `api/` entry in place of the template's, one module per operation, and take the
    sentence on one module per service below the layout as 0.3.3 says, and in the
    specifics section cite a decision by its URL or say it, never by a first name, a date
    or a row of the retired queue — the template's entry is wrong for such a source, and a
    reader of the repository resolves neither a row nor a first name.
    `README.md` — put `## Documents` directly above the licence's heading, `## Licence`,
    `## License` or however the source spells it — the section is the README's list of
    the documents, whatever the heading after it is called.
    `docs/handover.md` — delete it, and move a fact a reader of the repository needs into
    the `README.md` or the `CLAUDE.md` — the family's rules asked for it up to 0.3.2, it
    names a directory, a script, branches and classes of a merge outside the repository,
    and the generated `/release-prep` says the hand-over is sdk-core's file and not one a
    source must have.
    `CHANGELOG.md` — reword a line under `## [Unreleased]`, such as the one the adoption
    of 0.3.1 wrote, that names a class of a merge, an automatic merge, a reviewer's
    approval or a login — the section becomes the next release's tag message.
    `src/` — where a docstring or a README cites a row of the retired queue, cite the
    decision by its URL or say it — a reader of the repository cannot resolve the row.
