- The scaffold's first entry in the generated `CHANGELOG.md` names each source package the
  source depends on with its release and its bound, such as `xippios-usda-esmis` 0.1.0
  (`~=0.1.0`), as a dependent names its dependency's release. It matters to new
  repositories only, since a source's `CHANGELOG.md` is its own once rendered.
  (ADR-0021, https://github.com/xippios/sdk-template/issues/53)
