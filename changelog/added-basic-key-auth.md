- `api_key_location` offers `basic`: the generated `_client.py` sends the key as the HTTP
  basic user name with no password, by core's `BasicKeyAuth`, which xippios-core 0.3 has,
  and the `Credentials` row of the generated `CLAUDE.md` says so; no header or parameter
  name is asked. A source whose upstream takes its key so, as sdk-cashctrl's does, passes
  `-d api_key_location=basic` to the update that takes this release.
  (https://github.com/xippios/sdk-template/issues/162)
  - Hand-apply: `src/xippios/<package>/_client.py` — where the answer becomes `basic` and
    the client sends one key, import `BasicKeyAuth` from `xippios.core` and write
    `auth = BasicKeyAuth(API_KEY_ENV, source=SOURCE)` in place of the auth the earlier
    answer rendered; a source that builds its clients' auth by its own lines keeps them —
    the update never rewrites the client.
    `CLAUDE.md` — where the answer becomes `basic`, the `Credentials` row says that the
    key is sent as the HTTP basic user name, with no password — the row named the earlier
    answer's header or parameter.
