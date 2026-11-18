- `scripts/refresh_reference.py` sends each request once, through the package's client with
  `RetryPolicy(max_attempts=1)`, and after its fetches prints the requests it sent and the
  quota left that upstream reported, a failed run's too. `--only <list> ...` fetches the
  named lists alone and keeps every other list's file. `/refresh-reference-data` says so,
  and the script's examples name the wrappers in snake case, as `/add-endpoint` names
  them, which matters to new repositories only.
  (https://github.com/xippios/sdk-template/issues/64)
  - Hand-apply: `scripts/refresh_reference.py` — for the fetches alone, set the client's
    configuration to `RetryPolicy(max_attempts=1)` with an `observe` hook that calls the
    hook it replaces, counts each response and reads upstream's quota header, and print
    the count at their end in a `finally`, as the template's `metered` does. Take
    `--only <list> ...` beside `--render-only`, checked against the packaged lists before
    the first request, and fetch every list before the first file is written — a 5xx or a
    429 spends no second call of the quota, a refresh's count is exact, and a change that
    packages a new list refreshes that list alone.
