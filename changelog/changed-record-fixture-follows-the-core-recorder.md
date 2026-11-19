- `/record-fixture` describes the recorder of core 0.4.0, which sends once and never
  retries, keeps the client's credentials to the base URL's origin and reads at most 32 MiB
  of a body. A recording passes the package's `client` itself, a file on another host needs
  no `auth=None`, and a recorder step of the source's own that rewrites a fixture keeps its
  client built for one attempt and writes the fixture with `write_fixture`. `max_bytes=`
  keeps a JSON array's last elements with `keep="last"` and cuts a JSON object at the array
  that `array_key=` names, and `copier update` brings the command. (ADR-0037, ADR-0040,
  ADR-0042, https://github.com/xippios/sdk-template/issues/164,
  https://github.com/xippios/sdk-template/issues/165,
  https://github.com/xippios/sdk-template/issues/166)
