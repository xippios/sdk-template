- `copier.yml` no longer asks `gateway`, `tenant_credential_env` or `human`: an update drops
  the three recorded answers from `.copier-answers.yml` and copies `.github/CODEOWNERS` as it
  stands, each path that steers a source owned by `jdidaskalu`. The scaffold's `_client.py`
  renders no gateway, so a source behind api.data.gov keeps `api_key_env` and imports the
  gateway from its publisher's shared package, `xippios.usda.fas`. A multi-tenant source whose
  tenants hold no key names that credential's variables in `live_secrets`, the reserved
  tenant's first, as sdk-google-mail's update passes them,
  `-d "live_secrets=[GOOGLE_DEMO_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]"`, by
  the release's list of the answers each source passes, which keeps the bytes of its
  `live.yml`. (ADR-0002,
  https://github.com/xippios/sdk-template/issues/301,
  https://github.com/xippios/sdk-template/issues/302)
  - Hand-apply: `src/xippios/<import path>/_client.py` — in sdk-usda-psd, sdk-usda-esr and
    sdk-usda-gats, import `Gateway` from `xippios.usda.fas` in place of
    `xippios.core.data_gov` — the gateway leaves core for its publisher's shared package, and
    the file is the source's once rendered.
