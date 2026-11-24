- An adoption of this release brings xippios-core 0.5.0, and the Hand-apply note below
  carries, ready to adapt, the entries that a source's changelog takes for it, first the
  adoption's own, `breaking` with its three versions, since a core minor is a breaking
  change of the source, then for each change of core 0.5.0 that the source's callers see
  the entries that the list under "Adopting core 0.5.0" of sdk-core's `docs/handover.md`
  names, each in its group. The pull request that brings a change, the adoption's or a
  later one of the source's patch, copies the entry where it holds, as a fragment of its
  own, and words it for the source's own tasks and names. Where an entry and the
  handover's list part, the list holds. (https://github.com/xippios/sdk-core/issues/485)
  - Hand-apply: `changelog/breaking-<slug>.md` — The package depends on
    `xippios-core~=0.5.0`, its extras likewise, is updated to sdk-template v0.5.0 and
    applies conventions 1.30. (`https://github.com/xippios/<repository>/issues/<n>`) —
    every source's adoption, by conventions §15 item 9, its citation the URL of the
    adoption's issue.
    `changelog/changed-<slug>.md` — Every refusal of a call as given says `Nothing was
    sent.` after its first sentence, the MCP adapter's refusal of an argument among them,
    and a list of codes is checked by one call, which names the first code it refuses and
    refuses an empty list. The refusals' classes are unchanged.
    (https://github.com/xippios/sdk-core/issues/481) — every source, its own refusals and
    core's.
    `changelog/changed-<slug>.md` — `<write task>` is sent once, after a 429 or a renewing
    bearer's 401 too: its error after a 5xx or a failure in transit says that the request
    was sent once and that its outcome is unknown, or that nothing was sent where the
    connection failed, and its docstring names the read that shows whether a failed write
    was applied. (https://github.com/xippios/sdk-core/issues/480) — each write task, and
    each read that upstream bills, which a 5xx no longer repeats.
    `changelog/changed-<slug>.md` — The description of `<tool>` is its task's docstring
    before `Args:`, under 1,000 characters, and the text of each of its arguments stands
    in its input schema. (https://github.com/xippios/sdk-core/issues/485) — each tool whose
    description the adoption trims.
    `changelog/breaking-<slug>.md` — `<tool>` takes no `offset`: its task pages upstream
    itself, and a caller pages it by the task's own `start`.
    (https://github.com/xippios/sdk-core/issues/476) — each tool of a task that takes
    `start` whose cap was paged.
    `changelog/added-<slug>.md` — The answer of `<task>` names the codes of its rows in
    `meta.names`, and a row's code that the packaged list lacks is left out of the names and
    said in `meta.notes`, which holds one sentence for each fact the task says about its
    answer. (https://github.com/xippios/sdk-core/issues/478) — each task whose record's
    code field declares its packaged list or the field in which upstream sends the name,
    and each task's notes.
    `changelog/changed-<slug>.md` — A decimal without fractional digits is a JSON integer
    in the answers, `16217` where it read `16217.0`.
    (https://github.com/xippios/sdk-core/issues/478) — each task whose answer holds such a
    decimal.
    `changelog/changed-<slug>.md` — `meta.retrieved_at` of `<task>` is the client's time of
    the answer, the oldest where it assembles several.
    (https://github.com/xippios/sdk-core/issues/479) — each task whose `retrieved_at` read
    another time.
    `changelog/changed-<slug>.md` — `<task>` sends no request at or past upstream's count,
    and where it needs more than `<n>` pages it refuses with `InvalidRequestError` and
    returns nothing, naming the count, the bound, the paging argument, the requests sent,
    the page reached and the total of pages. (https://github.com/xippios/sdk-core/issues/480)
    — each task that walks offset pages, with its bound.
    `changelog/breaking-<slug>.md` — `<task>` is renamed, takes the arguments that
    identify a record in the order of upstream's path, or leaves, by the boundary of a
    source package. (https://github.com/xippios/sdk-core/issues/474) — each task, argument
    or field renamed or removed.
    `changelog/changed-<slug>.md` — The answers are kept in core's cache, each for the
    lifetime of the longest path prefix that its path starts with, none where no prefix
    matches. (https://github.com/xippios/sdk-core/issues/479) — a read-only source of public
    data, in `added` where it kept no cache before.
    `changelog/changed-<slug>.md` — The refusal before a request into a spent quota says
    "quota" with the policy's source and no longer names the key's variable.
    (https://github.com/xippios/sdk-core/issues/485) — a source whose quota other sources
    share under one key.
    `changelog/changed-<slug>.md` — A tenant's client is kept until the registry is reset,
    so a tenant's changed variable takes effect at the next start, and a value that the
    source checks is refused by its own `ConfigError`, which names the variable and no
    value. (https://github.com/xippios/sdk-core/issues/475) — a multi-tenant source whose
    running server built a new client when a variable changed.
    `changelog/changed-<slug>.md` — Both servers are named `xippios-<source>`, the help of
    `--allow-remote` takes core's one wording, and the server's instructions come from the
    tasks module. (https://github.com/xippios/sdk-core/issues/476) — a source whose server
    took another name, the write server of a source that named it.
    `changelog/changed-<slug>.md` — The client reads each answer within one read timeout,
    60 s by default, and connects, writes and waits for a connection within 10 s each.
    (https://github.com/xippios/sdk-core/issues/475) — a source whose timeouts change.
    No entry for the credential names kept for each source — a source's answers change by
    it only beside another source, which the host's release states.
