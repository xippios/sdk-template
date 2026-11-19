- `rate_limit_provenance` offers `below-documented`, for a pace set under a limit that
  upstream documents, on recorded refusals or from a limit stated in another unit than
  requests: the generated `_client.py` says so above `RATE_LIMIT`, and the `Rate limit`
  row of the generated `CLAUDE.md` leaves the source a comment for that limit beside the
  pace, where `documented` rendered a pace within the limit and `self-imposed` no limit at
  all. A source in that place, as sdk-comtrade and sdk-google-mail are, passes
  `-d rate_limit_provenance=below-documented` to the update that takes this release.
  (ADR-0010, https://github.com/xippios/sdk-template/issues/46)
  - Hand-apply: `src/xippios/<package>/_client.py` — where the answer becomes
    `below-documented`, write the comment above `RATE_LIMIT` as a render has it, the
    documented limit and the reason for the lower pace after it — the update never
    rewrites the comment that the earlier answer rendered.
    `CLAUDE.md` — where the answer becomes `below-documented`, the `Rate limit` row names
    the pace, then that it is set under the limit upstream documents, with that limit in
    upstream's own unit and why the pace is under it — the row gives both numbers.
