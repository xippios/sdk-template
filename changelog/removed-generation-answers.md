- `copier.yml` no longer asks `api_base_url`, `api_key_location`, `api_key_name`,
  `rate_limit_per_minute`, `rate_limit_burst` and `rate_limit_provenance`, and refuses
  `has_reference_data: true` beside `tenant_param`: an update drops the recorded answers from
  `.copier-answers.yml` and the fixture cap's `LEVEL` variable from `ci.yml`, and changes no
  file a source fills. A new repository's `_client.py` keeps a marked place for the base URL,
  the key's auth and the pace, as its `CLAUDE.md` does for their rows, and its first pull
  request fills them from upstream's documentation as it fills `tasks.py`, which matters to
  new repositories only. The reference script's multi-tenant branch and the Layout entry of
  a flat source with a dependency in the generated `CLAUDE.md` leave with them.
  (https://github.com/xippios/sdk-template/issues/301)
