- This repository calls the organization's checks on its own pull requests from
  `.github/workflows/organization.yml`, byte for byte the file it renders into a source, so
  `conventions / conventions` and `adr-index / adr-index` report beside `ci` and the
  template's release pull request gets the conventions review. A test holds the two files
  equal, and a generated repository is unchanged.
  (https://github.com/xippios/sdk-template/issues/151)
