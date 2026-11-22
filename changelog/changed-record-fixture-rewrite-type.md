- The rendered `/record-fixture` names `Rewrite`, the type of a source's rewrite step that
  `xippios.core.testing` exports, and says that the step writes `REDACTED` for a field of a
  request that the fixture must not keep and drops none, as sdk-core ADR-0048 records it, so
  that core's census of built answers compares a replay with its recording key by key.
  (§10, https://github.com/xippios/sdk-template/issues/271)
