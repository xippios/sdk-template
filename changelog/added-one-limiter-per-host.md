- The generated `CLAUDE.md` and `/add-endpoint` state the rule of one limiter per host
  that sdk-core's conventions §2 and §6 set from core 0.4.0: a second base URL on the
  host of the first goes through the one client by its absolute URL, an origin or mirror
  that the publisher runs takes its canonical host's pace, a host that a dependency sends
  to is reached through the dependency's tasks alone, and any other host gets a client
  and a `RateLimit` of its own in `_client.py`, with its row in `CLAUDE.md`. No answer
  names a second host. `copier update` brings `/add-endpoint`.
  (https://github.com/xippios/sdk-template/issues/79)
  - Hand-apply: `CLAUDE.md` — add the code rule that starts "One limiter paces each host
    the package sends to" after the rule on `classify`, as a render has it, and a row for
    each other host the source sends to beside its API base URL, with that host's pace and
    where the pace comes from — conventions §6 paces each host by one limiter.
