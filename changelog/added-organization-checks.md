- A generated repository calls the organization's checks of a pull request from
  `.github/workflows/organization.yml`: the conventions review as the job `conventions`,
  passed `ANTHROPIC_API_KEY` alone, and the check of the ADR index as the job `adr-index`,
  which runs the repository's own `scripts/adr_index.py --check`. The file has a name of its
  own because GitHub keeps a workflow's state by its path and the sources disabled the old
  caller, `gates.yml`, by hand. A source that still holds `gates.yml` loses it at
  `copier update`, which renders it no longer, and gets the new workflow enabled, with no
  setting to change. (https://github.com/xippios/sdk-template/issues/129)
