- The rendered `/add-endpoint` and `/record-fixture` describe the helpers and the recorder of
  xippios-core 0.4.1, which a source adopts with this release. `/add-endpoint` refuses a code
  that a packaged list lacks by the `check` of `PackagedList.codes(...)` in place of an
  `UnknownCode` raised by hand, names `names_codes` and `UNNAMED_CODES`,
  `ResultCap(paged=True)` and `keep="last"`, `newer_than`, `fetch_counted` with
  `QueryTooLarge` and `Ceiling` with `fetch_periods`, and in a render without reference data
  names no helper of a packaged list and no reference lookup. `/record-fixture` names
  `rewrite=`, `send_once` in place of a client built for one attempt, the recorder's refusal
  of a 1xx or a 3xx and `record_task` for every exchange of a task.
  (https://github.com/xippios/sdk-template/issues/250, https://github.com/xippios/sdk-template/issues/270)
