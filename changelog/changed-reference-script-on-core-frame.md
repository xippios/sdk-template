- The rendered `scripts/refresh_reference.py` is a short script on xippios-core 0.4.1's frame,
  `xippios.core.refresh` of sdk-core ADR-0051, which fetches the lists a source declares, one
  `Listed` each, writes their files, the provenance rows and `enums.py`, takes `--only` and
  `--render-only` and counts a request that ended in a transport error as sent. A
  multi-tenant render fetches through the reserved tenant's client and needs none of its
  variables for `--render-only`. `/refresh-reference-data` says what a source declares in a
  `Listed` and that the run writes the list's provenance row.
  (https://github.com/xippios/sdk-template/issues/239)
  - Hand-apply: `scripts/refresh_reference.py` — declare each list as a `Listed` in one
    `LISTS`, with an `origin` for each list whose provenance row names more than its
    endpoint, hand them to `xippios.core.refresh.run` with the package, `PACKAGED_LISTS`,
    the client and the quota header, delete the script's own fetches, writes, `render`,
    `Meter`, `metered` and `--only`, the port of the 0.4.0 metering among them, and run it
    once with `--render-only` — core 0.4.1 carries the frame of sdk-core ADR-0051, which
    counts a request that fails in transport as sent and writes the provenance rows from
    the declarations.
    `src/xippios/<package>/params.py` — where the docstring of `PACKAGED_LISTS` names the
    script's `LISTS`, `ID_LISTS` and `TABLES`, name its one `LISTS` of `Listed` — the port
    leaves the script one declaration.
