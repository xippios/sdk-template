- An adoption of this release brings xippios-core 0.4.1, and the Hand-apply note below
  carries, ready to adapt, the entries that a source's changelog takes for it, first the
  adoption's own, `changed` with its three versions, then for each change of core 0.4.1
  that the source's callers see the entries that the list under "Adopting core 0.4.1" of
  sdk-core's `docs/handover.md` names, each in its group, and in `changed` the one it names
  without a group. The pull request that brings a change, the adoption's or a later one
  of the source's patch, copies the entry where it holds, as a fragment of its own, and
  words it for the source's own tasks and names. Where an entry and the handover's list
  part, the list holds, and the source corrects its fragment before its release, which
  rewords no entry. (https://github.com/xippios/sdk-template/issues/238)
  - Hand-apply: `changelog/changed-<slug>.md` — The package depends on
    `xippios-core~=0.4.1`, its extras likewise, is updated to sdk-template v0.4.1 and
    applies conventions 1.29. (`https://github.com/xippios/<repository>/issues/<n>`) —
    every source's adoption, by conventions §15 item 9, its citation the URL of the
    adoption's issue, and `breaking` in place of `changed` where the same pull request
    brings core 0.4.0 too, a core minor.
    `changelog/added-<slug>.md` — `<tool>` takes `offset`, the rows of a cut answer already
    shown, and answers the rows after them by running its task again. Every page carries
    its note, the last one too, and the note of every page but the last names the `offset`
    to continue with, so an answer without a note is whole.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap in `MCP_CAPS` is
    `ResultCap(paged=True)`.
    `changelog/changed-<slug>.md` — `<tool>` shows the newest rows of a cut series, ordered
    oldest first, in place of the oldest, and its `offset` walks to older rows.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose cap keeps the last
    rows, `ResultCap(keep="last")`.
    `changelog/changed-<slug>.md` — The note of a cut answer of `<tool>` names the `offset`
    to continue with in place of the narrower query it named before.
    (https://github.com/xippios/sdk-core/issues/314) — each tool whose note named a way
    around the cut before its cap took `paged=True`.
    `changelog/added-<slug>.md` — The answer of `<task>` names each `<parameter>` code it
    was called with in `meta.names`, by the name that its packaged list holds,
    `{"<parameter>": {"<code>": "<name>"}}`.
    (https://github.com/xippios/sdk-core/issues/316, https://github.com/xippios/sdk-core/issues/310)
    — each task that takes a country, area, reporter or partner code, by `names_codes`.
    `changelog/changed-<slug>.md` — `<task>` withholds its answer for a `<parameter>` code
    that its packaged list lacks, with the list's refusal, where it answered for such a
    code before. (https://github.com/xippios/sdk-core/issues/316) — each task that sent
    such a code upstream unchecked, as sdk-faostat's `get_series` sent a code of a domain
    outside its five area tables.
    `changelog/breaking-<slug>.md` — The tasks refuse an ISO alpha-3 code, which they
    resolved before the call, and the refusal names the UN Comtrade code it stands for,
    `"CHE"` refused naming `757 (Switzerland)`.
    (https://github.com/xippios/sdk-core/issues/375, https://github.com/xippios/sdk-core/issues/316)
    — sdk-comtrade alone, whose release this makes a minor by conventions §12.
    `changelog/changed-<slug>.md` — `<task>` refuses a query over upstream's limit of `<n>`
    records per call with core's `QueryTooLarge`, an `InvalidRequestError` whose message
    gives the count, the limit and what narrows the query, and answers a count of 0 with
    its empty answer, sending no data request. (https://github.com/xippios/sdk-core/issues/317)
    — each task that refuses with `QueryTooLarge`, by `fetch_counted` or by its `classify`
    of upstream's refusal, whose message names the request too, and sdk-comtrade's entry
    adds that the answer of `get_data` carries the count as `meta.total`.
    `changelog/breaking-<slug>.md` — `xippios.comtrade.errors` holds no `QueryTooLarge` of
    its own any more, so an import of it fails, and a caller catches core's
    `xippios.core.QueryTooLarge`, which the tasks raise.
    (https://github.com/xippios/sdk-core/issues/317) — sdk-comtrade alone, in the minor of
    its alpha-3 codes.
    `changelog/changed-<slug>.md` — `<task>` refuses a `<parameter>` code that its packaged
    list lacks by core's check, which names the list, its fetch date and the closest codes,
    and refuses a value of the other type than the list's codes with
    `InvalidRequestError`, naming the integer or the text to pass.
    (https://github.com/xippios/sdk-core/issues/313) — each argument that
    `PackagedList.codes(...).check` now checks, worded by the refusals whose wording or
    class the tests of the port change.
    `changelog/changed-<slug>.md` — `<task>` refuses a `since` it cannot read in core's
    wording, `since must be the meta.vintage text of an earlier call, an ISO date and time without a time zone such as '2026-10-06T08:00:00'`,
    its class and its two reasons kept. (https://github.com/xippios/sdk-core/issues/318) —
    sdk-usda-esr alone, since sdk-usda-psd's wording stays as it is.
    `changelog/changed-<slug>.md` — `<task>` refuses a range over its ceiling of `<n>`
    `<unit>` in core's wording before the first request, naming the range, the ceiling, its
    unit and, where the MCP server's ceiling is lower, the option that raises it, its class
    `InvalidRequestError` and the option's name unchanged. A request after the first that
    fails raises its error, its class kept, naming the periods fetched before it by their
    count, the first and the last, and the task returns nothing.
    (https://github.com/xippios/sdk-core/issues/315) — each task on `fetch_periods`.
    `changelog/added-<slug>.md` — The preview of `<write task>` carries `reads`, the
    operations it read, `[]` for none, and the task's docstring says whether its preview
    reads first and what the read costs. (https://github.com/xippios/sdk-core/issues/182) —
    each write task, its preview held by `assert_write_tools` with `preview_reads`.
