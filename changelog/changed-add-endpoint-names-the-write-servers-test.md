- Where `write_server` is true, `/add-endpoint` says that a write task goes into
  `tasks_write.py` and that a source's first one brings `tests/test_tasks_write.py`, which
  awaits core's `xippios.core.testing.assert_write_tools` under `@pytest.mark.anyio`, as
  conventions §8 and sdk-core ADR-0042 decision 1 ask. The command gives the test's code,
  and `copier update` brings it. (https://github.com/xippios/sdk-template/issues/220)
