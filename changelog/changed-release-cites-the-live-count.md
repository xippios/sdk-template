- The rendered `/release-prep` cites the count of the live run's requests from the line
  `requests sent by the live run: <n>` that xippios-core 0.4.1's testing plugin prints in the
  log of `live.yml`, from a green run on the commit of `main` that the release starts from
  and never from a run on an earlier commit. The header of the rendered `tests/test_live.py`
  points to that line and states no count of its own.
  (https://github.com/xippios/sdk-core/issues/382, https://github.com/xippios/sdk-template/issues/237)
  - Hand-apply: `tests/test_live.py` — add to the module's docstring that core's testing
    plugin prints the run's requests as `requests sent by the live run: <n>`, the count in
    the log of `live.yml` that `/release-prep` cites, and delete a count the docstring
    states by hand — the plugin counts every run, so a count written by hand goes stale
    with the next live test.
