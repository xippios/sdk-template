- `core_version` defaults to 0.4.0, the xippios-core release the template adopts, so a new
  render depends on `xippios-core~=0.4.0`, its extras likewise, and the files a render
  copies from sdk-core take their bytes at its tag v0.4.0, where `publish.yml`'s comments
  name a maintainer in place of the human. A source passes `-d core_version=0.4.0` to the
  update that takes this release, which brings the copies, so nothing is applied by hand.
  (ADR-0039, https://github.com/xippios/sdk-template/issues/190)
