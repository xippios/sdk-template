- The generated `.gitattributes` keeps `tests/fixtures/files/**` byte for byte where
  `has_files` is true, as it keeps `docs/upstream/**`: a sample is a byte-exact cut whose
  sha256 its provenance row states, and git under `core.autocrlf` converted a sample's line
  endings. `copier update` brings the line, so nothing is applied by hand.
  (ADR-0020, https://github.com/xippios/sdk-template/issues/62)
