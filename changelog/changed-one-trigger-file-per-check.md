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
