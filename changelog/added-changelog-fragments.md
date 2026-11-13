- A generated repository keeps its changelog entries as fragments, one file per change
  under `changelog/`, which the release assembles into `CHANGELOG.md` as the new
  `changelog/README.md` lays out. Its `ci.yml` takes a fragment that a pull request adds or
  changes as the CHANGELOG entry, beside a line under Unreleased in `CHANGELOG.md`, and
  `copier update` brings both files, so nothing is applied by hand. The template keeps its
  own entries the same way. (https://github.com/xippios/sdk-template/issues/122)
