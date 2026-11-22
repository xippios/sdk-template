- A render depends on xippios-core 0.4.1, `core_version`'s default, by the bound
  `xippios-core~=0.4.1`, its extras likewise, and the six files it copies from sdk-core
  follow core's bytes at v0.4.1. Of them only `publish.yml` changes, titled `Publish`, its
  first line citing sdk-core ADR-0039, decision 6, in place of the record that it
  supersedes. A source takes both by its adoption, whose update passes
  `-d core_version=0.4.1` as the README's update command does.
  (https://github.com/xippios/sdk-template/issues/242, https://github.com/xippios/sdk-core/issues/407)
